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
    assert {c.name for c in admin.commands} == {"상태", "공개", "예약", "시작", "중지", "재개", "테스트", "결과"}
    await bot.close()


def test_invite_url_uses_minimal_permissions():
    url = invite_url(123)
    assert "permissions=117760" in url and "applications.commands" in url
    assert "administrator" not in url
