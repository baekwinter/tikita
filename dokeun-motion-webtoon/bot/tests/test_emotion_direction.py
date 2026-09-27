"""감정 질문 엔진 자연어 이해 고도화 검증.

- 지정 11개 자연어 질문 전부 매칭
- 확장 12개 자연어 변형 매칭
- 감정 방향(거절함 vs 거절당함, 주어 방향) 구분
- 남궁호 인지 범위: 확정(YES) vs 미확정(INFO), NO 아님
- 관계 표현(두 사람/서로) 인식, 대상 불명확 시 CLARIFY
"""
from __future__ import annotations

import pytest

from bot.character_questions import CharacterQuestionBank


@pytest.fixture(scope="module")
def cbank():
    return CharacterQuestionBank.load()


# ── 지정 11개 질문: 전부 매칭되고 올바른 kind ──────────────────────────────
@pytest.mark.parametrize("text,qid,kind", [
    ("온하늘이 반휘혈을 좋아하나요?", "V4Q021", "YES"),
    ("반휘혈도 온하늘을 좋아하나요?", "V4Q001", "YES"),
    ("두 사람은 서로 좋아하나요?", "V4Q081", "YES"),
    ("두 사람은 실제로 사귀고 있나요?", "V4Q004", "INFO"),
    ("차세리는 하늘을 좋아하나요?", "V4Q041", "YES"),
    ("차세리는 휘혈을 질투하나요?", "V4Q049", "NO"),
    ("차세리는 왜 두 사람의 오해를 해결하고 싶었나요?", "V4Q047", "INFO"),
])
def test_required_questions_match(cbank, text, qid, kind):
    m = cbank.match(text)
    assert m is not None, text
    assert m.question_id == qid, f"{text} -> {m.question_id}"
    assert m.kind == kind


# ── 감정 방향성: '거절했다고 생각'(주체) vs '거절당했다고 생각'(오해) ──────
def test_rejection_direction_is_distinguished(cbank):
    # 온하늘이 거절한 주체로 읽히는 표현 → 실제로 거절한 적 없음(NO)
    m1 = cbank.match("하늘은 휘혈을 거절했다고 생각하나요?")
    assert m1 is not None and m1.kind == "NO", m1
    # 온하늘이 거절당했다고 오해 → YES
    m2 = cbank.match("휘혈은 하늘이 자신을 거절했다고 생각하나요?")
    assert m2 is not None and m2.kind == "YES", m2
    # 반대쌍은 같은 항목으로 매칭되면 안 된다
    assert m1.question_id != m2.question_id


def test_reject_subject_vs_belief_pair(cbank):
    a = cbank.match("온하늘은 반휘혈을 거절했나요?")          # 거절함(주체)
    b = cbank.match("온하늘은 반휘혈에게 거절당했다고 생각했나요?")  # 거절당함(오해)
    assert a is not None and b is not None
    assert a.kind == "NO"        # CQ-REJECT-ACTUAL
    assert b.kind == "YES"       # V4Q025
    assert a.question_id != b.question_id


# ── 확장 자연어 변형 12개 ──────────────────────────────────────────────────
@pytest.mark.parametrize("text,expect_kind", [
    ("둘이 서로 좋아해?", "YES"),
    ("휘혈이랑 하늘이 쌍방이야?", "YES"),
    ("하늘이는 휘혈한테 마음 있어?", "YES"),
    ("세리는 왜 둘을 도와준 거야?", "INFO"),
    ("둘이 사귀는 사이야?", "INFO"),
    ("두 사람은 서로 좋아하지만 사귀지는 않는 거야?", "INFO"),
    ("세리가 하늘을 좋아하는 건 우정이야?", "YES"),
    ("세리는 휘혈을 질투해서 방송을 조작했어?", "NO"),
])
def test_extended_variations(cbank, text, expect_kind):
    m = cbank.match(text)
    assert m is not None, text
    assert m.kind == expect_kind, f"{text} -> {m.question_id}/{m.kind}"


def test_belief_dislike_direction(cbank):
    # 주어가 다르면 다른 항목(반휘혈 믿음 vs 온하늘 믿음)
    a = cbank.match("휘혈은 하늘이 자기를 싫어한다고 생각해?")
    b = cbank.match("하늘은 휘혈이 자기를 싫어한다고 생각해?")
    assert a is not None and b is not None
    assert a.question_id != b.question_id


# ── 남궁호 인지 범위: 정본 근거 기반 ───────────────────────────────────────
@pytest.mark.parametrize("text,qid,kind", [
    ("남궁호는 답장 파일이 있다는 걸 알았나요?", "CQ-NAM-REPLY-EXISTS", "YES"),
    ("남궁호는 답장이 전달되지 않은 걸 알았나요?", "CQ-NAM-DELIVERY-KNOW", "YES"),
    ("남궁호는 두 사람의 감정을 알고 있었나요?", "CQ-NAM-KNOW-FEELINGS", "INFO"),
    ("남궁호는 과거 답장의 의미를 이해하고 있었나요?", "CQ-NAM-REPLY-MEANING", "INFO"),
])
def test_namgung_awareness(cbank, text, qid, kind):
    m = cbank.match(text)
    assert m is not None, text
    assert m.question_id == qid
    assert m.kind == kind


def test_namgung_unconfirmed_is_not_no(cbank):
    # 상호 감정 인지/의미 이해는 확정되지 않았을 뿐 '아니다(NO)'가 아니다
    for text in ["남궁호는 두 사람의 감정을 알고 있었나요?",
                 "궁호는 하늘이 휘혈을 좋아한다는 걸 알았어?",
                 "궁호는 그 답장이 무슨 뜻인지 알았어?"]:
        m = cbank.match(text)
        assert m is not None and m.kind != "NO", f"{text} -> {m.kind if m else None}"


# ── 관계 표현 대상 해석 ────────────────────────────────────────────────────
def test_pair_marker_defaults_to_main_romance(cbank):
    m = cbank.match("두 사람은 서로 좋아하나요?")
    assert m is not None and m.question_id == "V4Q081"


def test_ambiguous_pair_without_concept_is_clarify(cbank):
    # 대상 없는 '무슨 사이/관계' 는 임의 추측 대신 CLARIFY
    for text in ["둘이 무슨 사이야?", "두 사람은 무슨 관계야?", "둘은 무슨 관계인가요?"]:
        m = cbank.match(text)
        assert m is not None and m.kind == "CLARIFY", f"{text} -> {m.kind if m else None}"


def test_clear_target_relationship_not_clarify(cbank):
    # 인물이 명시되면 CLARIFY 가 아니라 실제 항목으로 매칭
    m = cbank.match("반휘혈과 온하늘은 무슨 사이야?")
    assert m is not None and m.kind != "CLARIFY"


# ── 스테이지 게이팅: 남궁호 신규 항목은 ACT3 이후에만 답한다 ────────────────
def test_namgung_new_items_are_stage_gated(cbank):
    # E-03(ACT3) 미공개 상태에서는 UNRELEASED
    r = cbank.answer("남궁호는 답장 파일이 있다는 걸 알았나요?", released_evidence=set(), finale=False)
    assert r is not None and r.kind == "UNRELEASED"
    # E-03 공개 후에는 YES
    r2 = cbank.answer("남궁호는 답장 파일이 있다는 걸 알았나요?", released_evidence={"E-03"}, finale=False)
    assert r2 is not None and r2.kind == "YES"
