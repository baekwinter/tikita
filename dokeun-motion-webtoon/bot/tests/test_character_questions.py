from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from bot.character_questions import CharacterQuestionBank
from .conftest import open_event


@pytest.mark.parametrize("text,qid", [
    ("온하늘이 반휘혈을 좋아하나요?", "V4Q021"),
    ("반휘혈이 온하늘을 좋아하나요?", "V4Q001"),
    ("둘은 서로 좋아하나요?", "V4Q081"),
    ("둘은 사귀고 있나요?", "V4Q004"),
    ("온하늘은 반휘혈을 거절했나요?", "CQ-REJECT-ACTUAL"),
    ("온하늘은 답장을 보냈다고 생각했나요?", "V4Q031"),
    ("반휘혈은 답장을 받은 적이 있나요?", "V4Q011"),
    ("온하늘은 휘혈이 자신을 싫어한다고 생각했나요?", "V4Q025"),
    ("반휘혈은 아직도 하늘을 좋아하나요?", "V4Q001"),
    ("차세리는 하늘을 좋아하나요?", "V4Q041"),
    ("차세리는 휘혈을 질투했나요?", "V4Q049"),
    ("세리와 하늘은 소꿉친구인가요?", "V4Q044"),
    ("차세리는 왜 방송을 조작했나요?", "V4Q054"),
    ("남궁호는 고백을 녹음했나요?", "CQ-NAM-REC"),
    ("남궁호는 음성을 편집했나요?", "V4Q069"),
    ("남궁호는 방송을 조작했나요?", "V4Q068"),
    ("고백 발신자와 송출 범인은 같은 사람인가요?", "CQ-SAME-PERSON"),
    ("2025년 답장이 전달되지 않은 이유는 무엇인가요?", "CQ-DELIVERY-CAUSE"),
    ("두 사람이 서로 거절했다고 오해한 이유는 무엇인가요?", "CQ-MISUNDERSTAND-CAUSE"),
    ("고백 파일과 과거 답장은 같은 파일인가요?", "V4Q096"),
])
def test_required_character_questions_match(text, qid):
    assert CharacterQuestionBank.load().match(text).question_id == qid


@pytest.mark.parametrize("text", [
    "하늘 휘혈 좋아함?",
    "하늘이가 휘혈이 좋아해?",
    "온하늘 반휘혈 좋아해요?",
    "하늘 마음이 휘혈한테 있는 거야?",
])
def test_haneul_romance_variations_are_consistent(text):
    item = CharacterQuestionBank.load().answer(text, set(), finale=False)
    assert item and item.question_id == "V4Q021" and item.kind == "YES"


def test_video_confirmed_seri_romance_and_unconfirmed_childhood(game, db):
    # 정본 v4 + 의도적 모호성: 중의적 애정("좋아해")은 1화부터 답하되 우정/연애를 확정하지 않는다.
    # 소꿉친구(확정 사실)는 10화 전까지 UNRELEASED.
    open_event(db, 1)
    result = asyncio.run(game.ask(77, "차세리는 온하늘을 좋아하나요?", display_name="검수자"))
    assert result["verdict"] == "YES"  # 중의적 애정 — 우정/연애 어느 쪽도 확정하지 않음
    assert "소꿉친구" not in result["response_text"] and "연애" not in result["response_text"]
    game.clock.now += timedelta(seconds=30)
    result = asyncio.run(game.ask(77, "세리와 하늘은 소꿉친구인가요?", display_name="검수자"))
    assert result["verdict"] == "UNRELEASED"  # 소꿉친구 확정은 10화 이후


def test_identity_question_is_sealed_before_finale(game, db):
    open_event(db, 12)
    result = asyncio.run(game.ask(78, "남궁호는 방송을 조작했나요?", display_name="검수자"))
    assert result["verdict"] == "SEALED"
    assert "/정답" in result["response_text"]


def test_stage_uses_released_evidence(game, db):
    open_event(db, 1)
    result = asyncio.run(game.ask(79, "남궁호는 음성을 편집했나요?", display_name="검수자"))
    assert result["verdict"] == "UNRELEASED"
    game.clock.now += timedelta(seconds=30)
    db.claim_release("evidence", "E-06", manual=True)
    db.complete_release("evidence", "E-06", 1, 999)
    result = asyncio.run(game.ask(79, "남궁호는 음성을 편집했나요?", display_name="검수자"))
    assert result["verdict"] == "YES"
