"""정본 v4 감정 서사 정합성 + 회차 기반 공개 조건 검증.

- 남궁호→온하늘 짝사랑: 9화 공개 후 YES (그 전 UNRELEASED), 송출/범인 아님 분리
- 세리↔하늘 소꿉친구: 10화 공개 후 YES
- 세리→하늘 연애감정/자각 2년: 12화 공개 후 YES/INFO
- 온하늘 화답: 단정 불가(INFO)
- 사건 동기: 세리 감정≠조작 동기 (오해 해소 유지)
- Feature Flag 활성 ≠ 참가자 공개 (회차 게이팅 우선)
"""
from __future__ import annotations

import asyncio
from datetime import timedelta

from .conftest import open_event


def _ask(game, uid, text):
    game.clock.now += timedelta(seconds=30)
    return asyncio.run(game.ask(uid, text, display_name="검수자"))


# ── 남궁호 짝사랑: 회차 게이팅 ──────────────────────────────────────────────
def test_namgung_crush_gated_by_episode9(game, db):
    open_event(db, 8)
    r = _ask(game, 301, "남궁호는 온하늘을 좋아해?")
    assert r["verdict"] == "UNRELEASED", r


def test_namgung_crush_yes_after_episode9(game, db):
    open_event(db, 9)
    r = _ask(game, 302, "남궁호는 온하늘을 좋아해?")
    assert r["verdict"] == "YES", r
    # 감정과 행동 분리: 짝사랑이 곧 송출/범인이 아님을 답변에 담는다
    assert "송출" in r["response_text"] or "범인" in r["response_text"]


def test_namgung_crush_natural_variations(game, db):
    open_event(db, 9)
    for text in ["궁호가 하늘 짝사랑했어?", "남궁호도 하늘을 좋아했어?"]:
        r = _ask(game, 303, text)
        assert r["verdict"] == "YES", (text, r)


# ── 세리 소꿉친구: 10화 게이팅 ──────────────────────────────────────────────
def test_seri_childhood_gated_by_episode10(game, db):
    open_event(db, 9)
    r = _ask(game, 304, "세리와 하늘은 소꿉친구인가요?")
    assert r["verdict"] == "UNRELEASED", r


def test_seri_childhood_yes_after_episode10(game, db):
    open_event(db, 10)
    r = _ask(game, 305, "세리와 하늘은 소꿉친구인가요?")
    assert r["verdict"] == "YES", r
    assert "태어났을 때부터" in r["response_text"]
    r2 = _ask(game, 305, "세리와 하늘은 언제부터 알고 지냈어?")
    assert r2["verdict"] == "INFO" and "태어났을 때부터" in r2["response_text"]


# ── 중의적 애정 질문: 초반부터 답하되 우정/연애를 확정하지 않는다 ───────────
def test_ambiguous_affection_answers_early_without_confirming(game, db):
    # "좋아해/아껴"는 1화부터 답하되, 소꿉친구/연애를 확정하지 않는 중립 문구.
    open_event(db, 1)
    for q in ["차세리는 온하늘을 좋아하나요?", "세리는 하늘을 아끼나요?", "차세리는 온하늘을 아끼나요?"]:
        r = _ask(game, 306, q)
        assert r["verdict"] == "YES", (q, r)
        assert "소중" in r["response_text"] or "아껴" in r["response_text"]
        # 초반에는 소꿉친구/연애를 확정 설명하지 않는다
        assert "소꿉친구" not in r["response_text"]
        assert "연애" not in r["response_text"]


# ── 명시적 연애 질문만 12화 게이팅 ──────────────────────────────────────────
def test_explicit_romance_gated_by_episode12(game, db):
    open_event(db, 11)
    for q in ["세리는 하늘을 연애 감정으로 좋아하나요?", "세리는 하늘을 짝사랑하나요?",
              "세리는 언제부터 하늘을 좋아했어?"]:
        r = _ask(game, 307, q)
        assert r["verdict"] == "UNRELEASED", (q, r)


def test_explicit_romance_after_episode12(game, db):
    open_event(db, 12)
    r = _ask(game, 308, "세리는 하늘을 연애 감정으로 좋아하나요?")
    assert r["verdict"] == "YES" and "연애" in r["response_text"]
    r2 = _ask(game, 308, "세리가 하늘을 좋아하는 건 우정이야?")
    assert r2["verdict"] == "YES" and "연애" in r2["response_text"]
    r3 = _ask(game, 308, "세리는 언제부터 하늘을 좋아했어?")
    assert r3["verdict"] == "INFO" and "2년" in r3["response_text"]


def test_haneul_return_is_undetermined(game, db):
    open_event(db, 12)
    r = _ask(game, 308, "온하늘도 차세리를 연애 감정으로 좋아하나요?")
    assert r["verdict"] == "INFO"
    assert "단정" in r["response_text"] or "확정" in r["response_text"]


# ── 사건 동기 불변: 세리 감정 ≠ 조작 동기 ───────────────────────────────────
def test_seri_love_is_not_the_motive(game, db):
    open_event(db, 12)
    r = _ask(game, 309, "차세리는 하늘을 좋아해서 방송을 조작했어?")
    assert r["verdict"] == "INFO"
    # 질투/연애를 동기로 단정하지 않고 '오해 해소' 동기를 유지
    assert "오해" in r["response_text"]


def test_seri_jealousy_still_no(game, db):
    open_event(db, 12)
    r = _ask(game, 310, "차세리는 휘혈을 질투했나요?")
    assert r["verdict"] == "NO"


# ── 사건 정답 불변 확인 (감정선 변경이 사건 판정을 바꾸지 않음) ──────────────
def test_case_answers_unchanged(game, db):
    open_event(db, 12)
    # 최종 송출자는 여전히 차세리(YES), 남궁호는 공범 아님(NO)
    assert _ask(game, 311, "차세리가 범인이야?")["verdict"] == "YES"
    assert _ask(game, 311, "남궁호는 공범이야?")["verdict"] == "NO"


# ── 상시 공개 경로(/관계·/인물)는 회차 스포일러를 담지 않는다 ────────────────
def test_public_profile_paths_have_no_spoilers(game, db):
    # /관계, /인물은 회차 게이팅이 없는 상시 공개 프로필이므로 확정 스포일러가 없어야 한다.
    open_event(db, 1)
    spoilers = ["태어났을 때부터", "소꿉친구", "연애", "짝사랑", "자각"]
    rel = game.relationship_public("차세리", "온하늘")
    assert rel is not None
    for term in spoilers:
        assert term not in rel["public"], f"/관계에 스포일러 누출: {term}"
    reln = game.relationship_public("온하늘", "남궁호")
    for term in spoilers:
        assert term not in reln["public"], f"/관계에 스포일러 누출: {term}"
    for name in ("차세리", "온하늘", "남궁호", "반휘혈"):
        cp = game.character_public(name)
        for term in spoilers:
            assert term not in cp["summary"], f"/인물 {name}에 스포일러 누출: {term}"


# ── 중의적 애정과 명시적 연애가 서로 다른 공개 시점을 갖는다 ─────────────────
def test_ambiguous_vs_explicit_have_different_gates(game, db):
    # 8화: 중의적 애정은 답하되 명시적 연애는 아직 안 됨
    open_event(db, 8)
    amb = _ask(game, 312, "차세리는 온하늘을 아끼나요?")
    exp = _ask(game, 312, "세리는 하늘을 연애 감정으로 좋아하나요?")
    assert amb["verdict"] == "YES" and "연애" not in amb["response_text"]
    assert exp["verdict"] == "UNRELEASED"
