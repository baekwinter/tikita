"""웹 조사실 백엔드 (FastAPI).

- Discord OAuth2 로 로그인하고, 지정 서버(길드) 멤버만 플레이할 수 있다.
- 봇과 같은 SQLite DB 와 같은 게임 엔진(bot.game.GameService)을 사용한다 → 디스코드/웹 진행도가 하나로 이어진다.
- 정답 데이터는 서버에서만 읽는다. 프론트엔드에는 공개된 정보와 채점 결과만 내려간다.

실행 (dokeun-motion-webtoon 폴더에서):
    uvicorn api.app:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import os
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from bot.config import load_config
from bot.database import Database
from bot.game import GameError, build_service
from bot.rewards import export_csv

DISCORD_API = "https://discord.com/api/v10"

cfg = load_config()
db = Database(cfg.db_path)
game = build_service(cfg, db)

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID") or (str(cfg.application_id) if cfg.application_id else "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
PUBLIC_URL = (os.getenv("DG_PUBLIC_URL") or "http://localhost:3000").rstrip("/")
SESSION_SECRET = os.getenv("DG_SESSION_SECRET") or ""
COOKIE_SECURE = PUBLIC_URL.startswith("https://")
DEV_LOGIN = cfg.test_mode and os.getenv("DG_WEB_DEV_LOGIN", "").lower() in {"1", "true", "yes"}

if not SESSION_SECRET:
    if not DEV_LOGIN:
        raise SystemExit("DG_SESSION_SECRET 을 설정하세요 (예: python -c \"import secrets;print(secrets.token_urlsafe(48))\")")
    SESSION_SECRET = secrets.token_urlsafe(48)

app = FastAPI(title="달빛 방송부 웹 조사실", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, session_cookie="dalbit_session",
                   max_age=60 * 60 * 24 * 14, same_site="lax", https_only=COOKIE_SECURE)


@app.exception_handler(GameError)
async def game_error_handler(_: Request, err: GameError) -> JSONResponse:
    return JSONResponse({"code": err.code, "message": err.message, **err.extra}, status_code=409)


# ---------------------------------------------------------------------------
# 인증
# ---------------------------------------------------------------------------
class User(BaseModel):
    id: int
    name: str
    avatar: str | None = None


def current_user(request: Request) -> User:
    data = request.session.get("user")
    if not data:
        raise HTTPException(401, detail={"code": "login", "message": "디스코드로 로그인해 주세요."})
    return User(**data)


def is_admin(user: User) -> bool:
    return user.id in cfg.admin_user_ids


@app.get("/api/auth/login")
async def login(request: Request) -> RedirectResponse:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(503, detail={"code": "oauth", "message": "Discord OAuth2 설정이 필요합니다 (DISCORD_CLIENT_ID/SECRET)."})
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    query = urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": f"{PUBLIC_URL}/api/auth/callback",
        "response_type": "code",
        "scope": "identify guilds",
        "state": state,
    })
    return RedirectResponse(f"https://discord.com/oauth2/authorize?{query}")


@app.get("/api/auth/callback")
async def callback(request: Request, code: str | None = None, state: str | None = None) -> RedirectResponse:
    expected = request.session.pop("oauth_state", None)
    if not code or not state or not expected or not secrets.compare_digest(state, expected):
        return RedirectResponse(f"{PUBLIC_URL}/?error=state")
    async with httpx.AsyncClient(timeout=15) as client:
        token_res = await client.post(f"{DISCORD_API}/oauth2/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": f"{PUBLIC_URL}/api/auth/callback",
        }, auth=(CLIENT_ID, CLIENT_SECRET), headers={"Content-Type": "application/x-www-form-urlencoded"})
        if token_res.status_code != 200:
            return RedirectResponse(f"{PUBLIC_URL}/?error=token")
        access = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {access}"}
        me = (await client.get(f"{DISCORD_API}/users/@me", headers=headers)).json()
        guilds_res = await client.get(f"{DISCORD_API}/users/@me/guilds", headers=headers)
    guild_ids = {int(g["id"]) for g in guilds_res.json()} if guilds_res.status_code == 200 else set()
    if cfg.guild_id not in guild_ids:
        return RedirectResponse(f"{PUBLIC_URL}/?error=guild")
    uid = int(me["id"])
    avatar = f"https://cdn.discordapp.com/avatars/{uid}/{me['avatar']}.png?size=64" if me.get("avatar") else None
    request.session["user"] = {"id": uid, "name": me.get("global_name") or me.get("username") or "조사원", "avatar": avatar}
    return RedirectResponse(f"{PUBLIC_URL}/play")


@app.get("/api/auth/dev")
async def dev_login(request: Request, uid: int = 1, name: str = "테스트 조사원") -> RedirectResponse:
    """테스트 모드 + DG_WEB_DEV_LOGIN 일 때만 동작하는 로컬 개발용 로그인."""
    if not DEV_LOGIN:
        raise HTTPException(404)
    request.session["user"] = {"id": uid, "name": name, "avatar": None}
    return RedirectResponse(f"{PUBLIC_URL}/play")


@app.post("/api/auth/logout")
async def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 게임
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "phase": game.phase(), "current_episode": game.current_episode}


@app.get("/api/me")
async def me(user: User = Depends(current_user)) -> dict[str, Any]:
    return {"user": user.model_dump(), "admin": is_admin(user)}


@app.get("/api/state")
async def state(user: User = Depends(current_user)) -> dict[str, Any]:
    """플레이 화면 전체 상태. 정답표는 포함하지 않는다."""
    info = game.case_info()
    for ep in info["episodes"]:
        ep["thumbnail_url"] = f"/api/media/episode/{ep['number']}" if ep["has_thumbnail"] else None
    if info["episode"]:
        info["episode"]["thumbnail_url"] = f"/api/media/episode/{info['episode']['number']}" if info["episode"]["has_thumbnail"] else None
    evidence = game.evidence_board(user.id)
    for ev in evidence:
        if not ev["locked"] and ev.get("has_image"):
            ev["image_url"] = f"/api/media/evidence/{ev['id']}"
    return {
        "user": user.model_dump(),
        "admin": is_admin(user),
        "case": info,
        "progress": game.progress(user.id),
        "evidence": evidence,
        "history": game.question_history(user.id, 60),
        "final": game.final_status(user.id),
        "note": game.get_note(user.id),
    }


@app.post("/api/join")
async def join(user: User = Depends(current_user)) -> dict[str, Any]:
    return game.register(user.id, user.name)


class AskBody(BaseModel):
    text: str = Field(min_length=1, max_length=200)


@app.post("/api/ask")
async def ask(body: AskBody, user: User = Depends(current_user)) -> dict[str, Any]:
    return await game.ask(user.id, body.text, "web", user.name)


@app.post("/api/evidence/{evidence_id}/investigate")
async def investigate(evidence_id: str, user: User = Depends(current_user)) -> dict[str, Any]:
    data = game.investigate(user.id, evidence_id, user.name)
    if data.get("has_image"):
        data["image_url"] = f"/api/media/evidence/{data['id']}"
    return data


@app.post("/api/episodes/{number}/watched")
async def watched(number: int, user: User = Depends(current_user)) -> dict[str, Any]:
    return game.mark_watched(user.id, number, user.name)


class TheoryBody(BaseModel):
    body: str = Field(min_length=1, max_length=1500)


@app.post("/api/theory")
async def theory(body: TheoryBody, user: User = Depends(current_user)) -> dict[str, Any]:
    return game.submit_theory(user.id, body.body, user.name)


class FinalBody(BaseModel):
    q1: str
    q2: str
    q3: str
    q4: str
    q5: str = Field(max_length=1500)
    story: str = Field(default="", max_length=1500)


@app.post("/api/final")
async def final(body: FinalBody, user: User = Depends(current_user)) -> dict[str, Any]:
    return game.submit_final(user.id, body.model_dump(), user.name)


class NoteBody(BaseModel):
    body: str = Field(max_length=5000)


@app.put("/api/note")
async def save_note(body: NoteBody, user: User = Depends(current_user)) -> dict[str, Any]:
    return game.save_note(user.id, body.body)


# ---------------------------------------------------------------------------
# 미디어 — 공개된 회차/증거의 이미지만 내려준다
# ---------------------------------------------------------------------------
@app.get("/api/media/episode/{number}")
async def episode_media(number: int, user: User = Depends(current_user)) -> FileResponse:
    ep = game.catalog.episodes.get(number)
    if ep is None or number > game.current_episode or ep.thumbnail_file is None:
        raise HTTPException(404)
    return FileResponse(ep.thumbnail_file, headers={"Cache-Control": "private, max-age=600"})


@app.get("/api/media/evidence/{evidence_id}")
async def evidence_media(evidence_id: str, user: User = Depends(current_user)) -> FileResponse:
    ev = game.catalog.evidence.get(evidence_id.upper())
    if ev is None or ev.image_file is None or not game.catalog.is_evidence_released(
            ev.evidence_id, game.current_episode, db.manually_released_evidence()):
        raise HTTPException(404)
    return FileResponse(ev.image_file, headers={"Cache-Control": "private, max-age=600"})


# ---------------------------------------------------------------------------
# 운영진
# ---------------------------------------------------------------------------
@app.get("/api/admin/export.csv")
async def admin_export(user: User = Depends(current_user)) -> PlainTextResponse:
    if not is_admin(user):
        raise HTTPException(403)
    return PlainTextResponse(export_csv(db, game.current_episode), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": "attachment; filename=dalbit_results.csv"})
