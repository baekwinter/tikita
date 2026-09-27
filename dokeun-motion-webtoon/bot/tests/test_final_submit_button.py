"""PHASE 2.2 최종 정답 제출 버튼/패널 검증.

- /증거 보관함 하단 '📝 최종 정답 제출하기' 버튼 존재
- 고정 정답 패널(final_panel_embed/view) 구성 + finalsubmit 영구 버튼(dg:finalsubmit) 복구
- 버튼/모달을 여는 것만으로는 제출 횟수 차감 없음, 취소 시 유지
- 정상 제출 시에만 기존 submit_final 판정·기록, 3회 제한, 시점 게이팅
- 중복 제출로 제출 보상(final_submit) 중복 지급 없음
- 기존 /정답 흐름(FinalView→FinalReasonModal) 유지, /증거 회차 선택/조사 유지
"""
from __future__ import annotations

import discord
import pytest

from bot import ui
from bot.game import GameError
from bot.main import DalbitBot

from .conftest import open_event

CORRECT = {"q1": "반휘혈", "q2": "온하늘", "q3": "온하늘", "q4": "차세리",
           "q5": "두 사람의 오해를 풀어 주려고 예약 목록을 수정해 허락 없이 송출했다."}


# ── 버튼/패널 구성 ──────────────────────────────────────────────────────────
def test_evidence_view_has_final_submit_button(cfg, db):
    open_event(db, 10)
    bot = DalbitBot(cfg)
    view = ui.EvidenceSelectView(bot, owner_id=7, episode=None)
    labels = [getattr(c, "label", None) for c in view.children]
    assert any(l and "최종 정답 제출" in l for l in labels)


def test_final_panel_embed_and_view():
    e = ui.final_panel_embed()
    assert e.title == "🌙 최종 수사 보고서"
    assert "3회" in (e.description or "")
    view = ui.final_panel_view()
    # 정답 제출 영구 버튼(dg:finalsubmit) 하나
    ids = [getattr(getattr(c, "item", None), "custom_id", None) or getattr(c, "custom_id", None) for c in view.children]
    assert any(cid == "dg:finalsubmit" for cid in ids)
    assert view.timeout is None  # 영구 View


def test_finalsubmit_action_registered_in_labels():
    # 영구 버튼 액션 라벨/스타일이 등록되어 있어야 from_custom_id 복구 시 생성 가능
    assert "finalsubmit" in ui.ACTION_LABELS
    label, _ = ui.ACTION_LABELS["finalsubmit"]
    assert "정답 제출" in label


def test_public_button_custom_id_pattern_matches_finalsubmit():
    import re
    tmpl = ui.PublicButton.__discord_ui_model_fields__ if hasattr(ui.PublicButton, "__discord_ui_model_fields__") else None
    # custom_id 가 템플릿과 일치해야 재시작 후 복구된다
    btn = ui.PublicButton("finalsubmit")
    assert btn.item.custom_id == "dg:finalsubmit"
    assert re.fullmatch(r"dg:(?P<action>[a-z]+)(?::(?P<arg>\d+))?", "dg:finalsubmit")


# ── 제출 횟수/보상 보호 (버튼·모달은 game 로직으로 귀결) ─────────────────────
def test_opening_flow_does_not_consume_attempt(game, db):
    open_event(db, 12)
    # 버튼/모달을 여는 것은 game 상태를 바꾸지 않는다: final_status 만 조회
    st1 = game.final_status(50)
    st2 = game.final_status(50)
    assert st1["attempts"] == 0 and st2["attempts"] == 0
    # 실제 제출해야만 attempts 증가
    game.submit_final(50, CORRECT)
    assert game.final_status(50)["attempts"] == 1


def test_max_three_attempts_via_submit(game, db):
    open_event(db, 12)
    bad = dict(CORRECT, q1="차세리")
    for _ in range(3):
        game.submit_final(60, bad)
    assert game.final_status(60)["attempts"] == 3
    with pytest.raises(GameError) as e:
        game.submit_final(60, CORRECT)
    assert e.value.code == "no_attempts"


def test_submit_blocked_before_open(game, db, cfg):
    cfg.settings["final"]["open_from_episode"] = 12
    open_event(db, 11)
    st = game.final_status(61)
    assert st["open"] is False
    with pytest.raises(GameError) as e:
        game.submit_final(61, CORRECT)
    assert e.value.code == "not_open"


