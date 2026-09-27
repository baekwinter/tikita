"""게임 규칙 계층. 디스코드 봇과 웹 API 가 같은 GameService 를 사용한다.

반환값은 모두 '참가자에게 보여도 되는' 데이터만 담는다. 정답표(answers.json)는
채점·응답 판단에만 쓰이고 그대로 밖으로 나가지 않는다.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable

from .config import BOT_NAME, GAME_TITLE, Config, DATA_DIR, load_json
from .character_questions import CharacterQuestionBank, normalize_character_question
from .database import Database, utcnow
from .evidence import Catalog, Evidence
from .questions import AskResult, Question, QuestionBank, Verdict
from .rewards import RewardService
from .scheduler import episode_schedule, kst

CHARACTERS = ["반휘혈", "온하늘", "남궁호", "차세리"]

CASE_SUMMARY = (
    "2026년 추석 특별 방송 도중, 방송실 스피커에서 예정에 없던 고백이 흘러나왔다.\n"
    "누가 녹음했을까? 누구에게 전하려던 마음이었을까? 그리고 누가 이 고백을 방송에 송출했을까?"
)


class GameError(Exception):
    def __init__(self, code: str, message: str, **extra: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


@dataclass
class FinalKey:
    items: dict[str, dict[str, Any]]

    @classmethod
    def load(cls, doc: dict | None = None) -> "FinalKey":
        doc = doc or load_json(DATA_DIR / "answers.json")
        return cls(items=doc["final"])

    def form(self) -> list[dict[str, Any]]:
        """참가자에게 보여 줄 문항 (정답 제외)."""
        out = []
        for key in ("q1", "q2", "q3", "q4"):
            out.append({"key": key, "label": self.items[key]["label"], "type": "choice", "choices": CHARACTERS})
        out.append({"key": "q5", "label": self.items["q5"]["label"], "type": "text"})
        out.append({"key": "story", "label": "사건의 흐름을 자유롭게 정리해 주세요 (선택)", "type": "text"})
        return out

    def grade(self, answers: dict[str, str]) -> dict[str, Any]:
        items: dict[str, bool] = {}
        for key in ("q1", "q2", "q3", "q4"):
            items[key] = (answers.get(key) or "").strip() == self.items[key]["answer"]
        text = f"{answers.get('q5') or ''}\n{answers.get('story') or ''}"
        rubric = self.items["q5"]["rubric"]
        hit_groups = []
        required_ok = True
        optional_hits = 0
        for g in rubric["groups"]:
            hit = any(word in text for word in g["any"])
            if hit:
                hit_groups.append(g["name"])
            if g.get("required") and not hit:
                required_ok = False
            if not g.get("required") and hit:
                optional_hits += 1
        items["q5"] = required_ok and optional_hits >= int(rubric.get("min_optional", 1))
        correct = sum(items.values())
        return {"items": items, "correct": correct, "total": len(items), "solved": all(items.values()),
                "q5_groups": hit_groups}


class GameService:
    def __init__(self, cfg: Config, db: Database, catalog: Catalog, bank: QuestionBank,
                 rewards: RewardService, final_key: FinalKey | None = None,
                 ai_pick: Callable[[str, list[Question]], str | None] | None = None,
                 clock: Callable[[], datetime] = utcnow):
        self.cfg = cfg
        self.db = db
        self.catalog = catalog
        self.bank = bank
        self.character_bank = CharacterQuestionBank.load()
        self.rewards = rewards
        self.final_key = final_key or FinalKey.load()
        self.ai_pick = ai_pick
        self.clock = clock

    # ---- 공통 상태 --------------------------------------------------------
    @property
    def current_episode(self) -> int:
        return self.db.current_episode()

    def phase(self) -> str:
        if self.db.paused:
            return "paused"
        if self.db.is_posted("ending"):
            return "ended"
        if not self.db.is_posted("opening"):
            return "before"
        return "live"

    def gate(self) -> None:
        """참가자 기능 사용 가능 여부."""
        phase = self.phase()
        if phase == "before":
            start = kst(self.cfg.start_at_utc, self.cfg)
            raise GameError("before_start", f"이벤트는 {start}(한국 시간)에 시작됩니다. 조금만 기다려 주세요.")
        if phase == "paused":
            raise GameError("paused", "방송부가 잠시 방송을 점검하고 있습니다. 잠시 후 다시 찾아와 주세요.")

    def today_start(self) -> datetime:
        local = self.clock().astimezone(self.cfg.tz)
        return local.replace(hour=0, minute=0, second=0, microsecond=0)

    def today_key(self) -> str:
        return self.clock().astimezone(self.cfg.tz).strftime("%Y-%m-%d")

    # ---- 참가 등록 --------------------------------------------------------
    def register(self, user_id: int, display_name: str | None) -> dict[str, Any]:
        self.gate()
        new = self.db.register_player(user_id, display_name)
        gained = self.rewards.grant(user_id, "join") if new else 0
        return {"new": new, "gained": gained}

    def ensure_player(self, user_id: int, display_name: str | None = None) -> None:
        if self.db.get_player(user_id) is None:
            self.register(user_id, display_name)

    # ---- 사건 정보 --------------------------------------------------------
    def episode_public(self, number: int) -> dict[str, Any] | None:
        ep = self.catalog.episodes.get(number)
        if ep is None or number > self.current_episode:
            return None
        row = self.db.get_release("episode", number)
        link = None
        if row and row["message_id"]:
            link = f"https://discord.com/channels/{self.cfg.guild_id}/{row['channel_id']}/{row['message_id']}"
        return {
            "number": ep.number,
            "code": ep.code,
            "title": ep.display_title,
            "description": ep.description,
            "keywords": ep.keywords,
            "has_thumbnail": ep.thumbnail_file is not None,
            "video_url": ep.video_url,
            "discord_link": link,
            "released_at": row["released_at"] if row else None,
        }

    def case_info(self) -> dict[str, Any]:
        cur = self.current_episode
        schedule = episode_schedule(self.cfg, self.catalog, self.db.schedule_overrides())
        nxt = cur + 1 if cur < self.catalog.episode_count else None
        return {
            "bot_name": BOT_NAME,
            "title": GAME_TITLE,
            "summary": CASE_SUMMARY,
            "phase": self.phase(),
            "start_at": self.cfg.start_at_utc.isoformat(),
            "start_at_kst": kst(self.cfg.start_at_utc, self.cfg),
            "current_episode": cur,
            "total_episodes": self.catalog.episode_count,
            "episode": self.episode_public(cur) if cur else None,
            "episodes": [self.episode_public(n) for n in range(1, cur + 1)],
            "next_episode": {"number": nxt, "at_kst": kst(schedule.get(nxt), self.cfg),
                             "at": schedule[nxt].isoformat() if schedule.get(nxt) else None} if nxt else None,
            "characters": CHARACTERS,
        }

    # ---- YES/NO 질문 ------------------------------------------------------
    def question_quota(self, user_id: int) -> dict[str, int]:
        qs = self.cfg.section("questions")
        limit = int(qs.get("daily_limit", 30))
        used = self.db.questions_since(user_id, self.today_start())
        return {"limit": limit, "used": used, "remaining": max(0, limit - used), "total": self.db.total_questions(user_id)}

    async def ask(self, user_id: int, text: str, source: str = "discord", display_name: str | None = None) -> dict[str, Any]:
        self.gate()
        self.ensure_player(user_id, display_name)
        text = (text or "").strip()
        if len(text) < 3:
            raise GameError("too_short", "질문을 조금 더 길게 적어 주세요.")
        if len(text) > 200:
            raise GameError("too_long", "질문은 200자 이내로 적어 주세요.")

        qs = self.cfg.section("questions")
        now = self.clock()
        cooldown = int(qs.get("cooldown_seconds", 10))
        last = self.db.last_question_at(user_id)
        if last and (now - last).total_seconds() < cooldown:
            wait = cooldown - int((now - last).total_seconds())
            raise GameError("cooldown", f"방송부가 기록을 정리하는 중입니다. {wait}초 뒤에 다시 질문해 주세요.", wait=wait)

        character_item = self.character_bank.match(text)
        normalized = normalize_character_question(text) if character_item else self.bank.parse(text).normalized
        window = timedelta(minutes=int(qs.get("duplicate_window_minutes", 30)))
        duplicate = self.db.recent_same_question(user_id, normalized, now - window) is not None

        quota = self.question_quota(user_id)
        if quota["remaining"] <= 0 and not duplicate:
            raise GameError("limit", "오늘의 질문 기회를 모두 사용했습니다. 내일 0시(한국 시간)에 다시 채워집니다.", **quota)

        cur = self.current_episode
        unconfirmed = bool(qs.get("answer_unconfirmed", False))
        if character_item:
            flags = set()
            for flag in ("enable_seri_haneul_romantic_crush", "enable_seri_haneul_childhood"):
                if bool(qs.get(flag, False)):
                    flags.add(flag)
            character_answer = self.character_bank.answer(
                text,
                set(self.released_evidence_ids()),
                self.db.is_posted("ending"),
                flags,
                current_episode=cur,
            )
            assert character_answer is not None
            verdict = {
                "YES": Verdict.YES,
                "NO": Verdict.NO,
                "INFO": Verdict.INFO,
                "UNKNOWN": Verdict.UNCONFIRMED,
                "SEALED": Verdict.SEALED,
                "UNRELEASED": Verdict.UNRELEASED,
                "CLARIFY": Verdict.CLARIFY,
            }[character_answer.kind]
            result = AskResult(
                verdict,
                question_id=character_answer.question_id,
                canonical=character_answer.canonical,
                response_text=character_answer.response_text,
                normalized=normalized,
                via="character-v4",
            )
        elif self.ai_pick is not None:
            result = await asyncio.to_thread(self.bank.ask, text, cur, unconfirmed, self.ai_pick)
        else:
            result = self.bank.ask(text, cur, unconfirmed)

        counted = result.counts_toward_limit and not duplicate
        store_text = text if self.cfg.section("privacy").get("log_question_text", True) else None
        self.db.log_question(user_id, normalized, store_text, result.question_id, result.verdict.value, counted, source, now)

        gained = 0
        if counted:
            gained += self.rewards.grant(user_id, "first_question")
            gained += self.rewards.grant(user_id, "daily_question", self.today_key())

        related = None
        if result.related_evidence and self.catalog.is_evidence_released(
                result.related_evidence, cur, self.db.manually_released_evidence()):
            ev = self.catalog.evidence[result.related_evidence]
            related = {"id": ev.evidence_id, "title": ev.title}

        answered = result.verdict in {Verdict.YES, Verdict.NO, Verdict.IRRELEVANT, Verdict.INFO,
                                      Verdict.SEALED, Verdict.UNCONFIRMED}
        hint = result.hint
        # CLARIFY: 질문 대상/의미가 불분명. 항목의 구체적 안내를 그대로 전달한다.
        if result.verdict == Verdict.CLARIFY and result.response_text:
            hint = result.response_text
        suggestions = result.extra.get("suggestions") or []
        if suggestions:
            hint += "\n이런 질문은 답할 수 있어요: " + " / ".join(suggestions)
        return {
            "question": text,
            "verdict": result.verdict.value,
            "label": result.label,
            "hint": hint,
            "suggestions": suggestions,
            "response_text": result.response_text if answered else "",
            "matched": result.canonical if answered else None,
            "related_evidence": related if answered else None,
            "counted": counted,
            "duplicate": duplicate,
            "gained": gained,
            "quota": self.question_quota(user_id),
        }

    def question_history(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.db.question_history(user_id, limit)
        out = []
        for r in rows:
            q = self.bank.questions.get(r["question_id"]) if r["question_id"] else None
            verdict = Verdict(r["result"])
            answered = verdict in {Verdict.YES, Verdict.NO, Verdict.IRRELEVANT}
            out.append({
                "asked_at": r["asked_at"],
                "question": r["question_text"] or (q.canonical if (q and answered) else "(기록되지 않은 질문)"),
                "verdict": verdict.value,
                "label": AskResult(verdict).label,
            })
        return out

    # ---- 인물 관계도 -------------------------------------------------------
    def relationship_map(self, user_id: int) -> dict[str, Any]:
        """참가자가 심문으로 직접 답을 얻은 관계만 연다 (스포일러 방지)."""
        data = load_json(DATA_DIR / "relations.json")
        rows = self.db.query(
            "SELECT DISTINCT question_id FROM question_log WHERE user_id=? AND question_id IS NOT NULL "
            "AND result IN ('YES', 'NO', 'IRRELEVANT')", (user_id,))
        asked = {r["question_id"] for r in rows}
        # v4 공개 질문은 기존 관계도 식별자를 재사용해 과거 질문 이력과 함께 보인다.
        v4_relation_bridge = {
            "V4Q001": "Q-LOVE",
            "V4Q021": "Q-HANEUL-LOVE",
            "V4Q081": "Q-MUTUAL",
            "V4Q041": "Q-SERI-LOVE-HANEUL",
            "V4Q069": "Q-NAM-EDIT",
        }
        asked |= {legacy for modern, legacy in v4_relation_bridge.items() if modern in asked}
        relations = [r for r in data["relations"] if r["question_id"] in self.bank.questions]
        if not self.cfg.section("questions").get("enable_seri_haneul_romantic_crush", False):
            relations = [r for r in relations if r["question_id"] != "Q-SERI-LOVE-HANEUL"]
        found = [r for r in relations if r["question_id"] in asked]
        return {
            "characters": data["characters"],
            "found": found,
            "found_count": len(found),
            "total": len(relations),
            "hidden_by_character": {c: sum(1 for r in relations if r["from"] == c and r not in found)
                                    for c in data["characters"]},
        }

    def character_public(self, name: str) -> dict[str, Any] | None:
        data = load_json(DATA_DIR / "public_characters.json")
        profile = data["characters"].get(name)
        return {"name": name, **profile} if profile else None

    def relationship_public(self, first: str, second: str) -> dict[str, Any] | None:
        if first == second:
            return None
        data = load_json(DATA_DIR / "public_characters.json")
        wanted = {first, second}
        for row in data["relationships"]:
            if set(row["people"]) == wanted:
                return row
        return None

    # ---- 증거 -------------------------------------------------------------
    def evidence_board(self, user_id: int | None = None) -> list[dict[str, Any]]:
        cur = self.current_episode
        manual = self.db.manually_released_evidence()
        found = self.db.found_evidence(user_id) if user_id else set()
        investigated = self.db.investigated_evidence(user_id) if user_id else set()
        board = []
        for ev in self.catalog.sorted_evidence():
            if self.catalog._released(ev, cur, manual):
                item = ev.public(found=ev.evidence_id in found)
                # 목록에서는 조사 가능한(심화 단서가 있는) 증거와, 이미 조사를 마친 증거를 구분해 표시한다.
                item["investigable"] = bool(ev.investigation_result or ev.inference)
                item["investigated"] = ev.evidence_id in investigated
                board.append(item)
            else:
                board.append(ev.locked())
        return board

    def evidence_overview(self, user_id: int | None = None) -> dict[str, Any]:
        """회차별로 묶은 증거 현황. UI(회차 선택/페이지)에서 사용한다.
        미공개 회차의 증거는 제목·내용 없이 개수만 노출한다(스포일러 차단)."""
        cur = self.current_episode
        manual = self.db.manually_released_evidence()
        found = self.db.found_evidence(user_id) if user_id else set()
        investigated = self.db.investigated_evidence(user_id) if user_id else set()
        episodes: list[dict[str, Any]] = []
        total_found = 0
        total_released = 0
        for n in sorted(self.catalog.episodes):
            evs = self.catalog.evidence_for_episode(n)
            if not evs:
                continue
            released = n <= cur
            items: list[dict[str, Any]] = []
            ep_found = 0
            for ev in evs:
                is_open = self.catalog._released(ev, cur, manual)
                if is_open:
                    total_released += 1
                    f = ev.evidence_id in found
                    if f:
                        ep_found += 1
                        total_found += 1
                    items.append({
                        "id": ev.evidence_id, "title": ev.title, "type": ev.evidence_type,
                        "category": ev.category, "found": f,
                        "investigated": ev.evidence_id in investigated,
                        "investigable": bool(ev.investigation_result or ev.inference),
                        "locked": False,
                    })
                else:
                    items.append({"id": ev.evidence_id, "locked": True})
            episodes.append({
                "episode": n,
                "released": released,
                "count": len(evs),
                "open_count": sum(1 for i in items if not i["locked"]),
                "found_count": ep_found,
                "items": items,
            })
        return {
            "total_episodes": self.catalog.episode_count,
            "total_evidence": len(self.catalog.evidence),
            "released_evidence": total_released,
            "found_evidence": total_found,
            "current_episode": cur,
            "episodes": episodes,
        }

    def released_evidence_ids(self) -> list[str]:
        return [e.evidence_id for e in self.catalog.released_evidence(self.current_episode, self.db.manually_released_evidence())]

    def _visible_related(self, ev: "Evidence") -> list[dict[str, Any]]:
        """이 증거와 연결되며 '현재 공개된' 관련 증거만 노출한다(미공개 증거 ID·제목 누출 방지)."""
        cur = self.current_episode
        manual = self.db.manually_released_evidence()
        out = []
        for rid in ev.related_evidence:
            rel = self.catalog.evidence.get(rid)
            if rel and self.catalog._released(rel, cur, manual):
                out.append({"id": rel.evidence_id, "title": rel.title})
        return out

    def investigate(self, user_id: int, evidence_id: str, display_name: str | None = None) -> dict[str, Any]:
        """증거를 조사한다.

        - 첫 조사: 증거를 '획득'(수사 수첩 기록)하고 evidence_found 보상을 준다(기존 계약 유지).
        - 조사(심화): 획득 여부와 무관하게 investigation_result·inference·공개된 관련 증거를 보여 준다.
          심화 조사를 처음 완료하면 evidence_investigated 보상을 1회 지급한다(중복 없음).
        획득 보상은 data['gained'], 심화 보상은 data['investigate_gained'] 로 분리해 반환한다.
        """
        self.gate()
        self.ensure_player(user_id, display_name)
        evidence_id = (evidence_id or "").strip().upper()
        if not self.catalog.is_evidence_released(evidence_id, self.current_episode, self.db.manually_released_evidence()):
            raise GameError("locked", "아직 공개되지 않았거나 존재하지 않는 증거입니다.")
        ev = self.catalog.evidence[evidence_id]
        new = self.db.mark_evidence(user_id, evidence_id)
        gained = self.rewards.grant(user_id, "evidence_found", evidence_id) if new else 0
        # 심화 조사 보상: 심화 단서가 있는 증거에 한해, 사람당 증거별 1회.
        investigate_gained = 0
        if ev.investigation_result or ev.inference:
            investigate_gained = self.rewards.grant(user_id, "evidence_investigated", evidence_id)
        data = ev.public(found=True, investigated=True)
        data["related_evidence"] = self._visible_related(ev)
        data.update({"new": new, "gained": gained, "investigate_gained": investigate_gained})
        return data

    # ---- 회차 시청 --------------------------------------------------------
    def mark_watched(self, user_id: int, number: int, display_name: str | None = None) -> dict[str, Any]:
        self.gate()
        self.ensure_player(user_id, display_name)
        if number < 1 or number > self.current_episode:
            raise GameError("locked", "아직 공개되지 않은 회차입니다.")
        new = self.db.mark_watched(user_id, number)
        gained = self.rewards.grant(user_id, "watch_episode", str(number)) if new else 0
        return {"episode": number, "new": new, "gained": gained}

    # ---- 가설(추리) -------------------------------------------------------
    def submit_theory(self, user_id: int, body: str, display_name: str | None = None) -> dict[str, Any]:
        self.gate()
        self.ensure_player(user_id, display_name)
        body = (body or "").strip()
        limit = int(self.cfg.section("theory").get("max_length", 1500))
        if len(body) < 5:
            raise GameError("too_short", "추리 내용을 조금 더 적어 주세요.")
        body = body[:limit]
        self.db.add_theory(user_id, body)
        gained = self.rewards.grant(user_id, "daily_theory", self.today_key())
        return {"saved": True, "gained": gained, "count": self.db.theory_count(user_id)}

    # ---- 최종 추리 --------------------------------------------------------
    def final_status(self, user_id: int) -> dict[str, Any]:
        fin = self.cfg.section("final")
        subs = self.db.submissions(user_id)
        opens = int(fin.get("open_from_episode", 1))
        return {
            "open": self.current_episode >= opens,
            "open_from_episode": opens,
            "attempts": len(subs),
            "max_attempts": int(fin.get("max_attempts", 3)),
            "feedback": fin.get("feedback", "count"),
            "solved": any(s["solved"] for s in subs),
            "ended": self.phase() == "ended",
            "form": self.final_key.form(),
            "last": self._submission_view(subs[-1]) if subs else None,
        }

    def _submission_view(self, row) -> dict[str, Any]:
        answers = json.loads(row["answers"])
        view: dict[str, Any] = {"submitted_at": row["submitted_at"], "answers": answers}
        fb = self.cfg.section("final").get("feedback", "count")
        if self.phase() == "ended":
            view.update(self.final_key.grade(answers))
        elif fb == "count":
            view.update({"correct": row["correct_count"], "total": 5})
        return view

    def submit_final(self, user_id: int, answers: dict[str, str], display_name: str | None = None) -> dict[str, Any]:
        self.gate()
        self.ensure_player(user_id, display_name)
        status = self.final_status(user_id)
        if not status["open"]:
            raise GameError("not_open", f"최종 추리는 EP.{status['open_from_episode']:02d} 공개 후 제출할 수 있습니다.")
        if status["solved"]:
            raise GameError("solved", "이미 사건을 해결했습니다. 엔딩 공개를 기다려 주세요.")
        if status["attempts"] >= status["max_attempts"]:
            raise GameError("no_attempts", "최종 추리 제출 기회를 모두 사용했습니다.")
        clean = {k: (answers.get(k) or "").strip()[:1500] for k in ("q1", "q2", "q3", "q4", "q5", "story")}
        for k in ("q1", "q2", "q3", "q4"):
            if clean[k] not in CHARACTERS:
                raise GameError("invalid", "Q1~Q4 는 인물 목록에서 골라 주세요.")
        if len(clean["q5"]) < 10:
            raise GameError("invalid", "Q5 에는 '왜, 어떻게' 그렇게 했는지 한두 문장으로 설명해 주세요.")

        graded = self.final_key.grade(clean)
        self.db.add_submission(user_id, clean, graded["correct"], graded["solved"])
        gained = self.rewards.grant(user_id, "final_submit")
        ended = self.phase() == "ended"
        if ended:
            gained += self._grant_final_rewards(user_id)

        result: dict[str, Any] = {"saved": True, "gained": gained,
                                  "attempts": status["attempts"] + 1, "max_attempts": status["max_attempts"]}
        fb = self.cfg.section("final").get("feedback", "count")
        if ended:
            result.update(graded)
        elif fb == "count":
            result.update({"correct": graded["correct"], "total": graded["total"], "solved": graded["solved"]})
        return result

    def _grant_final_rewards(self, user_id: int) -> int:
        subs = self.db.submissions(user_id)
        if not subs:
            return 0
        best = max(subs, key=lambda s: (s["solved"], s["correct_count"]))
        graded = self.final_key.grade(json.loads(best["answers"]))
        gained = 0
        for key, ok in graded["items"].items():
            if ok:
                gained += self.rewards.grant(user_id, "final_correct_item", key)
        if graded["solved"]:
            gained += self.rewards.grant(user_id, "case_solved")
        return gained

    def finalize_all(self) -> int:
        """엔딩 공개 시점에 제출자 전원의 정답 보상을 정산한다 (중복 지급 없음)."""
        total = 0
        for row in self.db.all_players():
            total += self._grant_final_rewards(row["user_id"])
        return total

    def ending_text(self) -> dict[str, str]:
        f = self.final_key.items
        return {
            "q1": f"{f['q1']['label']} → {f['q1']['answer']}",
            "q2": f"{f['q2']['label']} → {f['q2']['answer']}",
            "q3": f"{f['q3']['label']} → {f['q3']['answer']}",
            "q4": f"{f['q4']['label']} → {f['q4']['answer']}",
            "q5": f"{f['q5']['label']} → {f['q5']['model_answer']}",
        }

    # ---- 진행도 -----------------------------------------------------------
    def progress(self, user_id: int) -> dict[str, Any]:
        player = self.db.get_player(user_id)
        released = self.released_evidence_ids()
        found = self.db.found_evidence(user_id)
        subs = self.db.submissions(user_id)
        if not player:
            status = "조사 시작 전"
        elif any(s["solved"] for s in subs) and self.phase() == "ended":
            status = "사건 해결"
        elif subs:
            status = "최종 추리 제출 완료"
        elif found or self.db.total_questions(user_id):
            status = "수사 중"
        else:
            status = "조사 시작 전"
        return {
            "registered": player is not None,
            "status": status,
            "current_episode": self.current_episode,
            "total_episodes": self.catalog.episode_count,
            "watched": sorted(self.db.watched_episodes(user_id)),
            "evidence_found": len(found & set(released)),
            "evidence_released": len(released),
            "evidence_total": len(self.catalog.evidence),
            "questions": self.question_quota(user_id),
            "theories": self.db.theory_count(user_id),
            "final_attempts": len(subs),
            "final_max_attempts": int(self.cfg.section("final").get("max_attempts", 3)),
            "points": self.rewards.total(user_id),
            "currency": self.rewards.currency,
        }

    # ---- 랭킹(공개) -------------------------------------------------------
    def ranking(self, top: int = 10, user_id: int | None = None) -> dict[str, Any]:
        """공개 랭킹용 데이터. 순위·표시이름·포인트만 담고 스포일러(정답 여부 등)는 넣지 않는다.
        user_id 를 주면 그 사람의 등수/포인트를 함께 반환한다(자기 위치 확인용)."""
        rows = self.db.leaderboard()  # 포인트 내림차순 전체
        entries = [{"rank": i, "user_id": r["user_id"],
                    "display_name": r["display_name"] or "익명 조사원", "points": int(r["points"])}
                   for i, r in enumerate(rows, start=1)]
        me = None
        if user_id is not None:
            me = next((e for e in entries if e["user_id"] == user_id), None)
        return {
            "currency": self.rewards.currency,
            "total_players": len(entries),
            "top": entries[:top],
            "me": me,
        }

    # ---- 수사 노트 --------------------------------------------------------
    def get_note(self, user_id: int) -> dict[str, Any]:
        row = self.db.get_note(user_id)
        return {"body": row["body"] if row else "", "updated_at": row["updated_at"] if row else None}

    def save_note(self, user_id: int, body: str) -> dict[str, Any]:
        self.db.save_note(user_id, (body or "")[:5000])
        return self.get_note(user_id)


VIDEO_OVERRIDES_KEY = "video_urls"


def apply_video_overrides(catalog: Catalog, db: Database) -> None:
    """/운영 영상 으로 등록한 링크(DB)를 episodes.json 값보다 우선 적용한다."""
    for number, url in (db.get_kv(VIDEO_OVERRIDES_KEY, {}) or {}).items():
        ep = catalog.episodes.get(int(number))
        if ep is not None:
            ep.video_url = url or None


def build_service(cfg: Config, db: Database | None = None) -> GameService:
    """봇·웹 API·CLI 가 같은 방식으로 게임 서비스를 조립한다."""
    from .ai import make_ai_picker
    from .rewards import RewardTable

    db = db or Database(cfg.db_path)
    catalog = Catalog.load()
    apply_video_overrides(catalog, db)
    bank = QuestionBank.load()
    rewards = RewardService(db, RewardTable.load())
    ai_pick = make_ai_picker(cfg.anthropic_api_key, cfg.ai_model) if cfg.ai_enabled else None
    return GameService(cfg, db, catalog, bank, rewards, FinalKey.load(), ai_pick)
