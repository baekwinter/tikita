"""사건 해결자(정답 맞춘 참가자) 운영 표시 검증.

- db.solvers(): solved=1 참가자만, 최초 해결 시각 순
- /운영 상태(status_embed)에 '🌕 사건 해결' 필드로 해결자 표시
- 해결자 없을 때 안내 문구
"""
from __future__ import annotations

from datetime import timedelta

from bot.commands import status_embed
from bot.main import DalbitBot

from .conftest import open_event

CORRECT = {"q1": "반휘혈", "q2": "온하늘", "q3": "온하늘", "q4": "차세리",
           "q5": "두 사람의 오해를 풀어 주려고 예약 목록을 수정해 허락 없이 송출했다."}


def test_solvers_lists_only_solved(game, db):
    open_event(db, 12)
    game.submit_final(11, CORRECT)                 # 해결
    game.submit_final(12, dict(CORRECT, q1="차세리"))  # 오답
    solvers = db.solvers()
    ids = {s["user_id"] for s in solvers}
    assert ids == {11}
    assert solvers[0]["best"] == 5


def test_solvers_ordered_by_first_solved(game, db):
    open_event(db, 12)
    game.submit_final(21, CORRECT)
    game.clock.now += timedelta(minutes=1)
    game.submit_final(22, CORRECT)
    order = [s["user_id"] for s in db.solvers()]
    assert order == [21, 22]  # 먼저 해결한 사람이 앞


def test_status_embed_shows_solvers(cfg):
    bot = DalbitBot(cfg)
    open_event(bot.db, 12)
    bot.game.submit_final(31, CORRECT)
    e = status_embed(bot)
    field = next(f for f in e.fields if "사건 해결" in f.name)
    assert "1명" in f"{field.name}"
    assert "<@31>" in field.value


def test_status_embed_no_solver_message(cfg):
    bot = DalbitBot(cfg)
    open_event(bot.db, 12)
    e = status_embed(bot)
    field = next(f for f in e.fields if "사건 해결" in f.name)
    assert "아직 정답을 맞힌 참가자가 없습니다" in field.value
