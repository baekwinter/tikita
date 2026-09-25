"""디스코드 화면 구성: 임베드, 버튼, 선택 메뉴, 모달.

- 공식 채널 게시물(개막, 회차, 증거, 엔딩)에는 영구 버튼(DynamicItem)을 단다 → 봇 재시작 후에도 동작.
- 참가자 개인 화면은 모두 본인에게만 보이는(ephemeral) 응답으로 보여 채널을 밀어내지 않는다.
"""
from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any

import discord

from .config import BOT_NAME, GAME_TITLE
from .evidence import Episode, Evidence
from .game import CHARACTERS, GameError, GameService

if TYPE_CHECKING:
    from .main import DalbitBot

log = logging.getLogger(__name__)

# 회보라 · 인디핑크 · 달빛 남색
COLOR_MAIN = discord.Colour(0x8E7FA8)
COLOR_PINK = discord.Colour(0xD8A1A4)
COLOR_NIGHT = discord.Colour(0x39345A)
COLOR_ONAIR = discord.Colour(0xC75B6B)

FOOTER = BOT_NAME


def footer(ref: str | None = None) -> str:
    return f"{FOOTER} · {ref}" if ref else FOOTER


# ---------------------------------------------------------------------------
# 게임 HUD 요소 (웹 조사실과 같은 느낌을 디스코드 임베드로)
# ---------------------------------------------------------------------------
def bar(done: int, total: int, width: int = 12) -> str:
    total = max(total, 1)
    filled = round(width * min(done, total) / total)
    return "▰" * filled + "▱" * (width - filled)


def score_pips(correct: int, total: int) -> str:
    return "🟪" * correct + "⬛" * max(total - correct, 0)


def hud_line(game: GameService, user_id: int) -> str:
    p = game.progress(user_id)
    return (f"`ROUND {p['current_episode']:02d}/{p['total_episodes']}` · `질문 {p['questions']['total']}` · "
            f"`증거 {p['evidence_found']}/{p['evidence_released']}` · `{p['points']}점`")


def episode_grid(game: GameService, user_id: int) -> str:
    current = game.current_episode
    watched = game.db.watched_episodes(user_id)
    cells = []
    for n in range(1, game.catalog.episode_count + 1):
        if n > current:
            icon = "🔒"
        elif n == current:
            icon = "🔴"
        elif n in watched:
            icon = "✅"
        else:
            icon = "▶️"
        cells.append(f"{icon}`{n:02d}`")
    rows = [" ".join(cells[i:i + 6]) for i in range(0, len(cells), 6)]
    return "\n".join(rows) + "\n-# 🔴 ON AIR · ✅ 시청 완료 · ▶️ 미시청 · 🔒 잠김"


def points_toast(gained: int, currency: str = "달빛 수사 포인트") -> str:
    return f"\n\n> ✨ **+{gained} {currency}**" if gained else ""


VERDICT_BADGE = {"YES": "🟢 YES", "NO": "🔴 NO", "IRRELEVANT": "⚪ 관계없음"}


def web_url(bot: "DalbitBot") -> str | None:
    return os.getenv("DG_WEB_URL") or bot.cfg.section("event").get("web_url") or None


