import discord

from bot.commands import register_commands
from bot.main import DalbitBot, invite_url


async def test_command_tree_builds(cfg):
    bot = DalbitBot(cfg)
    register_commands(bot)
    cmds = bot.tree.get_commands(guild=discord.Object(id=cfg.guild_id))
    names = {c.name for c in cmds}
    assert {"시작", "사건", "질문", "증거", "조사", "추리", "정답", "진행도", "도움말", "운영"} <= names
    for c in cmds:
        c.to_dict(bot.tree)  # Discord 규칙 위반 시 여기서 예외
    admin = next(c for c in cmds if c.name == "운영")
    assert {c.name for c in admin.commands} == {"상태", "공개", "예약", "시작", "중지", "재개", "테스트", "결과", "영상", "공지"}
    await bot.close()


def test_invite_url_uses_minimal_permissions():
    url = invite_url(123)
    assert "permissions=117760" in url and "applications.commands" in url
    assert "administrator" not in url


def test_video_override_persists_over_episodes_json(db, catalog):
    from bot.evidence import Catalog
    from bot.game import VIDEO_OVERRIDES_KEY, apply_video_overrides

    db.set_kv(VIDEO_OVERRIDES_KEY, {"2": "https://youtu.be/abc", "3": ""})
    apply_video_overrides(catalog, db)
    assert catalog.episodes[2].video_url == "https://youtu.be/abc"
    assert catalog.episodes[2].media_status(10) in {"attach", "url"}
    assert catalog.episodes[3].video_url is None
    fresh = Catalog.load()  # 재시작해도 DB 값이 다시 적용된다
    apply_video_overrides(fresh, db)
    assert fresh.episodes[2].video_url == "https://youtu.be/abc"


def test_final_result_embed_shows_score_like_game():
    from bot.ui import final_result_embed

    e = final_result_embed({"correct": 3, "total": 5, "solved": False, "attempts": 1, "max_attempts": 3, "gained": 10})
    assert "# 3 / 5" in e.description and "🟪🟪🟪⬛⬛" in e.description
    assert "제출 1/3회" in e.description and "+10" in e.description
    assert len(e) <= 6000


def test_dashboard_has_case_banner_and_interrogation(game, db):
    import asyncio

    from bot import ui
    from .conftest import open_event

    open_event(db, 4)
    game.register(7, "조사원")
    asyncio.run(game.ask(7, "반휘혈이 고백을 녹음했나요?", "discord", "조사원"))
    e = ui.dashboard_embed(game, 7, with_image=True)
    assert e.author.name.endswith("CASE #01 · CONFIDENTIAL · EP.04")
    assert e.image.url == "attachment://scene.png" and ui.SCENE_FILE.is_file()
    names = [f.name for f in e.fields]
    assert {"확보 증거", "추리 시도"} <= set(names) and any("방송부 심문" in n for n in names)
    assert len(e) <= 6000 and len(ui.interrogation_embed(game, 7)) <= 6000
