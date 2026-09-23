"""환경 변수(.env)와 게임 설정(data/settings.json)을 읽어 하나의 Config 객체로 묶는다.

토큰·API 키는 오직 환경 변수에서만 읽고, 어떤 로그에도 출력하지 않는다.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

BOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BOT_DIR.parent  # dokeun-motion-webtoon/
DATA_DIR = BOT_DIR / "data"

# 운영 서버 고정값 (지시서 14절). 테스트 서버에서만 .env 로 덮어쓸 수 있다.
PRODUCTION_GUILD_ID = 1539519514956398692
PRODUCTION_EVENT_CHANNEL_ID = 1548252787002048572

BOT_NAME = "도근고등학교 달빛 방송부"
GAME_TITLE = "고백이 잘못 송출되었습니다."


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str) -> int | None:
    raw = (os.getenv(name) or "").strip()
    return int(raw) if raw else None


def _env_id_list(name: str) -> set[int]:
    raw = os.getenv(name) or ""
    return {int(part) for part in raw.replace(" ", "").split(",") if part}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fp:
        return json.load(fp)


@dataclass
class Config:
    token: str | None
    application_id: int | None
    guild_id: int
    event_channel_id: int
    admin_user_ids: set[int]
    admin_role_ids: set[int]
    admin_allow_manage_guild: bool
    admin_alert_channel_id: int | None
    test_mode: bool
    db_path: Path
    ai_enabled: bool
    ai_model: str
    anthropic_api_key: str | None
    settings: dict[str, Any]
    tz: ZoneInfo = field(default_factory=lambda: ZoneInfo("Asia/Seoul"))
    start_at_override: datetime | None = None

    # ---- 파생 값 ---------------------------------------------------------
    @property
    def is_production_target(self) -> bool:
        return self.guild_id == PRODUCTION_GUILD_ID

    @property
    def start_at_utc(self) -> datetime:
        if self.start_at_override is not None:
            return self.start_at_override
        return parse_local(self.settings["event"]["start_at"], self.tz)

    def section(self, name: str) -> dict[str, Any]:
        return self.settings.get(name, {})

    def resolve_media_path(self, rel: str | None) -> Path | None:
        """episodes.json 등에 적힌 경로를 실제 파일 경로로 바꾼다 (프로젝트 폴더 기준)."""
        if not rel:
            return None
        p = Path(rel)
        return p if p.is_absolute() else (PROJECT_DIR / p)


def parse_local(value: str, tz: ZoneInfo) -> datetime:
    """'2026-09-24T00:00:00' 또는 '2026-09-24 00:00' 형식의 한국 시각을 UTC aware datetime 으로."""
    value = value.strip().replace(" ", "T")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc)


def load_settings(path: Path | None = None) -> dict[str, Any]:
    return load_json(path or DATA_DIR / "settings.json")


def load_config(env_file: Path | None = None) -> Config:
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file or BOT_DIR / ".env")
    except ImportError:  # python-dotenv 가 없어도 OS 환경 변수로 동작
        pass

    settings = load_settings()
    tz = ZoneInfo(settings["event"].get("timezone", "Asia/Seoul"))
    test_mode = _env_bool("DG_TEST_MODE")

    guild_id = PRODUCTION_GUILD_ID
    channel_id = PRODUCTION_EVENT_CHANNEL_ID
    start_override = None
    if test_mode:
        guild_id = _env_int("DG_TEST_GUILD_ID") or guild_id
        channel_id = _env_int("DG_TEST_CHANNEL_ID") or channel_id
        raw_start = (os.getenv("DG_TEST_START_AT") or "").strip()
        if raw_start:
            if guild_id == PRODUCTION_GUILD_ID:
                raise SystemExit(
                    "DG_TEST_START_AT 은 실제 도근도근 서버에서는 사용할 수 없습니다. "
                    "DG_TEST_GUILD_ID / DG_TEST_CHANNEL_ID 로 별도 테스트 서버를 지정하세요."
                )
            start_override = parse_local(raw_start, tz)

    db_path = Path(os.getenv("DG_DB_PATH") or BOT_DIR / "var" / "dalbit.db")
    if not db_path.is_absolute():
        db_path = BOT_DIR / db_path

    api_key = os.getenv("ANTHROPIC_API_KEY") or None
    return Config(
        token=os.getenv("DISCORD_TOKEN") or None,
        application_id=_env_int("DISCORD_APPLICATION_ID"),
        guild_id=guild_id,
        event_channel_id=channel_id,
        admin_user_ids=_env_id_list("DG_ADMIN_USER_IDS"),
        admin_role_ids=_env_id_list("DG_ADMIN_ROLE_IDS"),
        admin_allow_manage_guild=_env_bool("DG_ADMIN_ALLOW_MANAGE_GUILD", True),
        admin_alert_channel_id=_env_int("DG_ADMIN_ALERT_CHANNEL_ID"),
        test_mode=test_mode,
        db_path=db_path,
        ai_enabled=_env_bool("DG_AI_ENABLED") and bool(api_key),
        ai_model=os.getenv("DG_AI_MODEL") or "claude-opus-5",
        anthropic_api_key=api_key,
        settings=settings,
        tz=tz,
        start_at_override=start_override,
    )
