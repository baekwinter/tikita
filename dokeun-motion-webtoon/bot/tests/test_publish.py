import pytest

from bot.scheduler import ALREADY, FAILED, HELD, POSTED, ReleaseScheduler, TransientError

from .conftest import START


class FakePublisher:
    def __init__(self, fail_times=0, fatal=False):
        self.posts = []
        self.markers = {}
        self.alerts = []
        self.fail_times = fail_times
        self.fatal = fatal
        self._id = 500

    async def _post(self, label, mk):
        if self.fatal:
            raise PermissionError("Missing Access")
        if self.fail_times:
            self.fail_times -= 1
            raise TransientError("503")
        self._id += 1
        self.posts.append(label)
        self.markers[mk] = self._id
        return 1, self._id

    async def post_opening(self):
        return await self._post("opening", "ref:opening:main")

    async def post_episode(self, ep, new_evidence):
        return await self._post(f"ep{ep.number}", f"ref:episode:{ep.number}")

    async def post_evidence(self, ev):
        return await self._post(ev.evidence_id, f"ref:evidence:{ev.evidence_id}")

    async def post_ending(self):
        return await self._post("ending", "ref:ending:main")

    async def find_marker(self, mk):
        return self.markers.get(mk)

    async def notify_admins(self, text):
        self.alerts.append(text)


@pytest.fixture
def with_video(catalog):
    for ep in catalog.episodes.values():
        ep.video_url = f"https://example.invalid/ep{ep.number}"
    return catalog


def sched(cfg, db, catalog, pub):
    return ReleaseScheduler(cfg, db, catalog, pub, retry_delays=(0, 0))


async def test_opening_and_first_episode_once_even_after_restart(cfg, db, with_video):
    pub = FakePublisher()
    await sched(cfg, db, with_video, pub).tick(START)
    assert pub.posts == ["opening", "ep1"]
    # 재시작(새 스케줄러 인스턴스) 후에도 중복 게시 없음
    await sched(cfg, db, with_video, pub).tick(START)
    await sched(cfg, db, with_video, pub).tick(START)
    assert pub.posts == ["opening", "ep1"]


async def test_missing_video_holds_and_alerts(cfg, db, catalog):
    ep1 = catalog.episodes[1]
    ep1.video_url = None  # 영상 파일·링크가 모두 없는 상황
    ep1.video_path = None
    pub = FakePublisher()
    await sched(cfg, db, catalog, pub).tick(START)
    assert pub.posts == ["opening"]
    assert any("EP.01" in a for a in pub.alerts)
    await sched(cfg, db, catalog, pub).tick(START)
    assert len(pub.alerts) == 1  # 같은 알림을 반복하지 않음


async def test_interrupted_post_is_recovered_from_channel_history(cfg, db, with_video):
    pub = FakePublisher()
    pub.markers["ref:opening:main"] = 999      # 채널에는 올라갔지만
    db.claim_release("opening", "main")         # DB 는 'posting' 에서 멈춘 상태
    await sched(cfg, db, with_video, pub).tick(START)
    assert "opening" not in pub.posts
    assert db.get_release("opening", "main")["message_id"] == 999


async def test_interrupted_post_not_in_channel_is_reposted(cfg, db, with_video):
    pub = FakePublisher()
    db.claim_release("opening", "main")
    await sched(cfg, db, with_video, pub).tick(START)
    assert pub.posts[0] == "opening"


async def test_transient_errors_retry(cfg, db, with_video):
    pub = FakePublisher(fail_times=2)
    res = await sched(cfg, db, with_video, pub).publish_opening()
    assert res == POSTED and pub.posts == ["opening"]


async def test_fatal_error_drops_claim_and_alerts(cfg, db, with_video):
    pub = FakePublisher(fatal=True)
    res = await sched(cfg, db, with_video, pub).publish_opening()
    assert res == FAILED
    assert db.get_release("opening", "main") is None
    assert pub.alerts


async def test_manual_episode_order_and_duplicates(cfg, db, with_video):
    pub = FakePublisher()
    s = sched(cfg, db, with_video, pub)
    assert await s.publish_episode(1) == "no_opening"
    await s.publish_opening()
    assert await s.publish_episode(3) == "order"
    assert await s.publish_episode(1) == POSTED
    assert await s.publish_episode(1) == ALREADY


async def test_manual_evidence_release(cfg, db, with_video):
    pub = FakePublisher()
    s = sched(cfg, db, with_video, pub)
    await s.publish_opening()
    await s.publish_episode(1)
    assert await s.publish_evidence("E-01") == "already_open"
    assert await s.publish_evidence("E-05") == POSTED
    assert "E-05" in db.manually_released_evidence()


async def test_paused_event_does_not_post(cfg, db, with_video):
    db.set_kv("paused", True)
    pub = FakePublisher()
    await sched(cfg, db, with_video, pub).tick(START)
    assert pub.posts == []


