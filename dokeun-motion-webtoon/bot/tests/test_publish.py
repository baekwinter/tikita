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
