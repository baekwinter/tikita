"""슬래시 명령어.

참가자: /시작 /사건 /질문 /증거 /조사 /추리 /정답 /진행도 /관계도 /도움말
운영진: /운영 상태·공개·예약·시작·중지·재개·테스트·결과·영상·공지

명령어는 이벤트 서버에만 길드 명령어로 등록되고, 게임 기능은 이벤트 채널에서만 동작한다.
운영 명령어는 기본적으로 '서버 관리' 권한자에게만 보이며, 실행 시 .env 의 운영진 ID/역할로 한 번 더 확인한다.
"""
from __future__ import annotations

import io
import logging
import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from . import ui
from .config import parse_local
from .database import utcnow
from .game import VIDEO_OVERRIDES_KEY
from .rewards import export_csv
from .scheduler import ALREADY, FAILED, HELD, POSTED, episode_schedule, kst, schedule_problems

if TYPE_CHECKING:
    from .main import DalbitBot

log = logging.getLogger(__name__)


def is_admin(bot: "DalbitBot", interaction: discord.Interaction) -> bool:
    cfg = bot.cfg
    user = interaction.user
    if user.id in cfg.admin_user_ids:
        return True
    if isinstance(user, discord.Member):
        if cfg.admin_role_ids and any(r.id in cfg.admin_role_ids for r in user.roles):
            return True
        if cfg.admin_allow_manage_guild and user.guild_permissions.manage_guild:
            return True
    return False