# ---------------------------------------------------------------------------
# 공식 게시물 임베드
# ---------------------------------------------------------------------------
def opening_embeds(has_poster: bool, poster_url: str | None) -> list[discord.Embed]:
    first = discord.Embed(
        title=f"[{BOT_NAME}]",
        description=(
            "2026년 추석 특별 방송이 시작되었습니다.\n\n"
            "그런데 방송 준비 중\n예정에 없던 고백이 발견되었습니다.\n\n"
            "누가 녹음했을까요?\n\n누구에게 전하려던 마음이었을까요?\n\n"
            "그리고 누가 이 고백을 방송에 송출했을까요?\n\n"
            "지금부터 여러분은\n도근고등학교 방송부의 **특별 조사원**이 됩니다."
        ),
        colour=COLOR_ONAIR,
    )
    if has_poster:
        first.set_image(url="attachment://poster.png")
    elif poster_url:
        first.set_image(url=poster_url)

    case = discord.Embed(title=f"사건명 · {GAME_TITLE}", colour=COLOR_MAIN)
    case.description = (
        "방송실 스피커에서 흘러나온 한 편의 고백.\n"
        "등장인물 네 사람 — **반휘혈 · 온하늘 · 남궁호 · 차세리** — 사이에서 무슨 일이 있었던 걸까요?\n"
        "※ 이 이벤트는 허구의 이야기로, 실제 인물·관계와 무관합니다."
    )
    how = discord.Embed(title="수사 방법", colour=COLOR_NIGHT, description=(
        "1. 매일 공개되는 모션 웹툰(총 12화)을 시청합니다.\n"
        "2. **YES/NO 질문**으로 사건을 캐묻습니다. 방송부는 YES · NO · 관계없음 · 아직 공개되지 않은 정보 중 하나로 답합니다.\n"
        "3. 회차가 공개될 때마다 열리는 **증거**를 조사합니다.\n"
        "4. 추리를 다듬어 **최종 추리**를 제출하세요. 범인 이름뿐 아니라 방법과 이유까지 밝혀야 사건 해결입니다.\n\n"
        "아래 **[수사 시작하기]** 를 누르면 나에게만 보이는 수사 수첩이 열립니다."
    ))
    how.set_footer(text=footer("ref:opening:main"))
    return [first, case, how]


def episode_embeds(ep: Episode, new_evidence: list[Evidence], media: str, has_thumb: bool) -> list[discord.Embed]:
    e = discord.Embed(title=f"ON AIR · {ep.display_title}", colour=COLOR_MAIN)
    lines = [ep.description] if ep.description else []
    if media == "url":
        lines.append(f"[영상 보기]({ep.video_url})")
    elif media in {"missing", "too_large"}:
        lines.append("영상은 방송부가 준비되는 대로 이 채널에 올려 드립니다.")
    lines.append("\n시청을 마쳤다면 **[시청 완료]** 를 눌러 수사 수첩에 기록하세요.")
    e.description = "\n".join(lines)
    if ep.keywords:
        e.add_field(name="키워드", value=" · ".join(ep.keywords), inline=False)
    if has_thumb:
        e.set_image(url="attachment://thumbnail.jpg")
    e.set_footer(text=footer(f"ref:episode:{ep.number}"))
    out = [e]
    for ev in new_evidence[:5]:
        out.append(evidence_notice_embed(ev, ref=None))
    return out


def evidence_notice_embed(ev: Evidence, ref: str | None) -> discord.Embed:
    e = discord.Embed(title=f"새 증거 공개 · {ev.evidence_id} {ev.title}", description=ev.summary, colour=COLOR_PINK)
    e.add_field(name="분류", value=ev.category or "-", inline=True)
    e.add_field(name="조사", value="[증거 확인] 버튼 또는 `/조사` 로 상세 내용을 확인하세요.", inline=False)
    if ref:
        e.set_footer(text=footer(ref))
    return e


def ending_embeds(game: GameService) -> list[discord.Embed]:
    t = game.ending_text()
    e = discord.Embed(title=f"[{BOT_NAME}] 사건 파일을 닫습니다", colour=COLOR_ONAIR, description=(
        "12화의 방송이 모두 끝났습니다. 방송부가 확인한 사건의 진실을 공개합니다.\n​"
    ))
    for key in ("q1", "q2", "q3", "q4", "q5"):
        label, _, answer = t[key].partition(" → ")
        e.add_field(name=label, value=answer, inline=False)
    e.add_field(name="사건 정리", value=(
        "2025년, 온하늘이 녹음한 답장은 반휘혈에게 전달되지 않았고 두 사람은 서로 거절당했다고 오해했습니다.\n"
        "2026년, 차세리는 두 음성 파일을 발견하고 방송 예약 목록을 수정해 21:00에 송출했습니다. "
        "오해를 풀어 주고 싶었던 마음이었지만, 두 사람의 사적인 녹음을 허락 없이 공개한 일이기도 합니다.\n"
        "남궁호는 음성 편집을 도왔을 뿐, 무단 송출의 공범은 아닙니다."
    ), inline=False)
    e.set_footer(text=footer("ref:ending:main"))
    return [e]


