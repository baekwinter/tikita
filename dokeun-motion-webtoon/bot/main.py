"""도근고등학교 달빛 방송부 — 디스코드 봇 실행 진입점.

실행 (dokeun-motion-webtoon 폴더에서):
    python -m bot.main
"""
from __future__ import annotations

import asyncio
import logging
import logging.handlers
import sys

import aiohttp
import discord
from discord import app_commands

from . import ui
from .commands import register_commands
from .config import BOT_DIR, BOT_NAME, Config, load_config
from .database import Database
from .evidence import Episode, Evidence
from .game import GameError, build_service
from .scheduler import ReleaseScheduler, TransientError, marker, run_forever

log = logging.getLogger("dalbit")

# 필요한 권한만: 채널 보기, 메시지 보내기, 링크 임베드, 파일 첨부, 메시지 기록 보기
BOT_PERMISSIONS = discord.Permissions(view_channel=True, send_messages=True, embed_links=True,
                                      attach_files=True, read_message_history=True)


def invite_url(application_id: int) -> str:
    return discord.utils.oauth_url(application_id, permissions=BOT_PERMISSIONS,
                                   scopes=("bot", "applications.commands"))


def setup_logging() -> None:
    log_dir = BOT_DIR / "var"
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    rotating = logging.handlers.RotatingFileHandler(log_dir / "bot.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    rotating.setFormatter(fmt)
    root.handlers = [stream, rotating]
    logging.getLogger("discord.http").setLevel(logging.WARNING)


def _wrap_transient(exc: BaseException) -> BaseException:
    if isinstance(exc, discord.DiscordServerError):
        return TransientError(f"Discord {exc.status}")
    if isinstance(exc, (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError)):
        return TransientError(type(exc).__name__)
    return exc


class DiscordPublisher:
    """스케줄러가 호출하는 실제 게시 동작. 이벤트 채널에만 게시한다."""

    def __init__(self, bot: "DalbitBot"):
        self.bot = bot

    async def channel(self) -> discord.TextChannel:
        cid = self.bot.cfg.event_channel_id
        ch = self.bot.get_channel(cid) or await self.bot.fetch_channel(cid)
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            raise RuntimeError("이벤트 채널이 텍스트 채널이 아닙니다")
        if getattr(ch, "guild", None) is None or ch.guild.id != self.bot.cfg.guild_id:
            raise RuntimeError("이벤트 채널이 지정된 서버에 속하지 않습니다")
        return ch  # type: ignore[return-value]

    async def _send(self, **kwargs) -> tuple[int, int]:
        try:
            ch = await self.channel()
            msg = await ch.send(**kwargs)
            return ch.id, msg.id
        except Exception as exc:
            wrapped = _wrap_transient(exc)
            if wrapped is exc:
                raise
            raise wrapped from exc

    async def post_opening(self) -> tuple[int, int]:
        cfg = self.bot.cfg
        ev = cfg.section("event")
        poster = cfg.resolve_media_path(ev.get("poster_path"))
        has_poster = bool(poster and poster.is_file())
        files = [discord.File(poster, filename="poster.png")] if has_poster else []
        view = ui.public_view(self.bot, ["start", "episodes", "progress", "evidence", "final"])
        return await self._send(embeds=ui.opening_embeds(has_poster, ev.get("poster_url")), files=files, view=view)

    async def post_episode(self, episode: Episode, new_evidence: list[Evidence]) -> tuple[int, int]:
        limit_mb = self.bot.cfg.section("media").get("upload_limit_mb", 10)
        limit = limit_mb * 1024 * 1024
        media = episode.media_status(limit_mb)
        files: list[discord.File] = []
        used = 0
        content = None
        if media == "attach" and episode.video_file:
            files.append(discord.File(episode.video_file, filename=episode.video_file.name))
            used += episode.video_file.stat().st_size
        elif media == "url":
            content = episode.video_url  # 디스코드가 링크 미리보기(플레이어)를 붙인다
        thumb = episode.thumbnail_file
        has_thumb = bool(thumb and used + thumb.stat().st_size <= limit)
        if has_thumb and thumb:
            files.append(discord.File(thumb, filename="thumbnail.jpg"))
        view = ui.public_view(self.bot, ["watch", "ask", "evidence", "progress"], episode=episode.number)
        embeds = ui.episode_embeds(episode, new_evidence, media, has_thumb)
        return await self._send(content=content, embeds=embeds, files=files, view=view)

    async def post_evidence(self, evidence: Evidence) -> tuple[int, int]:
        embed = ui.evidence_notice_embed(evidence, ref=marker("evidence", evidence.evidence_id))
        view = ui.public_view(self.bot, ["evidence", "ask", "progress"], with_web=True)
        return await self._send(embed=embed, view=view)

    async def post_ending(self) -> tuple[int, int]:
        view = ui.public_view(self.bot, ["progress"])
        return await self._send(embeds=ui.ending_embeds(self.bot.game), view=view)

    async def find_marker(self, mk: str) -> int | None:
        try:
            ch = await self.channel()
            async for msg in ch.history(limit=50):
                if self.bot.user and msg.author.id != self.bot.user.id:
                    continue
                for e in msg.embeds:
                    if e.footer and e.footer.text and mk in e.footer.text:
                        return msg.id
        except discord.HTTPException:
            log.exception("채널 기록 확인 실패")
        return None

    async def notify_admins(self, text: str) -> None:
        cfg = self.bot.cfg
        body = f"[{BOT_NAME} 운영 알림]\n{text}"
        if cfg.admin_alert_channel_id:
            ch = self.bot.get_channel(cfg.admin_alert_channel_id) or await self.bot.fetch_channel(cfg.admin_alert_channel_id)
            await ch.send(body)  # type: ignore[union-attr]
            return
        for uid in cfg.admin_user_ids:
            try:
                user = await self.bot.fetch_user(uid)
                await user.send(body)
            except discord.HTTPException:
                log.warning("운영진 %s 에게 DM 을 보낼 수 없습니다", uid)


class DalbitTree(app_commands.CommandTree):
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        original = getattr(error, "original", error)
        if isinstance(original, GameError):
            await ui.reply(interaction, original.message)
            return
        log.exception("명령어 오류", exc_info=error)
        try:
            await ui.reply(interaction, "방송부 장비에 잠시 문제가 생겼습니다. 잠시 후 다시 시도해 주세요.")
        except discord.HTTPException:
            pass


class DalbitBot(discord.Client):
    def __init__(self, cfg: Config):
        intents = discord.Intents.none()
        intents.guilds = True  # 메시지 내용(Message Content) 같은 특권 인텐트는 쓰지 않는다
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.cfg = cfg
        self.db = Database(cfg.db_path)
        self.game = build_service(cfg, self.db)
        self.catalog = self.game.catalog
        self.tree = DalbitTree(self)
        self.publisher = DiscordPublisher(self)
        self.scheduler = ReleaseScheduler(cfg, self.db, self.catalog, self.publisher, on_ending=self._on_ending)
        self._stop = asyncio.Event()
        self._scheduler_task: asyncio.Task | None = None

    async def _on_ending(self) -> None:
        total = self.game.finalize_all()
        log.info("엔딩 정산 완료: %s점 지급", total)

    async def setup_hook(self) -> None:
        self.add_dynamic_items(ui.PublicButton)
        register_commands(self)
        guild = discord.Object(id=self.cfg.guild_id)
        synced = await self.tree.sync(guild=guild)
        log.info("길드 명령어 %d개 등록 (서버 %s)", len(synced), self.cfg.guild_id)

    async def on_ready(self) -> None:
        log.info("로그인: %s (id=%s) · 이벤트 채널 %s · 게임 채널 %s · 개막 %s",
                 self.user, self.user.id if self.user else "?", self.cfg.event_channel_id,
                 self.cfg.game_channel_id, self.cfg.start_at_utc.isoformat())
        if self.application_id:
            log.info("초대 링크: %s", invite_url(self.application_id))
        if self.get_guild(self.cfg.guild_id) is None:
            log.error("봇이 지정된 서버(%s)에 초대되어 있지 않습니다", self.cfg.guild_id)
        if self._scheduler_task is None:
            tick = float(self.cfg.section("schedule").get("tick_seconds", 20))
            self._scheduler_task = asyncio.create_task(run_forever(self.scheduler, tick, self._stop))

    async def close(self) -> None:
        self._stop.set()
        if self._scheduler_task:
            await asyncio.wait([self._scheduler_task], timeout=5)
        await super().close()


def main() -> None:
    setup_logging()
    cfg = load_config()
    if not cfg.token:
        log.error("DISCORD_TOKEN 이 설정되지 않았습니다. bot/.env 를 확인하세요 (.env.example 참고).")
        raise SystemExit(1)
    if cfg.test_mode and cfg.is_production_target:
        log.warning("테스트 모드이지만 실제 도근도근 서버를 대상으로 합니다. 조기 공개 설정은 무시됩니다.")
    bot = DalbitBot(cfg)
    bot.run(cfg.token, log_handler=None)


if __name__ == "__main__":
    main()
