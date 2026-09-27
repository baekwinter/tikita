"""회차(episodes.json)와 증거(evidence.json) 카탈로그.

공개 여부 판단은 항상 이 모듈을 거친다. 미공개 항목의 내용은 참가자용 출력에 넣지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import DATA_DIR, PROJECT_DIR, load_json


def resolve(rel: str | None) -> Path | None:
    if not rel:
        return None
    p = Path(rel)
    return p if p.is_absolute() else PROJECT_DIR / p


@dataclass
class Episode:
    number: int
    title: str | None
    description: str | None
    keywords: list[str]
    video_path: str | None
    video_url: str | None
    thumbnail: str | None
    release_datetime: str | None
    clues: list[str]
    questions: list[str] = field(default_factory=list)

    @property
    def code(self) -> str:
        return f"EP.{self.number:02d}"

    @property
    def display_title(self) -> str:
        return f"{self.code} {self.title}" if self.title else self.code

    @property
    def video_file(self) -> Path | None:
        p = resolve(self.video_path)
        return p if p and p.is_file() else None

    @property
    def thumbnail_file(self) -> Path | None:
        p = resolve(self.thumbnail)
        return p if p and p.is_file() else None

    def media_status(self, upload_limit_mb: float) -> str:
        """attach | url | too_large | missing"""
        f = self.video_file
        if f and f.stat().st_size <= upload_limit_mb * 1024 * 1024:
            return "attach"
        if self.video_url:
            return "url"
        if f:
            return "too_large"
        return "missing"


@dataclass
class Evidence:
    evidence_id: str
    title: str
    category: str
    release_episode: int
    summary: str
    detail: str
    image: str | None
    tags: list[str]
    # ---- PHASE 2 확장 필드 (모두 선택. 없으면 기존 동작과 동일) ----------------
    evidence_type: str = ""            # digital | emotion | testimony | decisive
    related_characters: list[str] = field(default_factory=list)
    related_evidence: list[str] = field(default_factory=list)
    investigation_result: str = ""     # 조사(심화)했을 때만 보여 주는 추가 단서 (공개용)
    inference: str = ""                # 이 증거가 추리에 기여하는 방향 (공개용, 스포일러 아님)
    reward: int | None = None          # 이 증거 조사 보상(미지정이면 기본 evidence_found 표 사용)
    spoiler_level: int = 0             # 0=공개 안전, 1=회차 열람 후, 2=확정 스포일러(엄격 게이팅)
    # 운영진 전용 메모(정답 해설). 참가자 공개 payload 에는 절대 넣지 않는다.
    admin_note: str = ""

    @property
    def image_file(self) -> Path | None:
        p = resolve(self.image)
        return p if p and p.is_file() else None

    def public(self, found: bool = False, investigated: bool = False) -> dict[str, Any]:
        """참가자 공개용 payload. admin_note 는 절대 포함하지 않는다.
        investigation_result/inference 는 조사(investigated=True)한 뒤에만 채운다."""
        data = {
            "id": self.evidence_id,
            "title": self.title,
            "category": self.category,
            "episode": self.release_episode,
            "summary": self.summary,
            "detail": self.detail,
            "has_image": self.image_file is not None,
            "tags": self.tags,
            "type": self.evidence_type,
            "related_characters": list(self.related_characters),
            "related_evidence": list(self.related_evidence),
            "found": found,
            "investigated": investigated,
            "locked": False,
        }
        if investigated:
            data["investigation_result"] = self.investigation_result
            data["inference"] = self.inference
        return data

    def locked(self) -> dict[str, Any]:
        """잠긴 증거는 번호와 '몇 화에 열리는지'만 보여 준다. 제목도 숨긴다."""
        return {"id": self.evidence_id, "episode": self.release_episode, "locked": True}


class Catalog:
    def __init__(self, episodes_doc: dict, evidence_doc: dict):
        self.episodes: dict[int, Episode] = {}
        for raw in episodes_doc["episodes"]:
            ep = Episode(
                number=int(raw["episode_number"]),
                title=raw.get("title"),
                description=raw.get("description"),
                keywords=list(raw.get("keywords") or []),
                video_path=raw.get("video_path"),
                video_url=raw.get("video_url"),
                thumbnail=raw.get("thumbnail"),
                release_datetime=raw.get("release_datetime"),
                clues=list(raw.get("clues") or []),
                questions=list(raw.get("questions") or []),
            )
            self.episodes[ep.number] = ep
        self.evidence: dict[str, Evidence] = {}
        for raw in evidence_doc["evidence"]:
            # minimum_episode 는 release_episode 의 별칭으로도 허용(하위 호환)
            release_ep = int(raw.get("release_episode", raw.get("minimum_episode")))
            ev = Evidence(
                evidence_id=raw["evidence_id"],
                title=raw["title"],
                category=raw.get("category", ""),
                release_episode=release_ep,
                summary=raw.get("summary", ""),
                detail=raw.get("detail", ""),
                image=raw.get("image"),
                tags=list(raw.get("tags") or []),
                evidence_type=raw.get("evidence_type", ""),
                related_characters=list(raw.get("related_characters") or []),
                related_evidence=list(raw.get("related_evidence") or []),
                investigation_result=raw.get("investigation_result", ""),
                inference=raw.get("inference", ""),
                reward=raw.get("reward"),
                spoiler_level=int(raw.get("spoiler_level", 0)),
                admin_note=raw.get("admin_note", ""),
            )
            self.evidence[ev.evidence_id] = ev

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "Catalog":
        return cls(load_json(data_dir / "episodes.json"), load_json(data_dir / "evidence.json"))

    @property
    def episode_count(self) -> int:
        return len(self.episodes)

    def sorted_episodes(self) -> list[Episode]:
        return [self.episodes[n] for n in sorted(self.episodes)]

    def sorted_evidence(self) -> list[Evidence]:
        return sorted(self.evidence.values(), key=lambda e: (e.release_episode, e.evidence_id))

    @staticmethod
    def _released(ev: Evidence, current_episode: int, manual: set[str]) -> bool:
        """공개 여부. spoiler_level 2(확정 스포일러)는 수동 공개로도 조기 해금하지 못하고,
        반드시 release_episode 회차가 실제로 공개되어야 열린다."""
        if ev.release_episode <= current_episode:
            return True
        if ev.spoiler_level >= 2:
            return False  # 확정 스포일러는 회차 게이팅만 인정 (임의/수동 조기 공개 차단)
        return ev.evidence_id in manual

    def released_evidence(self, current_episode: int, manual: set[str] | None = None) -> list[Evidence]:
        manual = manual or set()
        return [e for e in self.sorted_evidence() if self._released(e, current_episode, manual)]

    def is_evidence_released(self, evidence_id: str, current_episode: int, manual: set[str] | None = None) -> bool:
        ev = self.evidence.get(evidence_id)
        return bool(ev and self._released(ev, current_episode, manual or set()))

    def evidence_for_episode(self, number: int) -> list[Evidence]:
        return [e for e in self.sorted_evidence() if e.release_episode == number]

    def validate(self) -> list[str]:
        problems: list[str] = []
        numbers = sorted(self.episodes)
        if numbers != list(range(1, len(numbers) + 1)):
            problems.append(f"회차 번호가 1부터 연속되지 않습니다: {numbers}")
        for ep in self.episodes.values():
            for cid in ep.clues:
                ev = self.evidence.get(cid)
                if ev is None:
                    problems.append(f"{ep.code}: 존재하지 않는 증거 {cid}")
                elif ev.release_episode != ep.number:
                    problems.append(f"{ep.code}: clues 의 {cid} 는 evidence.json 에서 {ev.release_episode}화 공개로 되어 있습니다")
        for ev in self.evidence.values():
            if ev.release_episode not in self.episodes:
                problems.append(f"{ev.evidence_id}: 없는 회차 {ev.release_episode}")
            elif ev.evidence_id not in self.episodes[ev.release_episode].clues:
                problems.append(f"{ev.evidence_id}: {ev.release_episode}화 clues 목록에 없습니다")
        return problems