# ---------------------------------------------------------------------------
# 개인 화면 임베드
# ---------------------------------------------------------------------------
def dashboard_embed(game: GameService, user_id: int) -> discord.Embed:
    info = game.case_info()
    prog = game.progress(user_id)
    ep = info["episode"]
    e = discord.Embed(title=f"🎙️ ON AIR · 달빛 방송부 수사실", colour=COLOR_MAIN, description=(
        f"{hud_line(game, user_id)}\n\n"
        f"## {GAME_TITLE}\n"
        "누가 녹음했을까? 누구에게 전하려던 마음이었을까?\n그리고 누가 이 고백을 방송에 송출했을까?\n"
        + " ".join(f"`{c}`" for c in CHARACTERS)
    ))
    e.add_field(name=f"📺 {ep['title'] if ep else '개막 전'}", value=episode_grid(game, user_id), inline=False)
    e.add_field(name="🔎 증거 수집", value=f"{bar(prog['evidence_found'], prog['evidence_released'], 10)} {prog['evidence_found']}/{prog['evidence_released']}", inline=True)
    q = prog["questions"]
    e.add_field(name="❓ 오늘 남은 질문", value=f"{bar(q['remaining'], q['limit'], 10)} {q['remaining']}/{q['limit']}", inline=True)
    left = prog["final_max_attempts"] - prog["final_attempts"]
    e.add_field(name="📝 최종 추리", value=f"남은 기회 **{left}/{prog['final_max_attempts']}** · {prog['status']}", inline=False)
    if info["next_episode"]:
        e.add_field(name="⏭️ 다음 방송", value=f"EP.{info['next_episode']['number']:02d} · {info['next_episode']['at_kst']}", inline=False)
    e.set_footer(text="이 화면은 나에게만 보입니다 · 특별 조사원 전용")
    return e


def answer_embed(res: dict[str, Any]) -> discord.Embed:
    colour = {"YES": COLOR_MAIN, "NO": COLOR_ONAIR, "IRRELEVANT": COLOR_NIGHT}.get(res["verdict"], COLOR_NIGHT)
    badge = VERDICT_BADGE.get(res["verdict"], f"🔒 {res['label']}")
    lines = [f"-# 방송부 응답", f"> {res['question'][:900]}", f"## {badge}"]
    if res["response_text"]:
        lines.append(f"📻 {res['response_text']}")
    if res["hint"]:
        lines.append(f"-# {res['hint']}")
    if res.get("related_evidence"):
        rel = res["related_evidence"]
        lines.append(f"🔎 관련 증거 `{rel['id']}` **{rel['title']}**")
    e = discord.Embed(description="\n".join(lines) + points_toast(res["gained"]), colour=colour)
    q = res["quota"]
    tail = f"오늘 남은 질문 {q['remaining']}/{q['limit']}"
    if res["duplicate"]:
        tail += " · 같은 질문은 횟수에서 차감하지 않았습니다"
    elif not res["counted"]:
        tail += " · 해석하지 못한 질문은 차감하지 않습니다"
    e.set_footer(text=tail)
    return e


def evidence_board_embed(game: GameService, user_id: int) -> discord.Embed:
    board = game.evidence_board(user_id)
    found = sum(1 for i in board if not i["locked"] and i["found"])
    released = sum(1 for i in board if not i["locked"])
    e = discord.Embed(title="🗂️ EVIDENCE · 증거 보관함", colour=COLOR_PINK,
                      description=f"{bar(found, len(board))} 확보 {found} · 공개 {released} · 전체 {len(board)}")
    for item in board[:25]:
        if item["locked"]:
            e.add_field(name=f"🔒 {item['id']} · 잠긴 증거", value=f"-# EP.{item['episode']:02d} 공개 후 열립니다.", inline=True)
        else:
            mark = "✅ 수사 수첩에 기록됨" if item["found"] else "🔍 조사하기"
            e.add_field(name=f"{'📁' if item['found'] else '🔓'} {item['id']} · {item['title']}"[:256],
                        value=f"-# {item['category']}\n{mark}", inline=True)
    e.set_footer(text="아래 메뉴에서 증거를 골라 조사하세요.")
    return e


def evidence_detail_embed(data: dict[str, Any]) -> discord.Embed:
    e = discord.Embed(title=f"{data['id']} · {data['title']}", description=data["detail"], colour=COLOR_PINK)
    e.add_field(name="분류", value=data["category"] or "-", inline=True)
    e.add_field(name="공개 회차", value=f"EP.{data['episode']:02d}", inline=True)
    if data.get("new"):
        e.description = (e.description or "") + points_toast(data.get("gained", 0))
        e.set_footer(text=f"증거 {data['id']}이(가) 수사 수첩에 기록되었습니다.")
    else:
        e.set_footer(text="이미 수사 수첩에 기록된 증거입니다.")
    return e


