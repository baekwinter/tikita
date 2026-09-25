import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[2]  # dokeun-motion-webtoon/
sys.path.insert(0, str(ROOT))

from bot.config import (  # noqa: E402
    Config,
    PRODUCTION_EVENT_CHANNEL_ID,
    PRODUCTION_GAME_CHANNEL_ID,
    PRODUCTION_GUILD_ID,
    load_settings,
)
from bot.database import Database  # noqa: E402
from bot.evidence import Catalog  # noqa: E402
from bot.game import FinalKey, GameService  # noqa: E402
from bot.questions import QuestionBank  # noqa: E402
from bot.rewards import RewardService, RewardTable  # noqa: E402

START = datetime(2026, 9, 23, 15, 0, tzinfo=timezone.utc)


def make_config(tmp_path: Path, **settings_patch) -> Config:
    settings = load_settings()
    for dotted, value in settings_patch.items():
        section, key = dotted.split("__")
        settings[section][key] = value
    return Config(
        token=None, application_id=None, guild_id=PRODUCTION_GUILD_ID,
        event_channel_id=PRODUCTION_EVENT_CHANNEL_ID, game_channel_id=PRODUCTION_GAME_CHANNEL_ID,
        admin_user_ids={1}, admin_role_ids=set(), admin_allow_manage_guild=True, admin_alert_channel_id=None,
        test_mode=False, db_path=tmp_path / "t.db", ai_enabled=False, ai_model="", anthropic_api_key=None,
        settings=settings, tz=ZoneInfo("Asia/Seoul"),
    )


class Clock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def cfg(tmp_path):
    return make_config(tmp_path)


@pytest.fixture
def db(cfg):
    return Database(cfg.db_path)


@pytest.fixture
def catalog():
    return Catalog.load()


@pytest.fixture
def bank():
    return QuestionBank.load()


@pytest.fixture
def clock():
    return Clock(START)


@pytest.fixture
def game(cfg, db, catalog, bank, clock):
    return GameService(cfg, db, catalog, bank, RewardService(db, RewardTable.load()), FinalKey.load(), clock=clock)


def open_event(db: Database, episodes: int) -> None:
    """개막 공지와 1~N화가 게시된 상태로 만든다."""
    db.claim_release("opening", "main")
    db.complete_release("opening", "main", 1, 1)
    for n in range(1, episodes + 1):
        db.claim_release("episode", n)
        db.complete_release("episode", n, 1, 100 + n)
