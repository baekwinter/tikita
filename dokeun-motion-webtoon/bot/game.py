"""게임 규칙 계층. 디스코드 봇과 웹 API 가 같은 GameService 를 사용한다.

반환값은 모두 '참가자에게 보여도 되는' 데이터만 담는다. 정답표(answers.json)는
채점·응답 판단에만 쓰이고 그대로 밖으로 나가지 않는다.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable

from .config import BOT_NAME, GAME_TITLE, Config, DATA_DIR, load_json
from .database import Database, utcnow
from .evidence import Catalog
from .questions import AskResult, Question, QuestionBank, Verdict
from .rewards import RewardService
from .scheduler import episode_schedule, kst

CHARACTERS = ["반휘혈", "온하늘", "남궁호", "차세리"]

CASE_SUMMARY = (
    "2026년 추석 특별 방송 도중, 방송실 스피커에서 예정에 없던 고백이 흘러나왔다.\n"
    "누가 녹음했을까? 누구에게 전하려던 마음이었을까? 그리고 누가 이 고백을 방송에 송출했을까?"
)


class GameError(Exception):
    def __init__(self, code: str, message: str, **extra: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


@dataclass
class FinalKey:
    items: dict[str, dict[str, Any]]

    @classmethod
    def load(cls, doc: dict | None = None) -> "FinalKey":
        doc = doc or load_json(DATA_DIR / "answers.json")
        return cls(items=doc["final"])

    def form(self) -> list[dict[str, Any]]:
        """참가자에게 보여 줄 문항 (정답 제외)."""
        out = []
        for key in ("q1", "q2", "q3", "q4"):
            out.append({"key": key, "label": self.items[key]["label"], "type": "choice", "choices": CHARACTERS})
        out.append({"key": "q5", "label": self.items["q5"]["label"], "type": "text"})
        out.append({"key": "story", "label": "사건의 흐름을 자유롭게 정리해 주세요 (선택)", "type": "text"})
        return out

    def grade(self, answers: dict[str, str]) -> dict[str, Any]:
        items: dict[str, bool] = {}
        for key in ("q1", "q2", "q3", "q4"):
            items[key] = (answers.get(key) or "").strip() == self.items[key]["answer"]
        text = f"{answers.get('q5') or ''}\n{answers.get('story') or ''}"
        rubric = self.items["q5"]["rubric"]
        hit_groups = []
        required_ok = True
        optional_hits = 0
        for g in rubric["groups"]:
            hit = any(word in text for word in g["any"])
            if hit:
                hit_groups.append(g["name"])
            if g.get("required") and not hit:
                required_ok = False
            if not g.get("required") and hit:
                optional_hits += 1
        items["q5"] = required_ok and optional_hits >= int(rubric.get("min_optional", 1))
        correct = sum(items.values())
        return {"items": items, "correct": correct, "total": len(items), "solved": all(items.values()),
                "q5_groups": hit_groups}


class GameService:
    def __init__(self, cfg: Config, db: Database, catalog: Catalog, bank: QuestionBank,
                 rewards: RewardService, final_key: FinalKey | None = None,
                 ai_pick: Callable[[str, list[Question]], str | None] | None = None,
                 clock: Callable[[], datetime] = utcnow):
        self.cfg = cfg
        self.db = db
        self.catalog = catalog
        self.bank = bank
        self.rewards = rewards
        self.final_key = final_key or FinalKey.load()
        self.ai_pick = ai_pick
        self.clock = clock

    # ---- 공통 상태 --------------------------------------------------------
    @property
    def current_episode(self) -> int:
        return self.db.current_episode()

    def phase(self) -> str:
        if self.db.paused:
            return "paused"
        if self.db.is_posted("ending"):
            return "ended"
        if not self.db.is_posted("opening"):
            return "before"
        return "live"

    def gate(self) -> None:
        """참가자 기능 사용 가능 여부."""
        phase = self.phase()
        if phase == "before":
            start = kst(self.cfg.start_at_utc, self.cfg)
            raise GameError("before_start", f"이벤트는 {start}(한국 시간)에 시작됩니다. 조금만 기다려 주세요.")
        if phase == "paused":
            raise GameError("paused", "방송부가 잠시 방송을 점검하고 있습니다. 잠시 후 다시 찾아와 주세요.")

    def today_start(self) -> datetime:
        local = self.clock().astimezone(self.cfg.tz)
        return local.replace(hour=0, minute=0, second=0, microsecond=0)

    def today_key(self) -> str:
        return self.clock().astimezone(self.cfg.tz).strftime("%Y-%m-%d")

    # ---- 참가 등록 --------------------------------------------------------
    def register(self, user_id: int, display_name: str | None) -> dict[str, Any]:
        self.gate()
        new = self.db.register_player(user_id, display_name)
        gained = self.rewards.grant(user_id, "join") if new else 0
        return {"new": new, "gained": gained}

    def ensure_player(self, user_id: int, display_name: str | None = None) -> None:
        if self.db.get_player(user_id) is None:
            self.register(user_id, display_name)

    # ---- 사건 정보 --------------------------------------------------------
    def episode_public(self, number: int) -> dict[str, Any] | None:
        ep = self.catalog.episodes.get(number)
        if ep is None or number > self.current_episode:
            return None
        row = self.db.get_release("episode", number)
        link = None
        if row and row["message_id"]:
            link = f"https://discord.com/channels/{self.cfg.guild_id}/{row['channel_id']}/{row['message_id']}"
        return {
            "number": ep.number,
            "code": ep.code,
            "title": ep.display_title,
            "description": ep.description,
            "keywords": ep.keywords,
            "has_thumbnail": ep.thumbnail_file is not None,
            "video_url": ep.video_url,
            "discord_link": link,
            "released_at": row["released_at"] if row else None,
        }

    def case_info(self) -> dict[str, Any]:
        cur = self.current_episode
        schedule = episode_schedule(self.cfg, self.catalog, self.db.schedule_overrides())
        nxt = cur + 1 if cur < self.catalog.episode_count else None
        return {
            "bot_name": BOT_NAME,
            "title": GAME_TITLE,
            "summary": CASE_SUMMARY,
            "phase": self.phase(),
            "start_at": self.cfg.start_at_utc.isoformat(),
            "start_at_kst": kst(self.cfg.start_at_utc, self.cfg),
            "current_episode": cur,
            "total_episodes": self.catalog.episode_count,
            "episode": self.episode_public(cur) if cur else None,
            "episodes": [self.episode_public(n) for n in range(1, cur + 1)],
            "next_episode": {"number": nxt, "at_kst": kst(schedule.get(nxt), self.cfg),
                             "at": schedule[nxt].isoformat() if schedule.get(nxt) else None} if nxt else None,
            "characters": CHARACTERS,
        }

    # ---- YES/NO 질문 ------------------------------------------------------
    def question_quota(self, user_id: int) -> dict[str, int]:
        qs = self.cfg.section("questions")
        limit = int(qs.get("daily_limit", 30))
        used = self.db.questions_since(user_id, self.today_start())
        return {"limit": limit, "used": used, "remaining": max(0, limit - used), "total": self.db.total_questions(user_id)}

    async def ask(self, user_id: int, text: str, source: str = "discord", display_name: str | None = None) -> dict[str, Any]:
        self.gate()
        self.ensure_player(user_id, display_name)
        text = (text or "").strip()
        if len(text) < 3:
            raise GameError("too_short", "질문을 조금 더 길게 적어 주세요.")
        if len(text) > 200:
            raise GameError("too_long", "질문은 200자 이내로 적어 주세요.")

        qs = self.cfg.section("questions")
        now = self.clock()
        cooldown = int(qs.get("cooldown_seconds", 10))
        last = self.db.last_question_at(user_id)
        if last and (now - last).total_seconds() < cooldown:
            wait = cooldown - int((now - last).total_seconds())
            raise GameError("cooldown", f"방송부가 기록을 정리하는 중입니다. {wait}초 뒤에 다시 질문해 주세요.", wait=wait)

        normalized = self.bank.parse(text).normalized
        window = timedelta(minutes=int(qs.get("duplicate_window_minutes", 30)))
        duplicate = self.db.recent_same_question(user_id, normalized, now - window) is not None

        quota = self.question_quota(user_id)
        if quota["remaining"] <= 0 and not duplicate:
            raise GameError("limit", "오늘의 질문 기회를 모두 사용했습니다. 내일 0시(한국 시간)에 다시 채워집니다.", **quota)

        cur = self.current_episode
        unconfirmed = bool(qs.get("answer_unconfirmed", False))
        if self.ai_pick is not None:
            result: AskResult = await asyncio.to_thread(self.bank.ask, text, cur, unconfirmed, self.ai_pick)
        else:
            result = self.bank.ask(text, cur, unconfirmed)

        counted = result.counts_toward_limit and not duplicate
        store_text = text if self.cfg.section("privacy").get("log_question_text", True) else None
        self.db.log_question(user_id, normalized, store_text, result.question_id, result.verdict.value, counted, source, now)

        gained = 0
        if counted:
            gained += self.rewards.grant(user_id, "first_question")
            gained += self.rewards.grant(user_id, "daily_question", self.today_key())

        related = None
        if result.related_evidence and self.catalog.is_evidence_released(
                result.related_evidence, cur, self.db.manually_released_evidence()):
            ev = self.catalog.evidence[result.related_evidence]
            related = {"id": ev.evidence_id, "title": ev.title}

        answered = result.verdict in {Verdict.YES, Verdict.NO, Verdict.IRRELEVANT}
        return {
            "question": text,
            "verdict": result.verdict.value,
            "label": result.label,
            "hint": result.hint,
            "response_text": result.response_text if answered else "",
            "matched": result.canonical if answered else None,
            "related_evidence": related if answered else None,
            "counted": counted,
            "duplicate": duplicate,
            "gained": gained,
            "quota": self.question_quota(user_id),
        }

    def question_history(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.db.question_history(user_id, limit)
        out = []
        for r in rows:
            q = self.bank.questions.get(r["question_id"]) if r["question_id"] else None
            verdict = Verdict(r["result"])
            answered = verdict in {Verdict.YES, Verdict.NO, Verdict.IRRELEVANT}
            out.append({
                "asked_at": r["asked_at"],
                "question": r["question_text"] or (q.canonical if (q and answered) else "(기록되지 않은 질문)"),
                "verdict": verdict.value,
                "label": AskResult(verdict).label,
            })
        return out

    # ---- 증거 -------------------------------------------------------------
    def evidence_board(self, user_id: int | None = None) -> list[dict[str, Any]]:
        cur = self.current_episode
        manual = self.db.manually_released_evidence()
        found = self.db.found_evidence(user_id) if user_id else set()
        board = []
        for ev in self.catalog.sorted_evidence():
            if ev.release_episode <= cur or ev.evidence_id in manual:
                board.append(ev.public(found=ev.evidence_id in found))
            else:
                board.append(ev.locked())
        return board

    def released_evidence_ids(self) -> list[str]:
        return [e.evidence_id for e in self.catalog.released_evidence(self.current_episode, self.db.manually_released_evidence())]

    def investigate(self, user_id: int, evidence_id: str, display_name: str | None = None) -> dict[str, Any]:
        self.gate()
        self.ensure_player(user_id, display_name)
        evidence_id = (evidence_id or "").strip().upper()
        if not self.catalog.is_evidence_released(evidence_id, self.current_episode, self.db.manually_released_evidence()):
            raise GameError("locked", "아직 공개되지 않았거나 존재하지 않는 증거입니다.")
        ev = self.catalog.evidence[evidence_id]
        new = self.db.mark_evidence(user_id, evidence_id)
        gained = self.rewards.grant(user_id, "evidence_found", evidence_id) if new else 0
        data = ev.public(found=True)
        data.update({"new": new, "gained": gained})
        return data

    # ---- 회차 시청 --------------------------------------------------------
    def mark_watched(self, user_id: int, number: int, display_name: str | None = None) -> dict[str, Any]:
        self.gate()
        self.ensure_player(user_id, display_name)
        if number < 1 or number > self.current_episode:
            raise GameError("locked", "아직 공개되지 않은 회차입니다.")
        new = self.db.mark_watched(user_id, number)
        gained = self.rewards.grant(user_id, "watch_episode", str(number)) if new else 0
        return {"episode": number, "new": new, "gained": gained}

    # ---- 가설(추리) -------------------------------------------------------
    def submit_theory(self, user_id: int, body: str, display_name: str | None = None) -> dict[str, Any]:
        self.gate()
        self.ensure_player(user_id, display_name)
        body = (body or "").strip()
        limit = int(self.cfg.section("theory").get("max_length", 1500))
        if len(body) < 5:
            raise GameError("too_short", "추리 내용을 조금 더 적어 주세요.")
        body = body[:limit]
        self.db.add_theory(user_id, body)
        gained = self.rewards.grant(user_id, "daily_theory", self.today_key())
        return {"saved": True, "gained": gained, "count": self.db.theory_count(user_id)}

    # ---- 최종 추리 --------------------------------------------------------
    def final_status(self, user_id: int) -> dict[str, Any]:
        fin = self.cfg.section("final")
        subs = self.db.submissions(user_id)
        opens = int(fin.get("open_from_episode", 1))
        return {
            "open": self.current_episode >= opens,
            "open_from_episode": opens,
            "attempts": len(subs),
            "max_attempts": int(fin.get("max_attempts", 3)),
            "feedback": fin.get("feedback", "count"),
            "solved": any(s["solved"] for s in subs),
            "ended": self.phase() == "ended",
            "form": self.final_key.form(),
            "last": self._submission_view(subs[-1]) if subs else None,
        }

    def _submission_view(self, row) -> dict[str, Any]:
        answers = json.loads(row["answers"])
        view: dict[str, Any] = {"submitted_at": row["submitted_at"], "answers": answers}
        fb = self.cfg.section("final").get("feedback", "count")
        if self.phase() == "ended":
            view.update(self.final_key.grade(answers))
        elif fb == "count":
            view.update({"correct": row["correct_count"], "total": 5})
        return view

    def submit_final(self, user_id: int, answers: dict[str, str], display_name: str | None = None) -> dict[str, Any]:
        self.gate()
        self.ensure_player(user_id, display_name)
        status = self.final_status(user_id)
        if not status["open"]:
            raise GameError("not_open", f"최종 추리는 EP.{status['open_from_episode']:02d} 공개 후 제출할 수 있습니다.")
        if status["solved"]:
            raise GameError("solved", "이미 사건을 해결했습니다. 엔딩 공개를 기다려 주세요.")
        if status["attempts"] >= status["max_attempts"]:
            raise GameError("no_attempts", "최종 추리 제출 기회를 모두 사용했습니다.")
        clean = {k: (answers.get(k) or "").strip()[:1500] for k in ("q1", "q2", "q3", "q4", "q5", "story")}
        for k in ("q1", "q2", "q3", "q4"):
            if clean[k] not in CHARACTERS:
                raise GameError("invalid", "Q1~Q4 는 인물 목록에서 골라 주세요.")
        if len(clean["q5"]) < 10:
            raise GameError("invalid", "Q5 에는 '왜, 어떻게' 그렇게 했는지 한두 문장으로 설명해 주세요.")

        graded = self.final_key.grade(clean)
        self.db.add_submission(user_id, clean, graded["correct"], graded["solved"])
        gained = self.rewards.grant(user_id, "final_submit")
        ended = self.phase() == "ended"
        if ended:
            gained += self._grant_final_rewards(user_id)

        result: dict[str, Any] = {"saved": True, "gained": gained,
                                  "attempts": status["attempts"] + 1, "max_attempts": status["max_attempts"]}
        fb = self.cfg.section("final").get("feedback", "count")
        if ended:
            result.update(graded)
        elif fb == "count":
            result.update({"correct": graded["correct"], "total": graded["total"], "solved": graded["solved"]})
        return result

    def _grant_final_rewards(self, user_id: int) -> int:
        subs = self.db.submissions(user_id)
        if not subs:
            return 0
        best = max(subs, key=lambda s: (s["solved"], s["correct_count"]))
        graded = self.final_key.grade(json.loads(best["answers"]))
        gained = 0
        for key, ok in graded["items"].items():
            if ok:
                gained += self.rewards.grant(user_id, "final_correct_item", key)
        if graded["solved"]:
            gained += self.rewards.grant(user_id, "case_solved")
        return gained

    def finalize_all(self) -> int:
        """엔딩 공개 시점에 제출자 전원의 정답 보상을 정산한다 (중복 지급 없음)."""
        total = 0
        for row in self.db.all_players():
            total += self._grant_final_rewards(row["user_id"])
        return total

    def ending_text(self) -> dict[str, str]:
        f = self.final_key.items
        return {
            "q1": f"{f['q1']['label']} → {f['q1']['answer']}",
            "q2": f"{f['q2']['label']} → {f['q2']['answer']}",
            "q3": f"{f['q3']['label']} → {f['q3']['answer']}",
            "q4": f"{f['q4']['label']} → {f['q4']['answer']}",
            "q5": f"{f['q5']['label']} → {f['q5']['model_answer']}",
        }

    # ---- 진행도 -----------------------------------------------------------
    def progress(self, user_id: int) -> dict[str, Any]:
        player = self.db.get_player(user_id)
        released = self.released_evidence_ids()
        found = self.db.found_evidence(user_id)
        subs = self.db.submissions(user_id)
        if not player:
            status = "조사 시작 전"
        elif any(s["solved"] for s in subs) and self.phase() == "ended":
            status = "사건 해결"
        elif subs:
            status = "최종 추리 제출 완료"
        elif found or self.db.total_questions(user_id):
            status = "수사 중"
        else:
            status = "조사 시작 전"
        return {
            "registered": player is not None,
            "status": status,
            "current_episode": self.current_episode,
            "total_episodes": self.catalog.episode_count,
            "watched": sorted(self.db.watched_episodes(user_id)),
            "evidence_found": len(found & set(released)),
            "evidence_released": len(released),
            "evidence_total": len(self.catalog.evidence),
            "questions": self.question_quota(user_id),
            "theories": self.db.theory_count(user_id),
            "final_attempts": len(subs),
            "final_max_attempts": int(self.cfg.section("final").get("max_attempts", 3)),
            "points": self.rewards.total(user_id),
            "currency": self.rewards.currency,
        }

    # ---- 수사 노트 --------------------------------------------------------
    def get_note(self, user_id: int) -> dict[str, Any]:
        row = self.db.get_note(user_id)
        return {"body": row["body"] if row else "", "updated_at": row["updated_at"] if row else None}

    def save_note(self, user_id: int, body: str) -> dict[str, Any]:
        self.db.save_note(user_id, (body or "")[:5000])
        return self.get_note(user_id)


def build_service(cfg: Config, db: Database | None = None) -> GameService:
    """봇·웹 API·CLI 가 같은 방식으로 게임 서비스를 조립한다."""
    from .ai import make_ai_picker
    from .rewards import RewardTable

    db = db or Database(cfg.db_path)
    catalog = Catalog.load()
    bank = QuestionBank.load()
    rewards = RewardService(db, RewardTable.load())
    ai_pick = make_ai_picker(cfg.anthropic_api_key, cfg.ai_model) if cfg.ai_enabled else None
    return GameService(cfg, db, catalog, bank, rewards, FinalKey.load(), ai_pick)