def progress_embed(game: GameService, user_id: int) -> discord.Embed:
    p = game.progress(user_id)
    e = discord.Embed(title="내 수사 기록", colour=COLOR_MAIN)
    e.add_field(name="상태", value=p["status"], inline=True)
    e.add_field(name=p["currency"], value=f"{p['points']}점", inline=True)
    e.add_field(name="공개 회차", value=f"EP.{p['current_episode']:02d} / {p['total_episodes']}", inline=True)
    e.add_field(name="시청 완료", value=", ".join(f"EP.{n:02d}" for n in p["watched"]) or "-", inline=False)
    e.add_field(name="확보 증거", value=f"{p['evidence_found']} / {p['evidence_released']}", inline=True)
    e.add_field(name="질문", value=f"누적 {p['questions']['total']} · 오늘 남은 {p['questions']['remaining']}", inline=True)
    e.add_field(name="추리 제출", value=f"가설 {p['theories']} · 최종 {p['final_attempts']}/{p['final_max_attempts']}", inline=True)
    return e


def help_embed() -> discord.Embed:
    e = discord.Embed(title="수사 안내", colour=COLOR_NIGHT, description=(
        "**/시작** 수사 수첩 열기 (참가 등록)\n"
        "**/사건** 현재 사건 설명과 공개 회차\n"
        "**/질문** YES/NO 질문 — 예) `/질문 반휘혈이 고백을 녹음했나요?`\n"
        "**/증거** 공개된 증거 목록 · **/조사** 증거 상세 보기\n"
        "**/추리** 지금까지의 가설 기록 · **/정답** 최종 추리 제출\n"
        "**/진행도** 내 수사 기록\n\n"
        "방송부의 응답은 YES · NO · 관계없음 · 아직 공개되지 않은 정보입니다 중 하나입니다.\n"
        "인물 이름과 행동을 넣어 긍정형으로 물을수록 정확하게 답할 수 있어요.\n"
        "모든 응답은 나에게만 보입니다."
    ))
    return e


def case_embed(game: GameService) -> discord.Embed:
    info = game.case_info()
    e = discord.Embed(title=f"사건 파일 · {GAME_TITLE}", description=info["summary"], colour=COLOR_MAIN)
    ep = info["episode"]
    e.add_field(name="현재 공개된 이야기", value=ep["title"] if ep else "개막 전", inline=True)
    e.add_field(name="등장인물", value=" · ".join(CHARACTERS), inline=True)
    if ep and ep.get("description"):
        e.add_field(name="이번 화", value=ep["description"], inline=False)
    if info["next_episode"]:
        e.add_field(name="다음 방송", value=f"EP.{info['next_episode']['number']:02d} · {info['next_episode']['at_kst']}", inline=False)
    return e


def final_status_embed(game: GameService, user_id: int) -> discord.Embed:
    st = game.final_status(user_id)
    left = st["max_attempts"] - st["attempts"]
    e = discord.Embed(title="📝 FINAL REPORT · 최종 추리", colour=COLOR_ONAIR, description=(
        f"-# 남은 기회 {left}/{st['max_attempts']}\n"
        "누가 녹음했고, 누구를 향했고, 누가 어떻게·왜 송출했는지까지 밝혀야 사건 해결입니다."
    ))
    for item in st["form"][:5]:
        e.add_field(name=f"{item['key'].upper()}", value=item["label"], inline=False)
    if st["feedback"] == "count":
        e.add_field(name="채점", value="제출하면 5문항 중 몇 개를 맞혔는지만 알려 드립니다.", inline=True)
    else:
        e.add_field(name="채점", value="결과는 엔딩 공개 때 함께 발표됩니다.", inline=True)
    if st["last"] and "correct" in st["last"]:
        e.add_field(name="마지막 제출", value=f"{score_pips(st['last']['correct'], st['last']['total'])} {st['last']['correct']}/{st['last']['total']}", inline=True)
    e.set_footer(text="Q1~Q4 는 아래 메뉴에서 고르고, Q5 는 직접 써서 제출합니다.")
    return e


