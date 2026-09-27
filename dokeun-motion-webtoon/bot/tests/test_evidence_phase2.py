"""PHASE 2 증거·조사·추리 시스템 고도화 검증.

- 기존 증거 ID(E-01~E-08) 보존, 총 25개, 회차별 clues 정합
- 획득(evidence_found)과 조사(evidence_investigated) 보상 분리, 각 1회만
- 확정 스포일러(E-22, 세리 연애감정)는 12화 전 어떤 방법으로도 열리지 않음(수동 공개 포함)
- 미공개 관련 증거 ID/제목이 조사 결과로 새지 않음
- 조사 결과(investigation_result/inference)는 조사한 뒤에만 노출
- 운영진 전용 admin_note 는 참가자 payload 에 절대 없음
- 정본 불변(정답 판정 그대로, 남궁호 편집≠송출, 세리 연애≠동기)
"""
from __future__ import annotations

import json

import pytest

from bot.evidence import Catalog
from bot.game import GameError

from .conftest import open_event

OLD_IDS = {"E-01", "E-02", "E-03", "E-04", "E-05", "E-06", "E-07", "E-08"}


# ── 데이터 정합 ────────────────────────────────────────────────────────────
def test_existing_ids_preserved_and_total(catalog):
    assert OLD_IDS.issubset(set(catalog.evidence))
    assert 25 <= len(catalog.evidence) <= 35
    assert len(catalog.evidence) == 25


def test_catalog_validates_clean(catalog):
    assert catalog.validate() == []


def test_every_episode_has_evidence_and_types_balanced(catalog):
    from collections import Counter
    types = Counter(e.evidence_type for e in catalog.evidence.values())
    # 네 유형 모두 존재
    for t in ("digital", "emotion", "testimony", "decisive"):
        assert types[t] >= 3, (t, dict(types))


def test_old_evidence_fields_unchanged(catalog):
    # 기존 증거의 회차·제목이 그대로여야 기존 참가자 기록/기대가 유지된다
    assert catalog.evidence["E-01"].release_episode == 1
    assert catalog.evidence["E-08"].release_episode == 12
    assert catalog.evidence["E-06"].title == "남궁호 편집 요청 기록"


# ── 회차 게이팅 & 스포일러 차단 ─────────────────────────────────────────────
def test_new_evidence_released_by_episode(game, db):
    open_event(db, 9)
    ids = set(game.released_evidence_ids())
    # 9화까지 공개된 신규 증거는 포함, 그 이후 회차 증거는 미포함
    assert "E-23" in ids and "E-25" in ids  # 9화 공개
    assert "E-11" not in ids                # 11화
    assert "E-22" not in ids                # 12화(확정 스포일러)


def test_spoiler_level2_never_opens_before_episode_even_manually(game, db):
    open_event(db, 11)
    # 운영진 수동 공개를 시도해도 확정 스포일러(E-22)는 12화 전 열리지 않는다
    db.claim_release("evidence", "E-22")
    db.complete_release("evidence", "E-22", 1, 999)
    assert "E-22" not in set(game.released_evidence_ids())
    with pytest.raises(GameError) as e:
        game.investigate(70, "E-22")
    assert e.value.code == "locked"
    board = {i["id"]: i for i in game.evidence_board(70)}
    assert board["E-22"]["locked"] is True


def test_spoiler_level2_opens_at_episode12(game, db):
    open_event(db, 12)
    assert "E-22" in set(game.released_evidence_ids())
    data = game.investigate(70, "E-22")
    assert data["investigated"] and "연애" in data["investigation_result"]


def test_seri_childhood_evidence_at_10_but_not_romance(game, db):
    open_event(db, 10)
    ids = set(game.released_evidence_ids())
    assert "E-21" in ids       # 소꿉친구 증거는 10화 공개
    assert "E-22" not in ids   # 연애 감정 확정은 12화 전 비공개
    # 10화 소꿉친구 증거에는 '연애/짝사랑' 확정 표현이 없어야 한다
    data = game.investigate(71, "E-21")
    blob = data["investigation_result"] + data["inference"]
    assert "소꿉친구" in blob
    assert "연애" not in blob and "짝사랑" not in blob


# ── 획득 ≠ 조사, 보상 분리 & 중복 방지 ──────────────────────────────────────
def test_collect_and_investigate_rewards_are_separate_and_once(game, db):
    open_event(db, 6)
    first = game.investigate(80, "E-06")
    # 첫 조사: 획득 보상 3점 + 심화 조사 보상 2점 (기존 evidence_found 계약 유지)
    assert first["new"] is True and first["gained"] == 3
    assert first["investigate_gained"] == 2
    points_after_first = db.points(80)
    # 재조사: 두 보상 모두 0 (중복 지급 없음)
    again = game.investigate(80, "E-06")
    assert again["new"] is False and again["gained"] == 0 and again["investigate_gained"] == 0
    # 재조사로 포인트가 늘지 않는다 (증거 보상 중복 지급 없음)
    assert db.points(80) == points_after_first
    # evidence 관련 보상은 정확히 5점(획득 3 + 조사 2). join 등 다른 보상과 분리되어 계산.
    ev_points = sum(r["points"] for r in db.query(
        "SELECT points FROM rewards WHERE user_id=? AND reward_key LIKE 'evidence_%'", (80,)))
    assert ev_points == 5


def test_investigation_details_only_after_investigate(game, db):
    open_event(db, 6)
    # 보관함 목록(board)에는 조사 결과가 들어 있지 않다
    board = {i["id"]: i for i in game.evidence_board(81) if not i["locked"]}
    assert "investigation_result" not in board["E-06"]
    assert board["E-06"]["investigable"] is True
    # 조사하면 결과가 열린다
    data = game.investigate(81, "E-06")
    assert data["investigation_result"] and data["inference"]


