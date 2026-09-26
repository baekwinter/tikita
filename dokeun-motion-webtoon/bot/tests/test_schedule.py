from datetime import timedelta

from bot.scheduler import PlanState, episode_schedule, plan_next, preset_slots

from .conftest import START, make_config


def test_start_is_kst_midnight(cfg):
    assert cfg.start_at_utc == START
    assert cfg.start_at_utc.isoformat() == "2026-09-23T15:00:00+00:00"


def test_configured_episode_schedule(cfg, catalog):
    sched = episode_schedule(cfg, catalog)
    assert sched[1] == START
    assert all(sched[n] is None for n in range(2, 5))
    assert sched[5] == START + timedelta(days=2, hours=12)
    assert sched[6] == START + timedelta(days=2, hours=15)
    assert sched[7] == START + timedelta(days=2, hours=18)
    assert sched[8] == START + timedelta(days=2, hours=21)
    assert sched[9] == START + timedelta(days=3, hours=12)
    assert sched[10] == START + timedelta(days=3, hours=15)
    assert sched[11] == START + timedelta(days=3, hours=18)
    assert sched[12] == START + timedelta(days=3, hours=21)


def test_presets_shapes(tmp_path):
    four = make_config(tmp_path, schedule__mode="4days_3per_day")
    three = make_config(tmp_path, schedule__mode="3days_4per_day")
    assert len(preset_slots(four)) == 12 and len(preset_slots(three)) == 12


def test_filled_preset_and_override_priority(tmp_path, catalog):
    cfg = make_config(tmp_path)
    cfg.settings["schedule"]["presets"]["4days_3per_day"][0]["times"] = ["00:00", "12:00", "20:00"]
    sched = episode_schedule(cfg, catalog, {3: START + timedelta(hours=5)})
    assert sched[2] == START + timedelta(hours=12)
    assert sched[3] == START + timedelta(hours=5)


def state(**kw):
    base = dict(now=START, start_at=START, paused=False, opening_posted=False, posted_episodes=set(),
                ending_posted=False, schedule={1: START, 2: START + timedelta(hours=12), 3: None},
                ending_at=None, grace=timedelta(minutes=30), opening_grace=timedelta(hours=12))
    base.update(kw)
    return PlanState(**base)


def test_nothing_before_start():
    assert plan_next(state(now=START - timedelta(seconds=1))) is None


def test_opening_then_episode_one():
    assert plan_next(state()).kind == "opening"
    a = plan_next(state(opening_posted=True))
    assert (a.kind, a.item) == ("episode", "1")


def test_pause_blocks_everything():
    assert plan_next(state(paused=True)) is None


def test_overdue_episode_asks_admin_instead_of_mass_posting():
    a = plan_next(state(now=START + timedelta(hours=13), opening_posted=True, posted_episodes={1}))
    assert a.kind == "alert" and a.alert_key == "overdue:episode:2"


def test_episodes_in_order_and_unscheduled_waits():
    s = state(now=START + timedelta(days=3), opening_posted=True, posted_episodes={1, 2})
    assert plan_next(s) is None  # 3화 시각 미정 → 자동 공개 없음