def final_result_embed(res: dict[str, Any]) -> discord.Embed:
    lines = ["-# FINAL REPORT", "### 최종 추리 · 채점 결과"]
    if "correct" in res:
        correct, total = res["correct"], res["total"]
        lines.append(f"# {correct} / {total}")
        lines.append(score_pips(correct, total))
        if res.get("solved"):
            msg, colour = "🌕 **사건의 진실에 도달했습니다!** 엔딩 공개를 기다려 주세요.", COLOR_PINK
        elif correct == 0:
            msg, colour = "아직 진실과는 거리가 있어요. 공개된 증거부터 다시 살펴볼까요?", COLOR_NIGHT
        else:
            msg, colour = "아직 맞지 않는 조각이 있어요. 증거와 질문으로 다시 확인해 보세요.", COLOR_MAIN
        lines.append(f"\n{msg}")
    else:
        colour = COLOR_MAIN
        lines.append("# 접수 완료")
        lines.append("채점 결과는 엔딩 공개 때 발표됩니다.")
    lines.append(f"-# 제출 {res['attempts']}/{res['max_attempts']}회")
    e = discord.Embed(description="\n".join(lines) + points_toast(res.get("gained", 0)), colour=colour)
    e.set_footer(text="이 결과는 나에게만 보입니다.")
    return e


# ---------------------------------------------------------------------------
# 공통 처리
# ---------------------------------------------------------------------------
async def reply(interaction: discord.Interaction, content: str | None = None, *,
                embed: discord.Embed | None = None, view: discord.ui.View | None = None) -> None:
    kwargs: dict[str, Any] = {"ephemeral": True}
    if content:
        kwargs["content"] = content
    if embed:
        kwargs["embed"] = embed
    if view:
        kwargs["view"] = view
    if interaction.response.is_done():
        await interaction.followup.send(**kwargs)
    else:
        await interaction.response.send_message(**kwargs)


def in_event_channel(interaction: discord.Interaction) -> bool:
    bot: DalbitBot = interaction.client  # type: ignore[assignment]
    return interaction.guild_id == bot.cfg.guild_id and interaction.channel_id == bot.cfg.event_channel_id


async def guard(interaction: discord.Interaction) -> bool:
    """이벤트 채널 밖에서는 게임 기능을 쓰지 않는다."""
    if in_event_channel(interaction):
        return True
    bot: DalbitBot = interaction.client  # type: ignore[assignment]
    await reply(interaction, f"수사는 <#{bot.cfg.event_channel_id}> 채널에서만 진행할 수 있어요.")
    return False


async def run_safely(interaction: discord.Interaction, coro_fn) -> None:
    try:
        await coro_fn()
    except GameError as err:
        await reply(interaction, err.message)
    except discord.HTTPException:
        log.exception("Discord 응답 실패")
    except Exception:
        log.exception("처리 중 오류")
        try:
            await reply(interaction, "방송부 장비에 잠시 문제가 생겼습니다. 잠시 후 다시 시도해 주세요.")
        except discord.HTTPException:
            pass


def name_of(interaction: discord.Interaction) -> str:
    return interaction.user.display_name


# ---------------------------------------------------------------------------
# 행동 (버튼·명령어 공용)
# ---------------------------------------------------------------------------
async def open_dashboard(interaction: discord.Interaction) -> None:
    bot: DalbitBot = interaction.client  # type: ignore[assignment]
    reg = bot.game.register(interaction.user.id, name_of(interaction))
    embed = dashboard_embed(bot.game, interaction.user.id)
    content = None
    if reg["new"]:
        content = f"🎙️ 특별 조사원 등록이 완료되었습니다. 환영합니다!{points_toast(reg['gained'])}"
    await reply(interaction, content, embed=embed, view=DashboardView(bot, interaction.user.id))


async def show_episodes(interaction: discord.Interaction) -> None:
    bot: DalbitBot = interaction.client  # type: ignore[assignment]
    bot.game.gate()
    info = bot.game.case_info()
    if not info["episodes"]:
        await reply(interaction, "아직 공개된 회차가 없습니다.")
        return
    watched = bot.db.watched_episodes(interaction.user.id)
    e = discord.Embed(title="공개된 이야기", colour=COLOR_MAIN)
    for ep in info["episodes"]:
        link = ep["discord_link"] or ep["video_url"]
        mark = "시청 완료" if ep["number"] in watched else "미시청"
        e.add_field(name=f"{ep['title']} · {mark}", value=f"[방송 보러 가기]({link})" if link else "방송 준비 중", inline=False)
    await reply(interaction, embed=e, view=EpisodeWatchView(bot, info["episodes"], watched))


