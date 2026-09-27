"""달빛 수사 포인트 공개 랭킹 검증.

- 포인트 내림차순 정렬, 동점은 참가 시각 순
- 본인 등수/포인트 반환(개인 확인용), 상위권 밖이면 별도 표기
- 공개 랭킹 payload/embed 에 스포일러(정답 여부·증거 내용) 없음
- 참가자 없음 처리
- 채널 게시용(public) 과 개인용(본인 강조) 구분
"""
from __future__ import annotations

import json

from bot import ui

from .conftest import open_event


def _seed(game, db):
    open_event(db, 12)
    # 세 참가자에게 서로 다른 포인트 부여 (join 10점씩 기본)
    game.register(101, "앨리스")
    game.register(102, "밥")
    game.register(103, "캐럴")
    game.rewards.grant(101, "case_solved")      # +50
    game.rewards.grant(102, "watch_episode", "1")  # +5
    # 캐럴은 join 만 (10)


def test_ranking_sorted_desc(game, db):
    _seed(game, db)
    data = game.ranking(top=10)
    pts = [e["points"] for e in data["top"]]
    assert pts == sorted(pts, reverse=True)
    assert data["top"][0]["user_id"] == 101  # 60점(10+50)로 1위
    assert data["total_players"] == 3


def test_ranking_reports_my_rank(game, db):
    _seed(game, db)
    data = game.ranking(top=10, user_id=103)
    assert data["me"] is not None
    assert data["me"]["user_id"] == 103
    # 밥(15) > 캐럴(10) 이므로 캐럴은 3위
    assert data["me"]["rank"] == 3


def test_ranking_top_limit_and_me_outside(game, db):
    open_event(db, 12)
    for i in range(1, 8):
        game.register(200 + i, f"수사관{i}")
        # 뒤 번호일수록 포인트 많게 (각 grant 는 고유 키라 중복 방지에 걸리지 않음)
        for j in range(i):
            game.rewards.grant(200 + i, "daily_theory", f"u{i}-{j}")  # +5 each unique key
    # 1등 확인용 낮은 포인트 참가자
    data = game.ranking(top=3, user_id=201)
    assert len(data["top"]) == 3
    assert data["me"]["user_id"] == 201
    # 201 은 포인트가 가장 낮아 top3 밖
    assert data["me"]["rank"] > 3


def test_ranking_embed_has_no_spoilers(game, db):
    _seed(game, db)
    game.submit_final(101, {"q1": "반휘혈", "q2": "온하늘", "q3": "온하늘", "q4": "차세리",
                            "q5": "오해를 풀려고 예약을 수정해 무단 송출했다."})
    e = ui.ranking_embed(game, user_id=101, top=10, public=True)
    blob = json.dumps(e.to_dict(), ensure_ascii=False)
    for secret in ("정답", "범인", "차세리가", "오해", "solved", "송출", "E-0"):
        assert secret not in blob, secret
    # 이름·포인트는 있다
    assert "앨리스" in blob and "점" in blob


def test_ranking_embed_empty(game, db):
    open_event(db, 1)
    e = ui.ranking_embed(game, user_id=None, top=10, public=True)
    assert "아직 참가자가 없습니다" in (e.description or "")


def test_public_vs_personal_marker(game, db):
    _seed(game, db)
    personal = ui.ranking_embed(game, user_id=101, top=10, public=False)
    public = ui.ranking_embed(game, user_id=101, top=10, public=True)
    assert "◀ 나" in (personal.description or "")
    assert "◀ 나" not in (public.description or "")
