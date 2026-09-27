"""감정 질문이 game.ask() 흐름에서 올바르게 verdict/횟수 처리되는지 검증."""
from __future__ import annotations

import asyncio

from .conftest import open_event


def test_pair_question_answers_via_game(game, db):
    open_event(db, 12)
    r = asyncio.run(game.ask(201, "두 사람은 서로 좋아하나요?", display_name="검수자"))
    assert r["verdict"] == "YES"
    assert r["counted"] is True


def test_direction_question_not_reversed_via_game(game, db):
    open_event(db, 12)
    # 온하늘이 거절한 주체로 읽히는 질문 → NO (정반대 YES 로 답하면 안 됨)
    r = asyncio.run(game.ask(202, "하늘은 휘혈을 거절했다고 생각하나요?", display_name="검수자"))
    assert r["verdict"] == "NO"


def test_namgung_meaning_is_info_not_no(game, db):
    open_event(db, 12)  # ACT3(E-03) 공개된 상태
    r = asyncio.run(game.ask(203, "남궁호는 과거 답장의 의미를 이해하고 있었나요?", display_name="검수자"))
    assert r["verdict"] == "INFO"


def test_cause_question_returns_info(game, db):
    open_event(db, 12)
    r = asyncio.run(game.ask(204, "세리는 왜 둘을 도와준 거야?", display_name="검수자"))
    assert r["verdict"] == "INFO"


def test_ambiguous_pair_asks_for_clarification(game, db):
    """대상 없는 관계 질문은 CLARIFY 로 구체적 안내를 준다 (임의로 휘혈·하늘로 단정하지 않음)."""
    open_event(db, 12)
    r = asyncio.run(game.ask(205, "둘이 무슨 사이야?", display_name="검수자"))
    assert r["verdict"] == "CLARIFY"
    # 구체적 안내가 UNCLEAR 기본 문구가 아니라 대상 확인 문구여야 한다
    assert "누구" in r["hint"]
    # 해석 실패류이므로 질문 횟수를 차감하지 않는다
    assert r["counted"] is False


def test_clear_target_relationship_is_answered(game, db):
    """대상이 명확하면 기존 감정/관계 DB에서 정상 답변."""
    open_event(db, 12)
    r = asyncio.run(game.ask(206, "반휘혈과 온하늘은 무슨 사이야?", display_name="검수자"))
    assert r["verdict"] in {"YES", "NO", "INFO"}
    assert r["verdict"] != "CLARIFY"