def test_related_evidence_only_shows_released(game, db):
    open_event(db, 6)
    # E-06 은 E-11(11화, 미공개)과 연결되어 있으나, 조사 결과에는 공개된 것만 나온다
    data = game.investigate(82, "E-06")
    rel_ids = {r["id"] for r in data["related_evidence"]}
    assert "E-11" not in rel_ids  # 아직 미공개 → 누출 금지
    # 공개된 회차에서는 관련 증거가 노출된다
    open_event(db, 11)
    data2 = game.investigate(82, "E-04")
    rel_ids2 = {r["id"] for r in data2["related_evidence"]}
    assert "E-11" in rel_ids2 and "E-12" in rel_ids2


# ── 스포일러/정답 누출 차단 ─────────────────────────────────────────────────
def test_admin_note_never_in_public_payload(game, db):
    open_event(db, 12)
    for eid in ("E-01", "E-06", "E-08", "E-22"):
        data = game.investigate(90, eid)
        blob = json.dumps(data, ensure_ascii=False)
        assert "admin_note" not in blob
        assert "정답:" not in blob and "정답 확정" not in blob
        assert "Q-" not in blob  # 운영진 메모의 질문 ID 누출 없음


def test_locked_evidence_titles_not_leaked(game, db):
    open_event(db, 3)
    payload = json.dumps(game.evidence_board(91), ensure_ascii=False)
    # 3화 기준 미공개 증거의 제목이 새지 않아야 한다
    for hidden in ("최종 자백", "차세리가 오래 품어 온 마음", "예약 수정 계정 로그"):
        assert hidden not in payload


# ── 정본 불변 (증거 확장이 사건 판정을 바꾸지 않음) ─────────────────────────
async def test_case_answers_unchanged_after_phase2(game, db):
    from datetime import timedelta
    open_event(db, 12)
    async def ask(uid, q):
        game.clock.now += timedelta(seconds=30)
        return await game.ask(uid, q)
    assert (await ask(92, "차세리가 범인이야?"))["verdict"] == "YES"
    assert (await ask(92, "남궁호는 공범이야?"))["verdict"] == "NO"
    assert (await ask(92, "남궁호가 방송을 송출했나요?"))["verdict"] == "NO"
    assert (await ask(92, "남궁호가 음성을 편집했나요?"))["verdict"] == "YES"


def test_final_answer_unchanged(game, db):
    open_event(db, 12)
    correct = {"q1": "반휘혈", "q2": "온하늘", "q3": "온하늘", "q4": "차세리",
               "q5": "두 사람의 오해를 풀어 주려고 예약 목록을 수정해 허락 없이 송출했다."}
    assert game.submit_final(95, correct)["solved"] is True


# ── PHASE 2.1 회차별 /증거 UI ───────────────────────────────────────────────
def test_overview_groups_by_episode_with_counts(game, db):
    open_event(db, 10)
    ov = game.evidence_overview(70)
    assert ov["total_episodes"] == 12
    assert ov["total_evidence"] == 25
    assert ov["current_episode"] == 10
    # 회차별 묶음 + 개수
    by = {e["episode"]: e for e in ov["episodes"]}
    assert by[8]["count"] == 4 and by[9]["count"] == 3
    # 증거가 없는 회차는 목록에 없다(현재 모든 회차에 증거가 있으므로 12개 모두 존재)
    assert len(ov["episodes"]) == 12


def test_overview_hides_unreleased_episode_content(game, db):
    open_event(db, 10)
    ov = game.evidence_overview(70)
    by = {e["episode"]: e for e in ov["episodes"]}
    # EP11·EP12 는 미공개 → released False, 항목에 제목/내용이 없어야 한다
    for n in (11, 12):
        ep = by[n]
        assert ep["released"] is False
        assert ep["open_count"] == 0
        for item in ep["items"]:
            assert item["locked"] is True
            assert set(item.keys()) == {"id", "locked"}  # 제목·요약 누출 없음
    import json
    payload = json.dumps(ov, ensure_ascii=False)
    assert "차세리가 오래 품어 온 마음" not in payload  # E-22 제목
    assert "예약 수정 계정 로그" not in payload          # E-11 제목


def test_overview_status_distinguishes_found_and_investigated(game, db):
    open_event(db, 6)
    # 확보만 한 증거 vs 조사까지 한 증거 구분
    game.db.mark_evidence(70, "E-01")  # 확보만(보상 경로 안 탐)
    game.investigate(70, "E-06")        # 확보+조사
    ov = game.evidence_overview(70)
    by_item = {i["id"]: i for e in ov["episodes"] for i in e["items"] if not i["locked"]}
    assert by_item["E-01"]["found"] is True and by_item["E-01"]["investigated"] is False
    assert by_item["E-06"]["found"] is True and by_item["E-06"]["investigated"] is True
    # 미확보 공개 증거는 조사 가능 상태(자물쇠 아님)
    assert by_item["E-02"]["found"] is False and by_item["E-02"]["locked"] is False


def test_episode12_evidence_hidden_until_released_then_shown(game, db):
    open_event(db, 10)
    ov10 = {e["episode"]: e for e in game.evidence_overview(70)["episodes"]}
    assert ov10[12]["released"] is False and ov10[12]["open_count"] == 0
    open_event(db, 12)
    ov12 = {e["episode"]: e for e in game.evidence_overview(70)["episodes"]}
    # 12화 공개 후에는 E-08·E-22 모두 열린다(정본상 12화 시점 공개)
    assert ov12[12]["released"] is True and ov12[12]["open_count"] == 2
