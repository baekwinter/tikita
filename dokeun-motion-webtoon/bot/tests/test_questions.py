import pytest

from bot.questions import Verdict


def test_data_is_consistent(bank, catalog):
    assert bank.validate(set(catalog.evidence)) == []
    assert catalog.validate() == []


@pytest.mark.parametrize("text", [
    "반휘혈은 온하늘을 좋아하나요?",
    "휘혈이는 하늘이를 좋아해?",
    "반휘혈이 온하늘에게 마음이 있나요?",
])
def test_same_meaning_questions_match_same_answer(bank, text):
    res = bank.ask(text, 12)
    assert res.question_id == "Q-LOVE" and res.verdict == Verdict.YES


@pytest.mark.parametrize("text,qid,verdict", [
    ("남궁호가 방송에 파일을 넣었나요?", "Q-NAM-BROADCAST", Verdict.NO),
    ("2025년에도 고백이 있었나요?", "Q-2025-CONFESS", Verdict.YES),
    ("온하늘은 답장을 남겼나요?", "Q-HANEUL-REPLY", Verdict.YES),
    ("둘이 서로 좋아했던 거야?", "Q-MUTUAL", Verdict.YES),
    ("차세리가 범인이야?", "Q-SERI-BROADCAST", Verdict.YES),
    ("세리가 허락 없이 틀었어?", "Q-SERI-NOPERM", Verdict.YES),
    ("세리가 허락 받고 틀었어?", "Q-SERI-PERM", Verdict.NO),
    ("답장이 전달됐나요?", "Q-REPLY-DELIVERED", Verdict.NO),
    ("남궁호는 공범이야?", "Q-NAM-ACCOMPLICE", Verdict.NO),
    ("온하늘이 답장을 송출했나요?", "Q-HANEUL-BROADCAST", Verdict.NO),
    ("온하늘의 답장도 방송됐나요?", "Q-REPLY-BROADCAST", Verdict.YES),
    ("실제 서버 멤버가 사건과 관련 있나요?", "Q-REAL", Verdict.IRRELEVANT),
])
def test_known_questions(bank, text, qid, verdict):
    res = bank.ask(text, 12)
    assert (res.question_id, res.verdict) == (qid, verdict)


def test_subject_direction_is_respected(bank):
    # '하늘이가 휘혈이를 좋아하나' 는 '휘혈이가 하늘이를 좋아하나' 와 다른 질문이다
    assert bank.ask("하늘이는 휘혈이를 좋아해?", 12).question_id == "Q-HANEUL-LOVE"
    assert bank.ask("반휘혈을 온하늘이 좋아하나요?", 12).question_id == "Q-HANEUL-LOVE"


def test_negative_questions_are_not_answered(bank):
    res = bank.ask("남궁호가 송출하지 않았나요?", 12)
    assert res.verdict == Verdict.NEGATIVE_FORM


def test_keyword_only_is_not_enough(bank):
    for text in ["고백한 사람이 누구야?", "오늘 날씨 어때?", "남궁호가 녹음을 도왔나요?", "하늘이가 고백했어?"]:
        assert bank.ask(text, 12).verdict == Verdict.UNCLEAR, text


def test_unreleased_information_is_gated(bank):
    assert bank.ask("차세리가 범인이야?", 3).verdict == Verdict.UNRELEASED
    assert bank.ask("차세리가 범인이야?", 11).verdict == Verdict.YES


def test_unconfirmed_questions_do_not_answer(bank):
    res = bank.ask("2025년 답장 전달을 누군가 고의로 막았나요?", 12)
    assert res.verdict == Verdict.UNCONFIRMED
    assert res.response_text == ""


def test_ai_picker_only_sees_answerable_questions_and_no_answers(bank):
    seen = {}

    def fake_ai(text, pool):
        seen["pool"] = pool
        return "Q-SERI-BROADCAST"  # 아직 답할 수 없는 질문을 골라도

    res = bank.ask("세리가 이 모든 일을 꾸몄나", 3, ai_pick=fake_ai)
    ids = {q.question_id for q in seen["pool"]}
    assert "Q-SERI-BROADCAST" not in ids          # 미공개 질문은 후보에 없음
    assert res.verdict == Verdict.UNCLEAR           # 후보 밖 선택은 무시
    assert all(not hasattr(q, "answer") for q in seen["pool"])
