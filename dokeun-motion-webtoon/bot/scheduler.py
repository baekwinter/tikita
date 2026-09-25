"""한국 시간 기준 예약 공개 스케줄러.

안전 장치
- 모든 공식 게시는 DB 에 'posting' 으로 먼저 선점한 뒤 보내고, 성공하면 'posted' 로 바꾼다.
  → 봇을 재시작해도 같은 개막 공지·회차가 두 번 올라가지 않는다.
- 'posting' 상태로 남은 항목(게시 도중 종료)은 채널 기록에서 ref 표식을 찾아 복구하고,
  찾지 못했을 때만 다시 게시한다.
- 봇이 꺼져 있다가 늦게 켜져서 공개 시각이 많이 지난 회차(catchup_grace_minutes 초과)는
  자동으로 몰아서 올리지 않고 운영진에게 확인을 요청한다. 한 번의 점검에서는 회차를 1개만 올린다.
- 회차는 반드시 번호 순서대로만 공개된다.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Protocol

from .config import Config, parse_local
from .database import Database, utcnow
from .evidence import Catalog, Episode, Evidence

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 편성표 계산 (순수 함수)
# ---------------------------------------------------------------------------
def preset_slots(cfg: Config) -> list[datetime | None]:
    sched = cfg.section("schedule")
    mode = sched.get("mode", "4days_3per_day")
    days = sched["presets"][mode]
    slots: list[datetime | None] = []
    for day in days:
        for t in day["times"]:
            slots.append(parse_local(f"{day['date']}T{t}", cfg.tz) if t else None)
    return slots


def episode_schedule(cfg: Config, catalog: Catalog, overrides: dict[int, datetime] | None = None) -> dict[int, datetime | None]:
    """회차별 공개 시각(UTC). 우선순위: /운영 예약 변경 > episodes.json release_datetime > settings 편성표."""
    overrides = overrides or {}
    slots = preset_slots(cfg)
    result: dict[int, datetime | None] = {}
    for idx, ep in enumerate(catalog.sorted_episodes()):
        if ep.number in overrides:
            result[ep.number] = overrides[ep.number]
        elif ep.release_datetime:
            result[ep.number] = parse_local(ep.release_datetime, cfg.tz)
        else:
            result[ep.number] = slots[idx] if idx < len(slots) else None
    # 1화는 개막 시각에 공개된다. 편성표가 비어 있으면 개막 시각을 쓴다.
    if 1 in result and result[1] is None:
        result[1] = cfg.start_at_utc
    return result


def ending_time(cfg: Config) -> datetime | None:
    raw = cfg.section("schedule").get("ending_at")
    return parse_local(raw, cfg.tz) if raw else None


def schedule_problems(cfg: Config, schedule: dict[int, datetime | None]) -> list[str]:
    problems = []
    prev: datetime | None = None
    for n in sorted(schedule):
        t = schedule[n]
        if t is None:
            problems.append(f"EP.{n:02d} 공개 시각 미정")
            continue
        if t < cfg.start_at_utc:
            problems.append(f"EP.{n:02d} 공개 시각이 개막보다 이릅니다")
        if prev and t < prev:
            problems.append(f"EP.{n:02d} 공개 시각이 앞 회차보다 이릅니다")
        prev = t
    return problems


# ---------------------------------------------------------------------------
# 다음 행동 결정 (순수 함수)
# ---------------------------------------------------------------------------
@dataclass
class Action:
    kind: str                 # opening | episode | ending | alert
    item: str = "main"
    alert_key: str | None = None
    message: str | None = None


@dataclass
class PlanState:
    now: datetime
    start_at: datetime
    paused: bool
    opening_posted: bool
    posted_episodes: set[int]
    ending_posted: bool
    schedule: dict[int, datetime | None]
    ending_at: datetime | None
    grace: timedelta
    opening_grace: timedelta


def plan_next(state: PlanState) -> Action | None:
    if state.paused or state.now < state.start_at:
        return None

    if not state.opening_posted:
        late = state.now - state.start_at
        if late <= state.opening_grace:
            return Action("opening")
        return Action("alert", alert_key="overdue:opening",
                      message="개막 공지 시각이 크게 지났습니다. 확인 후 `/운영 시작` 으로 수동 게시하세요.")

    numbers = sorted(state.schedule)
    for n in numbers:
        if n in state.posted_episodes:
            continue
        when = state.schedule[n]
        if when is None or state.now < when:
            return None
        if n > 1 and (n - 1) not in state.posted_episodes:
            return None  # 앞 회차가 먼저
        if state.now - when > state.grace:
            return Action("alert", alert_key=f"overdue:episode:{n}",
                          message=f"EP.{n:02d} 공개 예정 시각이 {int((state.now - when).total_seconds() // 60)}분 지났습니다. "
                                  f"대량 게시를 막기 위해 자동 공개를 보류했습니다. 확인 후 `/운영 공개 대상:회차 번호:{n}` 으로 공개하세요.")
        return Action("episode", item=str(n))

    if state.ending_at and not state.ending_posted and state.now >= state.ending_at:
        if state.now - state.ending_at > state.grace:
            return Action("alert", alert_key="overdue:ending",
                          message="엔딩 공개 시각이 지났습니다. `/운영 공개 대상:엔딩` 으로 공개하세요.")
        return Action("ending")
    return None


# ---------------------------------------------------------------------------
# 게시 실행
# ---------------------------------------------------------------------------
class Publisher(Protocol):
    async def post_opening(self) -> tuple[int, int]: ...
    async def post_episode(self, episode: Episode, new_evidence: list[Evidence]) -> tuple[int, int]: ...
    async def post_evidence(self, evidence: Evidence) -> tuple[int, int]: ...
    async def post_ending(self) -> tuple[int, int]: ...
    async def find_marker(self, marker: str) -> int | None: ...
    async def notify_admins(self, text: str) -> None: ...


class TransientError(Exception):
    """재시도해도 되는 일시적 오류 (네트워크, Discord 5xx)."""


class PublishResult(str):
    pass


POSTED = PublishResult("posted")
ALREADY = PublishResult("already")
HELD = PublishResult("held")
FAILED = PublishResult("failed")


def marker(kind: str, item: str | int) -> str:
    return f"ref:{kind}:{item}"


class ReleaseScheduler:
    def __init__(self, cfg: Config, db: Database, catalog: Catalog, publisher: Publisher,
                 on_ending: Callable[[], Awaitable[Any]] | None = None,
                 retry_delays: tuple[float, ...] = (2, 4, 8)):
        self.cfg = cfg
        self.db = db
        self.catalog = catalog
        self.publisher = publisher
        self.on_ending = on_ending
        self.retry_delays = retry_delays
        self._lock = asyncio.Lock()

    # ---- 상태 -------------------------------------------------------------
    def schedule(self) -> dict[int, datetime | None]:
        return episode_schedule(self.cfg, self.catalog, self.db.schedule_overrides())

    def state(self, now: datetime) -> PlanState:
        sched = self.cfg.section("schedule")
        return PlanState(
            now=now,
            start_at=self.cfg.start_at_utc,
            paused=self.db.paused,
            opening_posted=self.db.is_posted("opening"),
            posted_episodes=self.db.released_episode_numbers(),
            ending_posted=self.db.is_posted("ending"),
            schedule=self.schedule(),
            ending_at=ending_time(self.cfg),
            grace=timedelta(minutes=sched.get("catchup_grace_minutes", 30)),
            opening_grace=timedelta(hours=sched.get("opening_catchup_hours", 12)),
        )

    # ---- 주기 점검 --------------------------------------------------------
    async def tick(self, now: datetime | None = None) -> list[str]:
        """한 번의 점검. 개막 공지 + 1화처럼 연달아 필요한 게시는 최대 2건까지 처리한다."""
        done: list[str] = []
        async with self._lock:
            late = await self._late_start(now or utcnow())
            if late:
                done.extend(late)
                await self.flush_alerts()
                return done
            posted_episode = False
            for _ in range(3):
                action = plan_next(self.state(now or utcnow()))
                if action is None:
                    break
                if action.kind == "alert":
                    await self.alert(action.alert_key or "alert", action.message or "")
                    break
                if action.kind == "episode":
                    if posted_episode:
                        break  # 한 번에 회차 하나만
                    res = await self._publish_episode(int(action.item), manual=False)
                    done.append(f"episode:{action.item}:{res}")
                    if res != POSTED:
                        break
                    posted_episode = True
                elif action.kind == "opening":
                    res = await self._publish("opening", "main", self.publisher.post_opening)
                    done.append(f"opening:{res}")
                    if res != POSTED:
                        break
                elif action.kind == "ending":
                    res = await self.publish_ending(manual=False, _locked=True)
                    done.append(f"ending:{res}")
                    break
            await self.flush_alerts()
        return done

    async def _late_start(self, now: datetime) -> list[str]:
        """event.auto_start_late 가 켜져 있으면, 개막 시각이 지났는데 개막·1화가 없을 때
        `/운영 시작` 과 똑같이 개막 공지 + 1화(영상이 없어도)를 한 번만 게시한다."""
        if not self.cfg.section("event").get("auto_start_late") or self.db.paused or now < self.cfg.start_at_utc:
            return []
        if self.db.is_posted("opening") and self.db.is_posted("episode", 1):
            return []
        res1 = await self._publish("opening", "main", self.publisher.post_opening, manual=True)
        done = [f"opening:{res1}"]
        if res1 in (POSTED, ALREADY):
            res2 = await self._publish_episode(1, manual=True)
            done.append(f"episode:1:{res2}")
        return done

    # ---- 운영진 알림 ------------------------------------------------------
    async def alert(self, key: str, message: str) -> None:
        if self.db.raise_alert(key, message):
            log.warning("운영 알림: %s", message)

    async def flush_alerts(self) -> None:
        for row in self.db.pending_alerts():
            try:
                await self.publisher.notify_admins(row["message"])
                self.db.mark_alert_notified(row["key"])
            except Exception:  # 알림 실패가 게시를 막지 않게 한다
                log.exception("운영진 알림 전송 실패")

    # ---- 게시 공통 --------------------------------------------------------
    async def _publish(self, kind: str, item: str | int, send: Callable[[], Awaitable[tuple[int, int]]],
                       manual: bool = False) -> PublishResult:
        row = self.db.get_release(kind, item)
        mk = marker(kind, item)
        if row and row["status"] == "posted":
            return ALREADY
        if row and row["status"] == "posting":
            found = await self.publisher.find_marker(mk)
            if found:
                self.db.complete_release(kind, item, self.cfg.event_channel_id, found)
                log.info("게시 이력 복구: %s", mk)
                return ALREADY
            self.db.drop_release(kind, item)
        if not self.db.claim_release(kind, item, manual=manual):
            return ALREADY

        attempts = len(self.retry_delays) + 1
        for i in range(attempts):
            try:
                channel_id, message_id = await send()
                self.db.complete_release(kind, item, channel_id, message_id)
                self.db.clear_alert(f"overdue:{kind}:{item}" if kind != "opening" else "overdue:opening")
                log.info("게시 완료: %s (message %s)", mk, message_id)
                return POSTED
            except TransientError as exc:
                log.warning("게시 일시 오류 (%s/%s) %s: %s", i + 1, attempts, mk, exc)
                if i + 1 < attempts:
                    await asyncio.sleep(self.retry_delays[i])
                    found = await self.publisher.find_marker(mk)
                    if found:  # 응답만 유실되고 실제로는 올라간 경우
                        self.db.complete_release(kind, item, self.cfg.event_channel_id, found)
                        return POSTED
            except Exception as exc:  # 권한 없음 등 재시도해도 소용없는 오류
                log.exception("게시 실패: %s", mk)
                self.db.drop_release(kind, item)
                await self.alert(f"failed:{kind}:{item}", f"{mk} 게시 실패: {type(exc).__name__}: {exc}")
                return FAILED
        self.db.drop_release(kind, item)
        await self.alert(f"failed:{kind}:{item}", f"{mk} 게시가 반복 실패했습니다. 네트워크/Discord 상태를 확인하세요.")
        return FAILED

    async def _publish_episode(self, number: int, manual: bool) -> PublishResult:
        ep = self.catalog.episodes[number]
        limit = self.cfg.section("media").get("upload_limit_mb", 10)
        status = ep.media_status(limit)
        policy = self.cfg.section("media").get("missing_video_policy", "hold")
        if status in {"missing", "too_large"} and policy == "hold" and not manual:
            reason = "영상 파일/링크가 없습니다" if status == "missing" else f"영상이 업로드 제한({limit}MB)을 넘고 video_url 이 없습니다"
            await self.alert(f"media:episode:{number}", f"{ep.code} 공개 시각이지만 {reason}. 공개를 보류합니다.")
            return HELD
        new_evidence = self.catalog.evidence_for_episode(number)
        res = await self._publish("episode", number, lambda: self.publisher.post_episode(ep, new_evidence), manual)
        if res == POSTED:
            self.db.clear_alert(f"media:episode:{number}")
        return res

    # ---- 운영진 수동 조작 --------------------------------------------------
    async def publish_opening(self) -> PublishResult:
        async with self._lock:
            res = await self._publish("opening", "main", self.publisher.post_opening, manual=True)
            await self.flush_alerts()
            return res

    async def publish_episode(self, number: int) -> PublishResult | str:
        async with self._lock:
            if number not in self.catalog.episodes:
                return "unknown"
            if not self.db.is_posted("opening"):
                return "no_opening"
            if number > 1 and not self.db.is_posted("episode", number - 1):
                return "order"
            res = await self._publish_episode(number, manual=True)
            await self.flush_alerts()
            return res

    async def publish_evidence(self, evidence_id: str) -> PublishResult | str:
        async with self._lock:
            ev = self.catalog.evidence.get(evidence_id)
            if ev is None:
                return "unknown"
            if ev.release_episode <= self.db.current_episode():
                return "already_open"
            res = await self._publish("evidence", evidence_id, lambda: self.publisher.post_evidence(ev), manual=True)
            await self.flush_alerts()
            return res

    async def publish_ending(self, manual: bool = True, _locked: bool = False) -> PublishResult | str:
        async def run() -> PublishResult | str:
            if self.db.current_episode() < self.catalog.episode_count:
                return "episodes_left"
            res = await self._publish("ending", "main", self.publisher.post_ending, manual)
            if res == POSTED and self.on_ending:
                await self.on_ending()
            await self.flush_alerts()
            return res

        if _locked:
            return await run()
        async with self._lock:
            return await run()


async def run_forever(scheduler: ReleaseScheduler, tick_seconds: float, stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await scheduler.tick()
        except Exception:
            log.exception("스케줄러 점검 중 오류")
        try:
            await asyncio.wait_for(stop.wait(), timeout=tick_seconds)
        except asyncio.TimeoutError:
            pass


def kst(dt: datetime | None, cfg: Config) -> str:
    if dt is None:
        return "미정"
    return dt.astimezone(cfg.tz).strftime("%m/%d(%a) %H:%M").replace("Mon", "월").replace("Tue", "화") \
        .replace("Wed", "수").replace("Thu", "목").replace("Fri", "금").replace("Sat", "토").replace("Sun", "일")


def utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc)