async def show_evidence(interaction: discord.Interaction) -> None:
    bot: DalbitBot = interaction.client  # type: ignore[assignment]
    bot.game.gate()
    uid = interaction.user.id
    await reply(interaction, embed=evidence_board_embed(bot.game, uid), view=EvidenceSelectView(bot, uid))


async def investigate(interaction: discord.Interaction, evidence_id: str) -> None:
    bot: DalbitBot = interaction.client  # type: ignore[assignment]
    data = bot.game.investigate(interaction.user.id, evidence_id, name_of(interaction))
    embed = evidence_detail_embed(data)
    ev = bot.catalog.evidence[data["id"]]
    if ev.image_file:
        embed.set_image(url=f"attachment://{ev.image_file.name}")
        kwargs = {"embed": embed, "file": discord.File(ev.image_file, filename=ev.image_file.name), "ephemeral": True}
        if interaction.response.is_done():
            await interaction.followup.send(**kwargs)
        else:
            await interaction.response.send_message(**kwargs)
        return
    await reply(interaction, embed=embed)


async def ask_question(interaction: discord.Interaction, text: str) -> None:
    bot: DalbitBot = interaction.client  # type: ignore[assignment]
    res = await bot.game.ask(interaction.user.id, text, "discord", name_of(interaction))
    await reply(interaction, embed=answer_embed(res))


async def show_progress(interaction: discord.Interaction) -> None:
    bot: DalbitBot = interaction.client  # type: ignore[assignment]
    await reply(interaction, embed=progress_embed(bot.game, interaction.user.id))


async def show_final(interaction: discord.Interaction) -> None:
    bot: DalbitBot = interaction.client  # type: ignore[assignment]
    bot.game.gate()
    uid = interaction.user.id
    st = bot.game.final_status(uid)
    embed = final_status_embed(bot.game, uid)
    if not st["open"]:
        await reply(interaction, f"최종 추리는 EP.{st['open_from_episode']:02d} 공개 후 열립니다.", embed=embed)
        return
    if st["solved"] or st["attempts"] >= st["max_attempts"]:
        await reply(interaction, "더 이상 최종 추리를 제출할 수 없습니다.", embed=embed)
        return
    await reply(interaction, embed=embed, view=FinalView(bot, uid))


# ---------------------------------------------------------------------------
# 모달
# ---------------------------------------------------------------------------
class QuestionModal(discord.ui.Modal, title="YES/NO 질문"):
    text = discord.ui.TextInput(label="예/아니오로 답할 수 있는 질문", placeholder="예) 반휘혈이 고백을 녹음했나요?",
                                min_length=3, max_length=200)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_safely(interaction, lambda: ask_question(interaction, str(self.text.value)))


class TheoryModal(discord.ui.Modal, title="추리 기록"):
    body = discord.ui.TextInput(label="지금까지의 가설", style=discord.TextStyle.paragraph,
                                placeholder="누가, 언제, 어떻게, 왜? 떠오른 생각을 자유롭게 적어 두세요.",
                                min_length=5, max_length=1500)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        async def run():
            bot: DalbitBot = interaction.client  # type: ignore[assignment]
            res = bot.game.submit_theory(interaction.user.id, str(self.body.value), name_of(interaction))
            msg = f"가설이 수사 수첩에 기록되었습니다. (누적 {res['count']}건)"
            if res["gained"]:
                msg += f" 오늘의 추리 참여 +{res['gained']}점"
            await reply(interaction, msg)
        await run_safely(interaction, run)


