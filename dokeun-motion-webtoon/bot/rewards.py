"""달빛 수사 포인트.

- 지급표는 data/rewards.json 에서 관리한다.
- 같은 보상 키는 DB 고유 키로 한 사람에게 한 번만 지급된다 (중복 지급 방지).
- 다른 디스코드 레벨링 봇의 EXP 를 임의로 바꾸지 않는다. 공식 API 가 확인되면
  ExternalRewardSink 를 구현해 연결한다.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import DATA_DIR, load_json
from .database import Database

log = logging.getLogger(__name__)


class ExternalRewardSink(Protocol):
    def grant(self, user_id: int, points: int, reason: str) -> None: ...


@dataclass
class RewardTable:
    currency: str
    points: dict[str, int]

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "RewardTable":
        doc = load_json(data_dir / "rewards.json")
        return cls(currency=doc.get("currency_name", "달빛 수사 포인트"), points=dict(doc["points"]))


class RewardService:
    def __init__(self, db: Database, table: RewardTable, sink: ExternalRewardSink | None = None):
        self.db = db
        self.table = table
        self.sink = sink

    @property
    def currency(self) -> str:
        return self.table.currency

    def grant(self, user_id: int, kind: str, suffix: str | None = None) -> int:
        """kind 는 rewards.json 의 points 키. suffix 로 '회차별/일자별' 고유 키를 만든다. 지급된 포인트(중복이면 0)."""
        pts = int(self.table.points.get(kind, 0))
        key = f"{kind}:{suffix}" if suffix else kind
        if pts <= 0 or not self.db.grant(user_id, key, pts):
            return 0
        if self.sink:
            try:
                self.sink.grant(user_id, pts, key)
            except Exception:
                log.exception("외부 보상 연동 실패 (이벤트 포인트는 정상 지급됨)")
        return pts

    def total(self, user_id: int) -> int:
        return self.db.points(user_id)


def export_csv(db: Database, current_episode: int) -> str:
    """운영진용 결과 CSV (UTF-8 BOM, 엑셀 호환)."""
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf)
    w.writerow(["순위", "user_id", "표시이름", "포인트", "참가시각(UTC)", "시청 회차 수", "확보 증거 수", "질문 수",
                "추리 제출 수", "정답 제출 수", "최고 정답 수", "사건 해결", "마지막 정답 제출 내용"])
    for rank, row in enumerate(db.leaderboard(), start=1):
        uid = row["user_id"]
        subs = db.submissions(uid)
        best = max((s["correct_count"] for s in subs), default=0)
        solved = any(s["solved"] for s in subs)
        w.writerow([
            rank, str(uid), row["display_name"] or "", row["points"], row["joined_at"],
            len(db.watched_episodes(uid)), len(db.found_evidence(uid)), db.total_questions(uid),
            db.theory_count(uid), len(subs), best, "Y" if solved else "", subs[-1]["answers"] if subs else "",
        ])
    return buf.getvalue()
