"""SQLite 저장소. 봇과 웹 API 가 같은 DB 파일을 공유한다 (WAL 모드).

저장하는 개인 정보는 Discord 사용자 ID, 표시 이름, 게임 진행도뿐이다.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- 공식 게시 이력: kind = opening | episode | evidence | ending
CREATE TABLE IF NOT EXISTS releases (
    kind TEXT NOT NULL,
    item_id TEXT NOT NULL,
    status TEXT NOT NULL,              -- posting | posted
    released_at TEXT NOT NULL,
    channel_id INTEGER,
    message_id INTEGER,
    manual INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (kind, item_id)
);
CREATE TABLE IF NOT EXISTS schedule_overrides (
    episode_number INTEGER PRIMARY KEY,
    release_at TEXT NOT NULL,          -- UTC ISO
    updated_by INTEGER,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    display_name TEXT,
    joined_at TEXT NOT NULL,
    last_seen_at TEXT
);
CREATE TABLE IF NOT EXISTS rewards (
    user_id INTEGER NOT NULL,
    reward_key TEXT NOT NULL,
    points INTEGER NOT NULL,
    granted_at TEXT NOT NULL,
    PRIMARY KEY (user_id, reward_key)
);
CREATE TABLE IF NOT EXISTS player_evidence (
    user_id INTEGER NOT NULL,
    evidence_id TEXT NOT NULL,
    found_at TEXT NOT NULL,
    PRIMARY KEY (user_id, evidence_id)
);
CREATE TABLE IF NOT EXISTS player_episodes (
    user_id INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    watched_at TEXT NOT NULL,
    PRIMARY KEY (user_id, episode_number)
);
CREATE TABLE IF NOT EXISTS question_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    asked_at TEXT NOT NULL,
    normalized TEXT NOT NULL,
    question_text TEXT,                -- 매칭 실패한 질문만 (설정으로 끌 수 있음)
    question_id TEXT,
    result TEXT NOT NULL,
    counted INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'discord'
);
CREATE INDEX IF NOT EXISTS idx_question_user ON question_log(user_id, asked_at);
CREATE TABLE IF NOT EXISTS theories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    submitted_at TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    submitted_at TEXT NOT NULL,
    answers TEXT NOT NULL,             -- JSON
    correct_count INTEGER NOT NULL,
    solved INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
    user_id INTEGER PRIMARY KEY,
    body TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    key TEXT PRIMARY KEY,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    notified INTEGER NOT NULL DEFAULT 0
);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def from_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class Database:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=15)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=15000")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                yield self.conn
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(sql, params).fetchall()

    def one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    # ---- key/value 상태 ---------------------------------------------------
    def get_kv(self, key: str, default: Any = None) -> Any:
        row = self.one("SELECT value FROM kv WHERE key=?", (key,))
        return json.loads(row["value"]) if row else default

    def set_kv(self, key: str, value: Any) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT INTO kv(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value, ensure_ascii=False)),
            )

    @property
    def paused(self) -> bool:
        return bool(self.get_kv("paused", False))

    # ---- 공식 게시 이력 ---------------------------------------------------
    def get_release(self, kind: str, item_id: str | int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM releases WHERE kind=? AND item_id=?", (kind, str(item_id)))

    def claim_release(self, kind: str, item_id: str | int, manual: bool = False) -> bool:
        """게시 직전에 'posting' 으로 선점한다. 이미 기록이 있으면 False (중복 게시 방지)."""
        with self.tx() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO releases(kind, item_id, status, released_at, manual) VALUES(?,?,?,?,?)",
                (kind, str(item_id), "posting", iso(utcnow()), int(manual)),
            )
            return cur.rowcount == 1

    def complete_release(self, kind: str, item_id: str | int, channel_id: int | None, message_id: int | None) -> None:
        with self.tx() as c:
            c.execute(
                "UPDATE releases SET status='posted', channel_id=?, message_id=?, released_at=? WHERE kind=? AND item_id=?",
                (channel_id, message_id, iso(utcnow()), kind, str(item_id)),
            )

    def drop_release(self, kind: str, item_id: str | int) -> None:
        with self.tx() as c:
            c.execute("DELETE FROM releases WHERE kind=? AND item_id=?", (kind, str(item_id)))

    def forget_posts_outside(self, channel_id: int) -> int:
        """다른 채널에 게시된 개막·회차·공지·엔딩 기록을 지워 새 채널에 다시 게시되게 한다.
        (증거 수동 공개 기록과 참가자 진행도는 그대로 둔다.)"""
        with self.tx() as c:
            cur = c.execute(
                "DELETE FROM releases WHERE status='posted' AND channel_id IS NOT NULL AND channel_id != ? "
                "AND kind IN ('opening', 'episode', 'notice', 'ending')", (channel_id,))
            return cur.rowcount

    def releases(self, kind: str, status: str | None = "posted") -> list[sqlite3.Row]:
        if status is None:
            return self.query("SELECT * FROM releases WHERE kind=?", (kind,))
        return self.query("SELECT * FROM releases WHERE kind=? AND status=?", (kind, status))

    def released_episode_numbers(self) -> set[int]:
        return {int(r["item_id"]) for r in self.releases("episode")}

    def current_episode(self) -> int:
        """1화부터 연속으로 공개된 마지막 회차 번호 (없으면 0)."""
        released = self.released_episode_numbers()
        n = 0
        while n + 1 in released:
            n += 1
        return n

    def manually_released_evidence(self) -> set[str]:
        return {r["item_id"] for r in self.releases("evidence")}

    def is_posted(self, kind: str, item_id: str | int = "main") -> bool:
        row = self.get_release(kind, item_id)
        return bool(row and row["status"] == "posted")

    # ---- 일정 변경 --------------------------------------------------------
    def schedule_overrides(self) -> dict[int, datetime]:
        return {int(r["episode_number"]): from_iso(r["release_at"]) for r in self.query("SELECT * FROM schedule_overrides")}

    def set_schedule_override(self, episode: int, when: datetime | None, by: int | None) -> None:
        with self.tx() as c:
            if when is None:
                c.execute("DELETE FROM schedule_overrides WHERE episode_number=?", (episode,))
            else:
                c.execute(
                    "INSERT INTO schedule_overrides(episode_number, release_at, updated_by, updated_at) VALUES(?,?,?,?) "
                    "ON CONFLICT(episode_number) DO UPDATE SET release_at=excluded.release_at, "
                    "updated_by=excluded.updated_by, updated_at=excluded.updated_at",
                    (episode, iso(when), by, iso(utcnow())),
                )

    # ---- 참가자 -----------------------------------------------------------
    def get_player(self, user_id: int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM players WHERE user_id=?", (user_id,))

    def register_player(self, user_id: int, display_name: str | None) -> bool:
        """새로 등록되면 True."""
        now = iso(utcnow())
        with self.tx() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO players(user_id, display_name, joined_at, last_seen_at) VALUES(?,?,?,?)",
                (user_id, display_name, now, now),
            )
            if cur.rowcount == 0:
                c.execute(
                    "UPDATE players SET last_seen_at=?, display_name=COALESCE(?, display_name) WHERE user_id=?",
                    (now, display_name, user_id),
                )
            return cur.rowcount == 1

    # ---- 보상 -------------------------------------------------------------
    def grant(self, user_id: int, reward_key: str, points: int) -> bool:
        """같은 (user, key) 는 한 번만 지급된다. 새로 지급되면 True."""
        if points <= 0:
            return False
        with self.tx() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO rewards(user_id, reward_key, points, granted_at) VALUES(?,?,?,?)",
                (user_id, reward_key, points, iso(utcnow())),
            )
            return cur.rowcount == 1

    def points(self, user_id: int) -> int:
        row = self.one("SELECT COALESCE(SUM(points),0) AS p FROM rewards WHERE user_id=?", (user_id,))
        return int(row["p"])

    # ---- 증거/회차 --------------------------------------------------------
    def mark_evidence(self, user_id: int, evidence_id: str) -> bool:
        with self.tx() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO player_evidence(user_id, evidence_id, found_at) VALUES(?,?,?)",
                (user_id, evidence_id, iso(utcnow())),
            )
            return cur.rowcount == 1

    def found_evidence(self, user_id: int) -> set[str]:
        return {r["evidence_id"] for r in self.query("SELECT evidence_id FROM player_evidence WHERE user_id=?", (user_id,))}

    def mark_watched(self, user_id: int, episode: int) -> bool:
        with self.tx() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO player_episodes(user_id, episode_number, watched_at) VALUES(?,?,?)",
                (user_id, episode, iso(utcnow())),
            )
            return cur.rowcount == 1

    def watched_episodes(self, user_id: int) -> set[int]:
        return {int(r["episode_number"]) for r in self.query("SELECT episode_number FROM player_episodes WHERE user_id=?", (user_id,))}

    # ---- 질문 기록 --------------------------------------------------------
    def log_question(self, user_id: int, normalized: str, text: str | None, question_id: str | None,
                     result: str, counted: bool, source: str, at: datetime | None = None) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT INTO question_log(user_id, asked_at, normalized, question_text, question_id, result, counted, source) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (user_id, iso(at or utcnow()), normalized, text, question_id, result, int(counted), source),
            )

    def questions_since(self, user_id: int, since: datetime) -> int:
        row = self.one(
            "SELECT COUNT(*) AS n FROM question_log WHERE user_id=? AND counted=1 AND asked_at>=?",
            (user_id, iso(since)),
        )
        return int(row["n"])

    def total_questions(self, user_id: int) -> int:
        return int(self.one("SELECT COUNT(*) AS n FROM question_log WHERE user_id=? AND counted=1", (user_id,))["n"])

    def last_question_at(self, user_id: int) -> datetime | None:
        row = self.one("SELECT MAX(asked_at) AS t FROM question_log WHERE user_id=? AND counted=1", (user_id,))
        return from_iso(row["t"]) if row and row["t"] else None

    def recent_same_question(self, user_id: int, normalized: str, since: datetime) -> sqlite3.Row | None:
        return self.one(
            "SELECT * FROM question_log WHERE user_id=? AND normalized=? AND asked_at>=? ORDER BY id DESC LIMIT 1",
            (user_id, normalized, iso(since)),
        )

    def question_history(self, user_id: int, limit: int = 50) -> list[sqlite3.Row]:
        return self.query(
            "SELECT * FROM question_log WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)
        )

    # ---- 추리/정답 --------------------------------------------------------
    def add_theory(self, user_id: int, body: str) -> None:
        with self.tx() as c:
            c.execute("INSERT INTO theories(user_id, submitted_at, body) VALUES(?,?,?)", (user_id, iso(utcnow()), body))

    def theory_count(self, user_id: int) -> int:
        return int(self.one("SELECT COUNT(*) AS n FROM theories WHERE user_id=?", (user_id,))["n"])

    def add_submission(self, user_id: int, answers: dict, correct: int, solved: bool) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT INTO submissions(user_id, submitted_at, answers, correct_count, solved) VALUES(?,?,?,?,?)",
                (user_id, iso(utcnow()), json.dumps(answers, ensure_ascii=False), correct, int(solved)),
            )

    def submissions(self, user_id: int) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM submissions WHERE user_id=? ORDER BY id", (user_id,))

    # ---- 수사 노트 --------------------------------------------------------
    def get_note(self, user_id: int) -> sqlite3.Row | None:
        return self.one("SELECT * FROM notes WHERE user_id=?", (user_id,))

    def save_note(self, user_id: int, body: str) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT INTO notes(user_id, body, updated_at) VALUES(?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at",
                (user_id, body, iso(utcnow())),
            )

    # ---- 운영 알림 --------------------------------------------------------
    def raise_alert(self, key: str, message: str) -> bool:
        with self.tx() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO alerts(key, message, created_at) VALUES(?,?,?)", (key, message, iso(utcnow()))
            )
            return cur.rowcount == 1

    def clear_alert(self, key: str) -> None:
        with self.tx() as c:
            c.execute("DELETE FROM alerts WHERE key=?", (key,))

    def alerts(self) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM alerts ORDER BY created_at")

    def pending_alerts(self) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM alerts WHERE notified=0 ORDER BY created_at")

    def mark_alert_notified(self, key: str) -> None:
        with self.tx() as c:
            c.execute("UPDATE alerts SET notified=1 WHERE key=?", (key,))

    # ---- 결과 집계 --------------------------------------------------------
    def leaderboard(self, limit: int | None = None) -> list[sqlite3.Row]:
        sql = (
            "SELECT p.user_id, p.display_name, p.joined_at, COALESCE(SUM(r.points),0) AS points "
            "FROM players p LEFT JOIN rewards r ON r.user_id=p.user_id "
            "GROUP BY p.user_id ORDER BY points DESC, p.joined_at ASC"
        )
        if limit:
            sql += f" LIMIT {int(limit)}"
        return self.query(sql)

    def all_players(self) -> list[sqlite3.Row]:
        return self.query("SELECT * FROM players ORDER BY joined_at")