def register_commands(bot: "DalbitBot") -> None:
    tree = bot.tree
    guild = discord.Object(id=bot.cfg.guild_id)

    # ------------------------------------------------------------------ 참가자
    @tree.command(name="시작", description="특별 조사원으로 등록하고 수사 수첩을 엽니다", guild=guild)
    async def start_cmd(interaction: discord.Interaction) -> None:
        if await ui.guard(interaction):
            await ui.run_safely(interaction, lambda: ui.open_dashboard(interaction))

    @tree.command(name="사건", description="현재 사건 설명과 공개된 이야기를 확인합니다", guild=guild)
    async def case_cmd(interaction: discord.Interaction) -> None:
        if await ui.guard(interaction):
            async def run():
                bot.game.gate()
                await ui.reply(interaction, embed=ui.case_embed(bot.game))
            await ui.run_safely(interaction, run)

    @tree.command(name="질문", description="방송부에 YES/NO 질문을 합니다", guild=guild)
    @app_commands.describe(내용="예/아니오로 답할 수 있는 질문 (예: 반휘혈이 고백을 녹음했나요?)")
    async def ask_cmd(interaction: discord.Interaction, 내용: app_commands.Range[str, 3, 200]) -> None:
        if await ui.guard(interaction):
            await ui.run_safely(interaction, lambda: ui.ask_question(interaction, 내용))

    character_choices = [app_commands.Choice(name=name, value=name) for name in ("반휘혈", "온하늘", "차세리", "남궁호")]

    @tree.command(name="인물", description="등장인물의 공개 프로필을 확인합니다", guild=guild)
    @app_commands.choices(이름=character_choices)
    async def character_cmd(interaction: discord.Interaction, 이름: app_commands.Choice[str]) -> None:
        if await ui.guard(interaction):
            await ui.reply(interaction, embed=ui.character_embed(bot.game, 이름.value))

    @tree.command(name="관계", description="두 인물 사이의 공개 관계를 확인합니다", guild=guild)
    @app_commands.choices(인물1=character_choices, 인물2=character_choices)
    async def relation_cmd(interaction: discord.Interaction, 인물1: app_commands.Choice[str],
                           인물2: app_commands.Choice[str]) -> None:
        if await ui.guard(interaction):
            await ui.reply(interaction, embed=ui.public_relation_embed(bot.game, 인물1.value, 인물2.value))

    @tree.command(name="영상", description="현재까지 공개된 영상 목록을 확인합니다", guild=guild)
    async def videos_cmd(interaction: discord.Interaction) -> None:
        if await ui.guard(interaction):
            await ui.run_safely(interaction, lambda: ui.show_episodes(interaction))

    @tree.command(name="회차", description="현재 공개된 이야기와 회차를 확인합니다", guild=guild)
    async def episode_cmd(interaction: discord.Interaction) -> None:
        if await ui.guard(interaction):
            await ui.run_safely(interaction, lambda: ui.reply(interaction, embed=ui.case_embed(bot.game)))

    @tree.command(name="증거", description="공개된 증거 목록을 확인합니다", guild=guild)
    async def evidence_cmd(interaction: discord.Interaction) -> None:
        if await ui.guard(interaction):
            await ui.run_safely(interaction, lambda: ui.show_evidence(interaction))

    async def evidence_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        # 공개된 증거만 후보로 보여 준다
        cur = current.strip().lower()
        out = []
        for eid in bot.game.released_evidence_ids():
            ev = bot.catalog.evidence[eid]
            label = f"{eid} {ev.title}"
            if not cur or cur in label.lower():
                out.append(app_commands.Choice(name=label[:100], value=eid))
        return out[:25]

    @tree.command(name="조사", description="증거의 상세 내용을 조사합니다", guild=guild)
    @app_commands.describe(증거="조사할 증거")
    @app_commands.autocomplete(증거=evidence_autocomplete)
    async def investigate_cmd(interaction: discord.Interaction, 증거: str) -> None:
        if await ui.guard(interaction):
            await ui.run_safely(interaction, lambda: ui.investigate(interaction, 증거))

    @tree.command(name="추리", description="지금까지의 가설을 수사 수첩에 기록합니다", guild=guild)
    async def theory_cmd(interaction: discord.Interaction) -> None:
        if await ui.guard(interaction):
            try:
                bot.game.gate()
            except Exception as err:  # GameError
                await ui.reply(interaction, getattr(err, "message", "지금은 제출할 수 없습니다."))
                return
            await interaction.response.send_modal(ui.TheoryModal())

    @tree.command(name="정답", description="최종 추리(범인과 사건의 진실)를 제출합니다", guild=guild)
    async def final_cmd(interaction: discord.Interaction) -> None:
        if await ui.guard(interaction):
            await ui.run_safely(interaction, lambda: ui.show_final(interaction))

    @tree.command(name="진행도", description="내 수사 진행도를 확인합니다", guild=guild)
    async def progress_cmd(interaction: discord.Interaction) -> None:
        if await ui.guard(interaction):
            await ui.run_safely(interaction, lambda: ui.show_progress(interaction))

    @tree.command(name="순위", description="달빛 수사 포인트 랭킹과 내 등수를 확인합니다", guild=guild)
    async def ranking_cmd(interaction: discord.Interaction) -> None:
        if await ui.guard(interaction):
            await ui.run_safely(interaction, lambda: ui.show_ranking(interaction))

    @tree.command(name="관계도", description="심문으로 밝혀낸 인물 관계도를 확인합니다", guild=guild)
    async def relations_cmd(interaction: discord.Interaction) -> None:
        if await ui.guard(interaction):
            await ui.run_safely(interaction, lambda: ui.show_relationships(interaction))

    @tree.command(name="도움말", description="게임 방법을 확인합니다", guild=guild)
    async def help_cmd(interaction: discord.Interaction) -> None:
        await ui.reply(interaction, embed=ui.help_embed())

    # ------------------------------------------------------------------ 운영진
    admin = app_commands.Group(
        name="운영", description="달빛 방송부 운영진 전용",
        guild_ids=[bot.cfg.guild_id],
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    async def admin_only(interaction: discord.Interaction) -> bool:
        if is_admin(bot, interaction):
            return True
        await ui.reply(interaction, "운영진만 사용할 수 있는 명령어입니다.")
        return False

    @admin.command(name="상태", description="전체 이벤트 진행 현황")
    async def status_cmd(interaction: discord.Interaction) -> None:
        if not await admin_only(interaction):
            return
        await ui.reply(interaction, embed=status_embed(bot))

    @admin.command(name="공개", description="개막·회차·증거·엔딩을 이벤트 채널에 수동 공개")
    @app_commands.describe(대상="공개할 대상", 번호="회차 번호 (대상이 회차일 때)", 증거="증거 ID (대상이 증거일 때, 예: E-05)")
    @app_commands.choices(대상=[
        app_commands.Choice(name="회차", value="episode"),
        app_commands.Choice(name="증거", value="evidence"),
        app_commands.Choice(name="엔딩", value="ending"),
        app_commands.Choice(name="개막", value="opening"),
    ])
    async def publish_cmd(interaction: discord.Interaction, 대상: app_commands.Choice[str],
                          번호: int | None = None, 증거: str | None = None) -> None:
        if not await admin_only(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        kind = 대상.value
        if kind == "episode":
            if 번호 is None:
                await interaction.followup.send("번호를 입력하세요.", ephemeral=True)
                return
            ep = bot.catalog.episodes.get(번호)
            media = ep.media_status(bot.cfg.section("media").get("upload_limit_mb", 10)) if ep else "-"
            res = await bot.scheduler.publish_episode(번호)
            note = " (영상 없이 게시됨 — 준비되면 채널에 따로 올려 주세요)" if res == POSTED and media in {"missing", "too_large"} else ""
        elif kind == "evidence":
            if not 증거:
                await interaction.followup.send("증거 ID 를 입력하세요.", ephemeral=True)
                return
            res = await bot.scheduler.publish_evidence(증거.strip().upper())
            note = ""
        elif kind == "ending":
            res = await bot.scheduler.publish_ending()
            note = ""
        else:
            res = await bot.scheduler.publish_opening()
            note = ""
        await interaction.followup.send(f"결과: {describe(res)}{note}", ephemeral=True)

    @admin.command(name="패널", description="현재 채널에 '최종 수사 보고서' 정답 제출 패널을 게시")
    async def panel_cmd(interaction: discord.Interaction) -> None:
        if not await admin_only(interaction):
            return
        # 버튼(dg:finalsubmit)은 영구 View 라 봇 재시작 후에도 동작한다. 자동 게시는 없으므로
        # 재시작으로 중복 게시되지 않는다. 운영진이 이 명령을 부를 때만 새 패널이 올라간다.
        await interaction.channel.send(embed=ui.final_panel_embed(), view=ui.final_panel_view())
        await ui.reply(interaction, "🌙 최종 수사 보고서 패널을 이 채널에 게시했습니다.")

    @admin.command(name="순위게시", description="이벤트 채널에 달빛 수사 포인트 공개 랭킹판을 게시")
    @app_commands.describe(인원="표시할 상위 인원 (기본 15)")
    async def ranking_post_cmd(interaction: discord.Interaction, 인원: app_commands.Range[int, 3, 25] = 15) -> None:
        if not await admin_only(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = ui.ranking_embed(bot.game, user_id=None, top=int(인원), public=True)
        channel = bot.get_channel(bot.cfg.event_channel_id) or await bot.fetch_channel(bot.cfg.event_channel_id)
        await channel.send(embed=embed)
        await interaction.followup.send("🌙 달빛 수사 포인트 랭킹판을 이벤트 채널에 게시했습니다.", ephemeral=True)

    @admin.command(name="버튼추가", description="이미 게시된 수사본부/개막 공지에 '📝 최종 정답 제출하기' 버튼을 추가")
    @app_commands.describe(공지="버튼을 추가할 기존 공지", 메시지링크="자동으로 찾지 못할 때 쓸 메시지 링크(선택)")
    @app_commands.choices(공지=[
        app_commands.Choice(name="수사본부 OPEN 공지 (hq-open-3)", value="notice:hq-open-3"),
        app_commands.Choice(name="개막 공지", value="opening:main"),
    ])
    async def addbutton_cmd(interaction: discord.Interaction, 공지: app_commands.Choice[str],
                            메시지링크: str | None = None) -> None:
        if not await admin_only(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        kind, item_id = 공지.value.split(":", 1)
        channel_id = message_id = None
        # 1) DB 게시 이력에서 기존 메시지 위치를 조회
        row = bot.db.get_release(kind, item_id)
        if row and row["channel_id"] and row["message_id"]:
            channel_id, message_id = int(row["channel_id"]), int(row["message_id"])
        # 2) 실패 시 운영진이 준 메시지 링크에서 추출
        elif 메시지링크:
            m = re.search(r"/channels/\d+/(\d+)/(\d+)", 메시지링크)
            if m:
                channel_id, message_id = int(m.group(1)), int(m.group(2))
        if not (channel_id and message_id):
            await interaction.followup.send(
                "기존 공지 메시지를 자동으로 찾지 못했습니다. 해당 공지 메시지의 '링크 복사'로 얻은 URL을 "
                "`메시지링크:` 에 넣어 다시 실행해 주세요. (임의로 새 공지를 게시하지 않았습니다.)",
                ephemeral=True)
            return
        try:
            channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
            msg = await channel.fetch_message(message_id)
        except discord.HTTPException as exc:
            await interaction.followup.send(f"메시지를 불러오지 못했습니다: {exc}", ephemeral=True)
            return
        # 기존 5개 버튼 + 새 finalreport 버튼으로 View 를 다시 구성해 메시지를 편집한다(기존 내용·이미지 유지).
        actions = (["episodes", "watch", "ask", "evidence", "progress"] if kind == "episode"
                   else ["start", "episodes", "progress", "evidence", "final", "finalreport"])
        view = ui.public_view(bot, actions)
        await msg.edit(view=view)
        await interaction.followup.send(
            "✅ 기존 공지에 '📝 최종 정답 제출하기' 버튼을 추가했습니다. 기존 버튼과 내용·이미지는 그대로 유지됩니다.",
            ephemeral=True)

    @admin.command(name="예약", description="공개 일정 확인 및 변경 (한국 시간)")
    @app_commands.describe(회차="변경할 회차 번호", 일시="'2026-09-24 12:00' 형식. '삭제' 입력 시 변경 취소")
    async def schedule_cmd(interaction: discord.Interaction, 회차: int | None = None, 일시: str | None = None) -> None:
        if not await admin_only(interaction):
            return
        if 회차 is not None and 일시:
            if 회차 not in bot.catalog.episodes:
                await ui.reply(interaction, "없는 회차입니다.")
                return
            if bot.db.is_posted("episode", 회차):
                await ui.reply(interaction, "이미 공개된 회차입니다.")
                return
            if 일시.strip() == "삭제":
                bot.db.set_schedule_override(회차, None, interaction.user.id)
            else:
                try:
                    when = parse_local(일시, bot.cfg.tz)
                except ValueError:
                    await ui.reply(interaction, "일시 형식이 올바르지 않습니다. 예) 2026-09-24 12:00")
                    return
                bot.db.set_schedule_override(회차, when, interaction.user.id)
                bot.db.clear_alert(f"overdue:episode:{회차}")
        await ui.reply(interaction, embed=schedule_embed(bot))

    @admin.command(name="시작", description="비상시 이벤트 수동 시작 (개막 공지 + 1화)")
    @app_commands.describe(확인="개막 시각 전에 시작하려면 '조기 시작' 이라고 입력")
    async def force_start_cmd(interaction: discord.Interaction, 확인: str | None = None) -> None:
        if not await admin_only(interaction):
            return
        if utcnow() < bot.cfg.start_at_utc and (확인 or "").strip() != "조기 시작":
            await ui.reply(interaction, f"개막 시각({kst(bot.cfg.start_at_utc, bot.cfg)}) 전입니다. "
                                        "정말 먼저 시작하려면 `확인: 조기 시작` 을 함께 입력하세요.")
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        bot.db.set_kv("paused", False)
        res1 = await bot.scheduler.publish_opening()
        res2 = await bot.scheduler.publish_episode(1)
        await interaction.followup.send(f"개막 공지: {describe(res1)} · EP.01: {describe(res2)}", ephemeral=True)

    @admin.command(name="중지", description="이벤트 일시 중지 (자동 공개와 참가자 기능 정지)")
    async def pause_cmd(interaction: discord.Interaction) -> None:
        if not await admin_only(interaction):
            return
        bot.db.set_kv("paused", True)
        await ui.reply(interaction, "이벤트를 일시 중지했습니다. 자동 공개가 멈추고 참가자에게 점검 안내가 표시됩니다.")

    @admin.command(name="재개", description="이벤트 재개")
    async def resume_cmd(interaction: discord.Interaction) -> None:
        if not await admin_only(interaction):
            return
        bot.db.set_kv("paused", False)
        await ui.reply(interaction, "이벤트를 재개했습니다. 중지 중 지난 회차가 있으면 '/운영 상태' 의 알림을 확인하세요.")

    @admin.command(name="테스트", description="비공개 테스트 (나에게만 보임, 채널에 게시하지 않음)")
    @app_commands.describe(항목="테스트할 항목", 번호="회차 번호", 증거="증거 ID", 질문="질문 문장")
    @app_commands.choices(항목=[
        app_commands.Choice(name="데이터 점검", value="check"),
        app_commands.Choice(name="개막 미리보기", value="opening"),
        app_commands.Choice(name="회차 미리보기", value="episode"),
        app_commands.Choice(name="증거 미리보기", value="evidence"),
        app_commands.Choice(name="질문 테스트 (지정 회차 기준)", value="question"),
        app_commands.Choice(name="엔딩 미리보기", value="ending"),
        app_commands.Choice(name="수사 수첩 미리보기", value="dashboard"),
    ])
    async def test_cmd(interaction: discord.Interaction, 항목: app_commands.Choice[str], 번호: int | None = None,
                       증거: str | None = None, 질문: str | None = None) -> None:
        if not await admin_only(interaction):
            return
        await run_test(bot, interaction, 항목.value, 번호, 증거, 질문)

    @admin.command(name="결과", description="참가자별 기록 확인 및 CSV 내보내기")
    @app_commands.describe(형식="요약 또는 CSV", 참가자="특정 참가자 기록 보기")
    @app_commands.choices(형식=[app_commands.Choice(name="요약", value="summary"), app_commands.Choice(name="CSV", value="csv")])
    async def results_cmd(interaction: discord.Interaction, 형식: app_commands.Choice[str] | None = None,
                          참가자: discord.Member | None = None) -> None:
        if not await admin_only(interaction):
            return
        if 참가자 is not None:
            e = ui.progress_embed(bot.game, 참가자.id)
            e.title = f"{참가자.display_name} 의 수사 기록"
            subs = bot.db.submissions(참가자.id)
            if subs:
                last = subs[-1]
                e.add_field(name="마지막 최종 추리", value=f"{last['correct_count']}/5 · 해결 {'Y' if last['solved'] else 'N'}\n```{last['answers'][:900]}```", inline=False)
            await ui.reply(interaction, embed=e)
            return
        if 형식 and 형식.value == "csv":
            data = export_csv(bot.db, bot.db.current_episode()).encode("utf-8")
            await interaction.response.send_message(
                "참가자 결과 CSV 입니다.", file=discord.File(io.BytesIO(data), filename="dalbit_results.csv"), ephemeral=True)
            return
        rows = bot.db.leaderboard(15)
        lines = [f"{i}. <@{r['user_id']}> · {r['points']}점" for i, r in enumerate(rows, 1)]
        e = discord.Embed(title="달빛 수사 포인트 순위", description="\n".join(lines) or "참가자가 없습니다.", colour=ui.COLOR_MAIN)
        e.set_footer(text=f"참가자 {len(bot.db.all_players())}명")
        await ui.reply(interaction, embed=e)

    @admin.command(name="영상", description="회차 영상 링크(유튜브 일부공개 등) 등록 · 재배포 없이 바로 반영")
    @app_commands.describe(회차="회차 번호 (1~12)", 링크="https:// 로 시작하는 영상 주소. '삭제' 입력 시 등록 취소")
    async def video_cmd(interaction: discord.Interaction, 회차: int, 링크: str) -> None:
        if not await admin_only(interaction):
            return
        ep = bot.catalog.episodes.get(회차)
        if ep is None:
            await ui.reply(interaction, "없는 회차입니다.")
            return
        url = 링크.strip()
        if url == "삭제":
            url = ""
        elif not url.startswith("https://") or any(ch.isspace() for ch in url):
            await ui.reply(interaction, "링크는 https:// 로 시작하는 주소 하나만 입력하세요. 예) https://youtu.be/xxxx")
            return
        overrides = dict(bot.db.get_kv(VIDEO_OVERRIDES_KEY, {}) or {})
        overrides[str(회차)] = url
        bot.db.set_kv(VIDEO_OVERRIDES_KEY, overrides)
        ep.video_url = url or None
        if not url:
            await ui.reply(interaction, f"{ep.code} 영상 링크 등록을 취소했습니다.")
            return
        bot.db.clear_alert(f"media:episode:{회차}")
        if not bot.db.is_posted("episode", 회차):
            await ui.reply(interaction, f"{ep.code} 영상 링크를 등록했습니다. 회차가 공개될 때 함께 게시됩니다.")
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await bot.publisher.post_video_link(ep)
        except discord.HTTPException as exc:
            await interaction.followup.send(f"링크는 등록했지만 채널 게시에 실패했습니다: {exc}", ephemeral=True)
            return
        await interaction.followup.send(f"{ep.code} 은 이미 공개된 회차라 영상 링크를 이벤트 채널에 올렸습니다.", ephemeral=True)

    @admin.command(name="공지", description="이벤트 채널에 방송부 이름으로 공지 게시")
    @app_commands.describe(내용="공지 내용 (줄바꿈은 \\n 으로 입력)", 전체알림="@everyone 으로 서버 전체에 알림")
    async def notice_cmd(interaction: discord.Interaction, 내용: app_commands.Range[str, 1, 1800],
                         전체알림: bool = False) -> None:
        if not await admin_only(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await bot.publisher.post_notice(내용.replace("\\n", "\n"), mention_everyone=전체알림)
        except discord.HTTPException as exc:
            await interaction.followup.send(f"공지 게시 실패: {exc}", ephemeral=True)
            return
        await interaction.followup.send("이벤트 채널에 공지를 올렸습니다.", ephemeral=True)

    tree.add_command(admin)


# ---------------------------------------------------------------------------
def describe(res) -> str:
    return {
        POSTED: "게시 완료",
        ALREADY: "이미 게시됨 (중복 게시하지 않음)",
        HELD: "영상 누락으로 보류",
        FAILED: "게시 실패 — 로그와 운영 알림 확인",
        "order": "앞 회차가 아직 공개되지 않았습니다",
        "no_opening": "개막 공지가 먼저 게시되어야 합니다",
        "unknown": "존재하지 않는 대상입니다",
        "already_open": "이미 회차 공개로 열린 증거입니다",
        "episodes_left": "아직 공개되지 않은 회차가 있습니다",
    }.get(res, str(res))


def schedule_embed(bot: "DalbitBot") -> discord.Embed:
    sched = episode_schedule(bot.cfg, bot.catalog, bot.db.schedule_overrides())
    overrides = bot.db.schedule_overrides()
    limit = bot.cfg.section("media").get("upload_limit_mb", 10)
    media_label = {"attach": "첨부", "url": "링크", "too_large": "용량초과", "missing": "영상없음"}
    lines = [f"개막 · {kst(bot.cfg.start_at_utc, bot.cfg)} · {'게시됨' if bot.db.is_posted('opening') else '대기'}"]
    for n, when in sorted(sched.items()):
        ep = bot.catalog.episodes[n]
        state = "공개됨" if bot.db.is_posted("episode", n) else "대기"
        mark = " (변경)" if n in overrides else ""
        lines.append(f"{ep.code} · {kst(when, bot.cfg)}{mark} · {state} · {media_label[ep.media_status(limit)]}")
    e = discord.Embed(title=f"공개 일정 · 방식 {bot.cfg.section('schedule').get('mode')}", description="\n".join(lines), colour=ui.COLOR_NIGHT)
    problems = schedule_problems(bot.cfg, sched)
    if problems:
        e.add_field(name="확인 필요", value="\n".join(problems)[:1000], inline=False)
    e.set_footer(text="변경: /운영 예약 회차:3 일시:2026-09-24 12:00 · 취소: 일시:삭제")
    return e


def status_embed(bot: "DalbitBot") -> discord.Embed:
    db, cfg = bot.db, bot.cfg
    e = discord.Embed(title="달빛 방송부 운영 현황", colour=ui.COLOR_MAIN)
    e.add_field(name="현재 시각", value=kst(utcnow(), cfg), inline=True)
    e.add_field(name="개막", value=f"{kst(cfg.start_at_utc, cfg)} · {'게시됨' if db.is_posted('opening') else '대기'}", inline=True)
    e.add_field(name="상태", value={"before": "개막 전", "live": "진행 중", "paused": "일시 중지", "ended": "종료"}[bot.game.phase()], inline=True)
    e.add_field(name="공개 회차", value=f"EP.{db.current_episode():02d} / {bot.catalog.episode_count}", inline=True)
    e.add_field(name="참가자", value=f"{len(db.all_players())}명", inline=True)
    e.add_field(name="테스트 모드", value="ON" if cfg.test_mode else "OFF", inline=True)
    alerts = db.alerts()
    if alerts:
        e.add_field(name="운영 알림", value="\n".join(f"• {a['message']}" for a in alerts[-8:])[:1000], inline=False)
    unmatched = db.query("SELECT question_text FROM question_log WHERE question_id IS NULL AND question_text IS NOT NULL ORDER BY id DESC LIMIT 5")
    if unmatched:
        e.add_field(name="최근 해석 실패 질문 (동의어 보강용)", value="\n".join(f"• {r['question_text'][:80]}" for r in unmatched), inline=False)
    return e


async def run_test(bot: "DalbitBot", interaction: discord.Interaction, item: str,
                   number: int | None, evidence_id: str | None, question: str | None) -> None:
    game = bot.game
    if item == "check":
        from .cli import data_report
        text = data_report(bot.cfg, game)
        await ui.reply(interaction, f"```{text[:1900]}```")
    elif item == "opening":
        await ui.reply(interaction, "[미리보기] 개막 공지 — 채널에는 게시되지 않았습니다.", embed=ui.opening_embeds(False, None)[0])
    elif item == "episode":
        ep = bot.catalog.episodes.get(number or 1)
        if ep is None:
            await ui.reply(interaction, "없는 회차입니다.")
            return
        media = ep.media_status(bot.cfg.section("media").get("upload_limit_mb", 10))
        embeds = ui.episode_embeds(ep, bot.catalog.evidence_for_episode(ep.number), media, False)
        await interaction.response.send_message(f"[미리보기] {ep.code} · 영상 상태: {media}", embeds=embeds, ephemeral=True)
    elif item == "evidence":
        ev = bot.catalog.evidence.get((evidence_id or "E-01").upper())
        if ev is None:
            await ui.reply(interaction, "없는 증거입니다.")
            return
        await ui.reply(interaction, f"[미리보기] {ev.evidence_id} · {ev.release_episode}화 공개 · 이미지 {'있음' if ev.image_file else '없음'}",
                       embed=ui.evidence_detail_embed(ev.public(True, investigated=True)))
    elif item == "question":
        if not question:
            await ui.reply(interaction, "질문을 입력하세요.")
            return
        ep = number or game.current_episode
        res = game.bank.ask(question, ep, bool(bot.cfg.section("questions").get("answer_unconfirmed", False)))
        await ui.reply(interaction, f"[질문 테스트 · EP.{ep:02d} 기준]\n응답: **{res.label}**\n인식: {res.question_id or '-'} ({res.via})\n{res.hint}")
    elif item == "ending":
        await ui.reply(interaction, "[미리보기] 엔딩 — 채널에는 게시되지 않았습니다.", embed=ui.ending_embeds(game)[0])
    elif item == "dashboard":
        await ui.reply(interaction, "[미리보기] 수사 수첩", embed=ui.dashboard_embed(game, interaction.user.id))
