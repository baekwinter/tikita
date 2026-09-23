import json
from datetime import timedelta

import pytest

from bot.game import GameError

from .conftest import open_event

CORRECT = {"q1": "반휘혈", "q2": "온하늘", "q3": "온하늘", "q4": "차세리",
           "q5": "두 사람의 오해를 풀어 주고 싶어서 예약 목록을 수정해 허락 없이 송출했다."}


def test_before_start_players_are_blocked(game):
    with pytest.raises(GameError) as e:
        game.register(10, "a")
    assert e.value.code == "before_start"


def test_join_reward_only_once(game, db):
    open_event(db, 1)
    assert game.register(10, "a")["gained"] == 10
    assert game.register(10, "a")["gained"] == 0
    assert db.points(10) == 10


async def test_question_flow_cooldown_duplicate_and_limit(game, db, clock, cfg):
    open_event(db, 12)
    r = await game.ask(10, "반휘혈은 온하늘을 좋아하나요?")
    assert r["verdict"] == "YES" and r["counted"] and r["gained"] == 5 + 2
    with pytest.raises(GameError) as e:
        await game.ask(10, "차세리가 범인이야?")
    assert e.value.code == "cooldown"
    clock.now += timedelta(seconds=30)
    dup = await game.ask(10, "반휘혈은 온하늘을 좋아하나요?")
    assert dup["duplicate"] and not dup["counted"]
    clock.now += timedelta(seconds=30)
    unclear = await game.ask(10, "오늘 날씨 어때?")
    assert unclear["verdict"] == "UNCLEAR" and not unclear["counted"]
    cfg.settings["questions"]["daily_limit"] = 1
    clock.now += timedelta(seconds=30)
    with pytest.raises(GameError) as e:
        await game.ask(10, "차세리가 범인이야?")
    assert e.value.code == "limit"


async def test_unreleased_answer_hides_memo_and_evidence(game, db):
    open_event(db, 2)
    r = await game.ask(10, "차세리가 범인이야?")
    assert r["verdict"] == "UNRELEASED"
    assert r["response_text"] == "" and r["related_evidence"] is None and r["matched"] is None


def test_locked_evidence_is_hidden_and_not_investigable(game, db):
    open_event(db, 1)
    board = game.evidence_board(10)
    locked = [e for e in board if e["locked"]]
    assert locked and all(set(e) == {"id", "episode", "locked"} for e in locked)
    with pytest.raises(GameError):
        game.investigate(10, "E-08")
    first = game.investigate(10, "E-01")
    assert first["new"] and first["gained"] == 3
    assert game.investigate(10, "e-01")["gained"] == 0


def test_watch_rewards_once_and_only_released(game, db):
    open_event(db, 2)
    assert game.mark_watched(10, 2)["gained"] == 5
    assert game.mark_watched(10, 2)["gained"] == 0
    with pytest.raises(GameError):
        game.mark_watched(10, 3)


def test_final_grading_and_attempt_limit(game, db):
    open_event(db, 12)
    wrong = dict(CORRECT, q4="남궁호", q5="남궁호가 장난으로 방송에 틀었다고 생각합니다.")
    r = game.submit_final(10, wrong)
    assert r["correct"] == 3 and not r["solved"] and "items" not in r  # 어떤 문항이 틀렸는지는 알려 주지 않음
    names_only = dict(CORRECT, q5="차세리가 했다고 생각합니다. 이유는 모르겠어요.")
    assert game.submit_final(10, names_only)["solved"] is False  # 이름만으로는 해결 불가
    assert game.submit_final(10, CORRECT)["solved"] is True
    with pytest.raises(GameError):
        game.submit_final(10, CORRECT)


def test_attempts_run_out(game, db):
    open_event(db, 12)
    bad = dict(CORRECT, q1="차세리")
    for _ in range(3):
        game.submit_final(11, bad)
    with pytest.raises(GameError) as e:
        game.submit_final(11, CORRECT)
    assert e.value.code == "no_attempts"


def test_final_rewards_granted_once_at_ending(game, db):
    open_event(db, 12)
    game.submit_final(10, CORRECT)
    before = db.points(10)
    first = game.finalize_all()
    assert first == 5 * 5 + 50
    assert game.finalize_all() == 0
    assert db.points(10) == before + first


def test_sealed_feedback_mode(game, db, cfg):
    open_event(db, 12)
    cfg.settings["final"]["feedback"] = "sealed"
    r = game.submit_final(10, CORRECT)
    assert "correct" not in r and "solved" not in r


def test_public_payloads_never_contain_answer_key(game, db):
    open_event(db, 3)
    game.register(10, "a")
    payload = json.dumps([game.case_info(), game.progress(10), game.evidence_board(10),
                          game.final_status(10)], ensure_ascii=False)
    for secret in ["model_answer", "rubric", "\"answer\"", "두 사람의 오해를 풀고 싶어"]:
        assert secret not in payload
    # 3화 기준으로 잠긴 증거의 제목/내용이 새지 않아야 한다
    assert "최종 자백" not in payload and "작가 노트" not in payload