async def test_auto_start_late_posts_opening_and_ep1_without_video_once(tmp_path, catalog):
    from datetime import timedelta

    from bot.database import Database

    from .conftest import make_config

    cfg = make_config(tmp_path, event__auto_start_late=True)
    db = Database(cfg.db_path)
    pub = FakePublisher()
    late = START + timedelta(days=1, hours=18)  # 개막 12시간 유예도 훌쩍 지남
    s = sched(cfg, db, catalog, pub)
    await s.tick(late)
    assert pub.posts == ["opening", "ep1"]
    await s.tick(late + timedelta(minutes=1))
    await sched(cfg, db, catalog, pub).tick(late + timedelta(minutes=2))  # 재시작 후에도
    assert pub.posts == ["opening", "ep1"]


async def test_auto_start_late_respects_pause(tmp_path, catalog):
    from datetime import timedelta

    from bot.database import Database

    from .conftest import make_config

    cfg = make_config(tmp_path, event__auto_start_late=True)
    db = Database(cfg.db_path)
    db.set_kv("paused", True)
    pub = FakePublisher()
    await sched(cfg, db, catalog, pub).tick(START + timedelta(days=1))
    assert pub.posts == []


async def test_hq_notice_then_opening_then_release_through_ep4(tmp_path, catalog):
    from datetime import timedelta

    from bot.database import Database

    from .conftest import make_config

    cfg = make_config(tmp_path, event__auto_start_late=True, schedule__release_through=4,
                      event__announcements=[{"id": "hq-open", "title": "수사본부 OPEN", "body": "시작"}])
    db = Database(cfg.db_path)
    pub = FakePublisher()

    async def post_notice(text, title=None, ref=None, banner=False, mention_everyone=False):
        return await pub._post(f"notice:{title}", ref)
    pub.post_notice = post_notice

    now = START + timedelta(days=1, hours=18)
    for i in range(10):
        await sched(cfg, db, catalog, pub).tick(now + timedelta(seconds=20 * i))  # 매 틱 재시작해도 중복 없음
    assert pub.posts == ["notice:수사본부 OPEN", "opening", "ep1", "ep2", "ep3", "ep4"]


def test_episode_list_has_video_buttons(game, db):
    import asyncio

    from bot.ui import EpisodeWatchView

    from .conftest import open_event

    open_event(db, 4)
    for ep in game.catalog.episodes.values():
        ep.video_url = f"https://youtu.be/ep{ep.number}"
    info = game.case_info()

    async def build():
        return EpisodeWatchView(None, info["episodes"], set())  # type: ignore[arg-type]
    view = asyncio.run(build())
    links = [c for c in view.children if getattr(c, "url", None)]
    assert [c.label for c in links] == ["1화", "2화", "3화", "4화"]
    assert links[0].url == "https://youtu.be/ep1"


async def test_channel_move_reposts_opening_and_episodes_once(tmp_path, catalog):
    from datetime import timedelta

    from bot.database import Database

    from .conftest import make_config

    cfg = make_config(tmp_path, event__auto_start_late=True, schedule__release_through=2,
                      event__repost_on_channel_change=True)
    db = Database(cfg.db_path)
    for kind, item in [("opening", "main"), ("episode", 1), ("episode", 2)]:
        db.claim_release(kind, item)
        db.complete_release(kind, item, 1548252787002048572, 10)  # 예전 채널에 올라간 기록
    db.claim_release("evidence", "E-05")
    db.complete_release("evidence", "E-05", 1548252787002048572, 11)

    class NewChannelPublisher(FakePublisher):
        async def _post(self, label, mk):
            _, mid = await super()._post(label, mk)
            return cfg.event_channel_id, mid

    pub = NewChannelPublisher()
    now = START + timedelta(days=1, hours=18)
    for i in range(6):
        await sched(cfg, db, catalog, pub).tick(now + timedelta(seconds=20 * i))
    assert pub.posts == ["opening", "ep1", "ep2"]
    assert db.is_posted("evidence", "E-05")  # 증거 수동 공개 기록은 유지


async def test_delete_own_messages_only_removes_bot_posts(monkeypatch):
    from types import SimpleNamespace

    from bot import main

    monkeypatch.setattr(main.asyncio, "sleep", _no_sleep)
    removed = []

    def msg(mid, author):
        async def delete():
            removed.append(mid)
        return SimpleNamespace(id=mid, author=SimpleNamespace(id=author), delete=delete)

    msgs = [msg(1, 99), msg(2, 5), msg(3, 99)]

    class Channel:
        def history(self, limit):
            async def gen():
                for m in msgs:
                    yield m
            return gen()

    n = await main.delete_own_messages(Channel(), 99)
    assert n == 2 and removed == [1, 3]


async def _no_sleep(_):
    return None


async def test_notice_can_mention_everyone(cfg):
    import discord

    from bot.main import DalbitBot, DiscordPublisher

    bot = DalbitBot(cfg)
    pub = DiscordPublisher(bot)
    sent = []

    async def fake_send(**kwargs):
        sent.append(kwargs)
        return 1, 2
    pub._send = fake_send  # type: ignore[method-assign]
    await pub.post_notice("본문", title="수사본부 OPEN", mention_everyone=True)
    await pub.post_notice("본문")
    assert sent[0]["content"] == "@everyone" and sent[0]["allowed_mentions"].everyone is True
    assert "content" not in sent[1] and "allowed_mentions" not in sent[1]  # 기본은 멘션 없음
    assert isinstance(sent[0]["embed"], discord.Embed)
    await bot.close()