class FinalReasonModal(discord.ui.Modal, title="최종 추리 · Q5"):
    reason = discord.ui.TextInput(label="Q5. 왜, 어떻게 그런 행동을 했나요?", style=discord.TextStyle.paragraph,
                                  min_length=10, max_length=1000)
    story = discord.ui.TextInput(label="사건의 흐름 (선택)", style=discord.TextStyle.paragraph, required=False,
                                 max_length=1500)

    def __init__(self, picks: dict[str, str]):
        super().__init__()
        self.picks = picks

    async def on_submit(self, interaction: discord.Interaction) -> None:
        async def run():
            bot: DalbitBot = interaction.client  # type: ignore[assignment]
            answers = dict(self.picks, q5=str(self.reason.value), story=str(self.story.value or ""))
            res = bot.game.submit_final(interaction.user.id, answers, name_of(interaction))
            await reply(interaction, embed=final_result_embed(res), view=ResultView(bot, interaction.user.id))
        await run_safely(interaction, run)


# ---------------------------------------------------------------------------
# 개인 화면 View
# ---------------------------------------------------------------------------
class OwnerView(discord.ui.View):
    def __init__(self, bot: "DalbitBot", owner_id: int, timeout: float = 900):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.owner_id


class DashboardView(OwnerView):
    def __init__(self, bot: "DalbitBot", owner_id: int):
        super().__init__(bot, owner_id)
        url = web_url(bot)
        if url:
            self.add_item(discord.ui.Button(label="웹 조사실 열기", url=url, row=2))

    @discord.ui.button(label="영상 시청", style=discord.ButtonStyle.secondary, row=0)
    async def videos(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await run_safely(interaction, lambda: show_episodes(interaction))

    @discord.ui.button(label="사건 조사", style=discord.ButtonStyle.secondary, row=0)
    async def case(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await run_safely(interaction, lambda: reply(interaction, embed=case_embed(self.bot.game)))

    @discord.ui.button(label="YES/NO 질문", style=discord.ButtonStyle.primary, row=0)
    async def question(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(QuestionModal())

    @discord.ui.button(label="증거 목록", style=discord.ButtonStyle.secondary, row=1)
    async def evidence(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await run_safely(interaction, lambda: show_evidence(interaction))

    @discord.ui.button(label="추리 제출", style=discord.ButtonStyle.secondary, row=1)
    async def theory(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(TheoryModal())

    @discord.ui.button(label="최종 추리", style=discord.ButtonStyle.danger, row=1)
    async def final(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await run_safely(interaction, lambda: show_final(interaction))


class ResultView(OwnerView):
    """최종 추리 결과 아래: 다시 조사하러 가기."""

    @discord.ui.button(label="증거 보관함", style=discord.ButtonStyle.secondary)
    async def evidence(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await run_safely(interaction, lambda: show_evidence(interaction))

    @discord.ui.button(label="YES/NO 질문", style=discord.ButtonStyle.primary)
    async def question(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(QuestionModal())

    @discord.ui.button(label="수사 수첩", style=discord.ButtonStyle.secondary)
    async def dashboard(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await run_safely(interaction, lambda: open_dashboard(interaction))


class EpisodeWatchView(OwnerView):
    def __init__(self, bot: "DalbitBot", episodes: list[dict], watched: set[int]):
        super().__init__(bot, 0)
        options = [
            discord.SelectOption(label=f"{ep['title']}"[:100], value=str(ep["number"]),
                                 description="시청 완료" if ep["number"] in watched else "시청 완료로 기록하기")
            for ep in episodes[-25:]
        ]
        select = discord.ui.Select(placeholder="시청을 마친 회차를 골라 기록하세요", options=options)
        select.callback = self._picked  # type: ignore[assignment]
        self.select = select
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def _picked(self, interaction: discord.Interaction) -> None:
        async def run():
            n = int(self.select.values[0])
            res = self.bot.game.mark_watched(interaction.user.id, n, name_of(interaction))
            msg = f"EP.{n:02d} 시청을 기록했습니다." + (f" +{res['gained']}점" if res["gained"] else "")
            await reply(interaction, msg)
        await run_safely(interaction, run)


class EvidenceSelectView(OwnerView):
    def __init__(self, bot: "DalbitBot", owner_id: int):
        super().__init__(bot, owner_id)
        released = [e for e in bot.game.evidence_board(owner_id) if not e["locked"]]
        if released:
            select = discord.ui.Select(
                placeholder="조사할 증거를 고르세요",
                options=[discord.SelectOption(label=f"{e['id']} {e['title']}"[:100], value=e["id"],
                                              description=e["summary"][:100]) for e in released[:25]],
            )
            select.callback = self._picked  # type: ignore[assignment]
            self.select = select
            self.add_item(select)

    async def _picked(self, interaction: discord.Interaction) -> None:
        await run_safely(interaction, lambda: investigate(interaction, self.select.values[0]))


class FinalView(OwnerView):
    def __init__(self, bot: "DalbitBot", owner_id: int):
        super().__init__(bot, owner_id)
        self.picks: dict[str, str] = {}
        for idx, item in enumerate(bot.game.final_key.form()[:4]):
            select = discord.ui.Select(
                placeholder=f"{item['key'].upper()}. {item['label']}"[:150],
                options=[discord.SelectOption(label=c, value=c) for c in CHARACTERS],
                row=idx,
            )
            select.callback = self._make_cb(item["key"], select)  # type: ignore[assignment]
            self.add_item(select)
        button = discord.ui.Button(label="Q5 작성하고 제출", style=discord.ButtonStyle.danger, row=4)
        button.callback = self._submit  # type: ignore[assignment]
        self.add_item(button)

    def _make_cb(self, key: str, select: discord.ui.Select):
        async def cb(interaction: discord.Interaction) -> None:
            self.picks[key] = select.values[0]
            await interaction.response.defer()
        return cb

    async def _submit(self, interaction: discord.Interaction) -> None:
        missing = [k.upper() for k in ("q1", "q2", "q3", "q4") if k not in self.picks]
        if missing:
            await reply(interaction, f"{', '.join(missing)} 를 먼저 골라 주세요.")
            return
        await interaction.response.send_modal(FinalReasonModal(dict(self.picks)))


# ---------------------------------------------------------------------------
# 공식 게시물의 영구 버튼
# ---------------------------------------------------------------------------
ACTION_LABELS = {
    "start": ("수사 시작하기", discord.ButtonStyle.primary),
    "episodes": ("현재 공개 화 보기", discord.ButtonStyle.secondary),
    "progress": ("내 진행도", discord.ButtonStyle.secondary),
    "evidence": ("증거 확인", discord.ButtonStyle.secondary),
    "final": ("최종 추리 안내", discord.ButtonStyle.danger),
    "watch": ("시청 완료", discord.ButtonStyle.success),
    "ask": ("YES/NO 질문", discord.ButtonStyle.primary),
}


class PublicButton(discord.ui.DynamicItem[discord.ui.Button], template=r"dg:(?P<action>[a-z]+)(?::(?P<arg>\d+))?"):
    def __init__(self, action: str, arg: int | None = None):
        label, style = ACTION_LABELS[action]
        custom_id = f"dg:{action}" + (f":{arg}" if arg is not None else "")
        super().__init__(discord.ui.Button(label=label, style=style, custom_id=custom_id))
        self.action = action
        self.arg = arg

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        arg = match.group("arg")
        return cls(match.group("action"), int(arg) if arg else None)

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await guard(interaction):
            return
        action = self.action
        if action == "ask":
            await interaction.response.send_modal(QuestionModal())
            return
        handlers = {
            "start": lambda: open_dashboard(interaction),
            "episodes": lambda: show_episodes(interaction),
            "progress": lambda: show_progress(interaction),
            "evidence": lambda: show_evidence(interaction),
            "final": lambda: show_final(interaction),
            "watch": lambda: _watch(interaction, self.arg or 0),
        }
        handler = handlers.get(action)
        if handler:
            await run_safely(interaction, handler)


async def _watch(interaction: discord.Interaction, number: int) -> None:
    bot: DalbitBot = interaction.client  # type: ignore[assignment]
    res = bot.game.mark_watched(interaction.user.id, number, name_of(interaction))
    if res["new"]:
        await reply(interaction, f"📺 EP.{number:02d} 시청이 수사 수첩에 기록되었습니다.{points_toast(res['gained'])}")
    else:
        await reply(interaction, f"EP.{number:02d} 은(는) 이미 시청 완료로 기록되어 있습니다.")


def public_view(bot: "DalbitBot", actions: list[str], episode: int | None = None, with_web: bool = True) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for i, action in enumerate(actions):
        item = PublicButton(action, episode if action == "watch" else None)
        item.item.row = 0 if i < 3 else 1
        view.add_item(item)
    url = web_url(bot) if with_web else None
    if url:
        view.add_item(discord.ui.Button(label="웹 조사실", url=url, row=1))
    return view
