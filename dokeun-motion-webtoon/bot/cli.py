"""운영진용 오프라인 도구 (디스코드 연결 없이 실행).

    python -m bot.cli check                     데이터·편성·미디어 점검
    python -m bot.cli schedule                  공개 일정 (한국 시간)
    python -m bot.cli ask "질문" --episode 5     질문 해석 테스트
    python -m bot.cli simulate                  임시 DB 로 전체 일정 모의 실행 (실제 게시 없음)
    python -m bot.cli export results.csv        결과 CSV 저장
    python -m bot.cli invite                    봇 초대 링크 (DISCORD_APPLICATION_ID 필요)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

from .config import Config, load_config
from .database import Database
from .game import GameService, build_service
from .scheduler import ReleaseScheduler, episode_schedule, kst, schedule_problems


def data_report(cfg: Config, game: GameService) -> str:
    lines: list[str] = []
    cat, bank = game.catalog, game.bank
    lines.append(f"개막: {kst(cfg.start_at_utc, cfg)} KST = {cfg.start_at_utc.isoformat()}")
    lines.append(
        f"서버 {cfg.guild_id} · 게시 채널 {cfg.event_channel_id} · 게임 채널 {cfg.game_channel_id}"
        f" · 테스트모드 {'ON' if cfg.test_mode else 'OFF'}"
    )
    problems = cat.validate() + bank.validate(set(cat.evidence))
    sched = episode_schedule(cfg, cat, game.db.schedule_overrides())
    problems += schedule_problems(cfg, sched)
    limit = cfg.section("media").get("upload_limit_mb", 10)
    missing_media = [ep.code for ep in cat.sorted_episodes() if ep.media_status(limit) in {"missing", "too_large"}]
    if missing_media:
        problems.append("영상 없음/용량 초과: " + ", ".join(missing_media))
    no_title = [ep.code for ep in cat.sorted_episodes() if not ep.title]
    if no_title:
        problems.append("제목 미입력: " + ", ".join(no_title))
    poster = cfg.resolve_media_path(cfg.section("event").get("poster_path"))
    if not (poster and poster.is_file()) and not cfg.section("event").get("poster_url"):
        problems.append("메인 포스터 파일 없음 (settings.json event.poster_path)")
    unconfirmed = [qid for qid, a in bank.answers.items() if not a.confirmed]
    lines.append(f"회차 {cat.episode_count} · 증거 {len(cat.evidence)} · 질문 {len(bank.questions)} (원작 확인 필요 {len(unconfirmed)})")
    lines.append("점검 결과: " + ("이상 없음" if not problems else f"{len(problems)}건 확인 필요"))
    lines += [f" - {p}" for p in problems]
    return "\n".join(lines)


class DryRunPublisher:
    def __init__(self):
        self.posts: list[str] = []
        self._id = 1000

    async def _post(self, label: str) -> tuple[int, int]:
        self._id += 1
        self.posts.append(label)
        return 1, self._id

    async def post_opening(self):
        return await self._post("개막 공지")

    async def post_episode(self, episode, new_evidence):
        ev = ", ".join(e.evidence_id for e in new_evidence)
        return await self._post(f"{episode.code}" + (f" + 증거 {ev}" if ev else ""))

    async def post_evidence(self, evidence):
        return await self._post(f"증거 {evidence.evidence_id}")

    async def post_ending(self):
        return await self._post("엔딩")

    async def find_marker(self, marker):
        return None

    async def notify_admins(self, text):
        self.posts.append(f"(운영 알림) {text}")


async def simulate(cfg: Config) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "sim.db")
        game = build_service(cfg, db)
        pub = DryRunPublisher()
        sch = ReleaseScheduler(cfg, db, game.catalog, pub, retry_delays=())
        sched = episode_schedule(cfg, game.catalog)
        times = sorted({cfg.start_at_utc, *[t for t in sched.values() if t]})
        for t in times:
            for step in (0, 1):
                now = t + timedelta(seconds=step * 20)
                before = len(pub.posts)
                await sch.tick(now)
                for p in pub.posts[before:]:
                    print(f"{kst(now, cfg)}  {p}")
        missing = [n for n, t in sched.items() if t is None]
        if missing:
            print(f"공개 시각 미정 회차: {', '.join(f'EP.{n:02d}' for n in missing)} — 자동 공개되지 않습니다.")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m bot.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("schedule")
    a = sub.add_parser("ask")
    a.add_argument("text")
    a.add_argument("--episode", type=int, default=12)
    sub.add_parser("simulate")
    e = sub.add_parser("export")
    e.add_argument("path")
    sub.add_parser("invite")
    args = p.parse_args(argv)

    cfg = load_config()
    if args.cmd == "invite":
        if not cfg.application_id:
            print("DISCORD_APPLICATION_ID 를 .env 에 입력하세요. (Developer Portal > General Information > Application ID)")
            sys.exit(1)
        from .main import invite_url
        print(invite_url(cfg.application_id))
        return
    if args.cmd == "simulate":
        asyncio.run(simulate(cfg))
        return

    game = build_service(cfg)
    if args.cmd == "check":
        print(data_report(cfg, game))
    elif args.cmd == "schedule":
        for n, t in episode_schedule(cfg, game.catalog, game.db.schedule_overrides()).items():
            print(f"EP.{n:02d}  {kst(t, cfg)}  {'공개됨' if game.db.is_posted('episode', n) else ''}")
    elif args.cmd == "ask":
        res = game.bank.ask(args.text, args.episode, bool(cfg.section("questions").get("answer_unconfirmed", False)))
        print(f"[EP.{args.episode:02d} 기준] {res.label}  (인식: {res.question_id or '-'}, {res.via})")
        if res.hint:
            print(res.hint)
    elif args.cmd == "export":
        from .rewards import export_csv
        Path(args.path).write_text(export_csv(game.db, game.db.current_episode()), encoding="utf-8")
        print(f"저장: {args.path}")


if __name__ == "__main__":
    main()