def test_final_submit_reward_not_double_paid(game, db):
    open_event(db, 12)
    wrong = dict(CORRECT, q1="온하늘")  # 오답으로 solved 안 됨 → 계속 제출 가능
    game.submit_final(62, wrong)
    after_first = db.points(62)
    game.submit_final(62, wrong)
    after_second = db.points(62)
    # 두 번째 제출에서 final_submit 보상이 또 지급되지 않는다
    assert after_second == after_first


def test_solved_blocks_further_submission(game, db):
    open_event(db, 12)
    game.submit_final(63, CORRECT)
    assert game.final_status(63)["solved"] is True
    with pytest.raises(GameError) as e:
        game.submit_final(63, CORRECT)
    assert e.value.code == "solved"


# ── 기존 흐름/기능 유지 ─────────────────────────────────────────────────────
def test_existing_final_view_and_modal_intact(cfg, db):
    open_event(db, 12)
    bot = DalbitBot(cfg)
    view = ui.FinalView(bot, owner_id=7)
    # Q1~Q4 Select 4개 + 제출 버튼
    selects = [c for c in view.children if isinstance(c, discord.ui.Select)]
    assert len(selects) == 4
    modal = ui.FinalReasonModal({"q1": "반휘혈", "q2": "온하늘", "q3": "온하늘", "q4": "차세리"})
    # Modal 입력란: 이유(필수) + 근거 증거(선택)
    assert modal.reason.required is True
    assert modal.story.required is False


def test_evidence_view_keeps_episode_and_evidence_selects(cfg, db):
    open_event(db, 10)
    bot = DalbitBot(cfg)
    view = ui.EvidenceSelectView(bot, owner_id=7, episode=8)
    selects = [c for c in view.children if isinstance(c, discord.ui.Select)]
    # 회차 선택 + 해당 회차 증거 선택 (2개)
    assert len(selects) >= 2


# ── 정정: 수사본부 공지의 새 버튼 → 최종 수사 보고서(ephemeral) → 정답 제출 ────
def test_notice_view_includes_finalreport_button(cfg, db):
    # post_notice 가 쓰는 액션 구성에 finalreport(새 버튼)가 포함된다
    bot = DalbitBot(cfg)
    view = ui.public_view(bot, ["start", "episodes", "progress", "evidence", "final", "finalreport"])
    ids = [getattr(getattr(c, "item", None), "custom_id", None) for c in view.children]
    # 기존 5개 버튼 유지 + 새 버튼
    assert "dg:start" in ids and "dg:final" in ids
    assert "dg:finalreport" in ids
    # 기존 버튼 개수 보존(5) + 신규 1
    dg_ids = [i for i in ids if i and i.startswith("dg:")]
    assert len(dg_ids) == 6


def test_finalreport_action_registered_and_recovers():
    import re
    assert "finalreport" in ui.ACTION_LABELS
    btn = ui.PublicButton("finalreport")
    assert btn.item.custom_id == "dg:finalreport"
    assert re.fullmatch(r"dg:(?P<action>[a-z]+)(?::(?P<arg>\d+))?", "dg:finalreport")
    # 기존 finalsubmit 과 custom_id 가 충돌하지 않는다
    assert ui.PublicButton("finalsubmit").item.custom_id != btn.item.custom_id


def test_final_report_screen_reuses_panel_embed_and_view():
    # 3단계 중 2단계 화면은 기존 final_panel_embed/view 를 재사용한다
    e = ui.final_panel_embed()
    v = ui.final_panel_view()
    assert e.title == "🌙 최종 수사 보고서"
    ids = [getattr(getattr(c, "item", None), "custom_id", None) for c in v.children]
    assert ids == ["dg:finalsubmit"]  # 2단계 화면의 버튼은 기존 정답 흐름으로 연결


def test_five_original_buttons_unchanged(cfg, db):
    bot = DalbitBot(cfg)
    view = ui.public_view(bot, ["start", "episodes", "progress", "evidence", "final", "finalreport"])
    ids = [getattr(getattr(c, "item", None), "custom_id", None) for c in view.children]
    for original in ("dg:start", "dg:episodes", "dg:progress", "dg:evidence", "dg:final"):
        assert original in ids
