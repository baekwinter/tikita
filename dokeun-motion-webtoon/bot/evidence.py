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

    @property
    def image_file(self) -> Path | None:
        p = resolve(self.image)
        return p if p and p.is_file() else None

    def public(self, found: bool = False) -> dict[str, Any]:
        return {
            "id": self.evidence_id,
            "title": self.title,
            "category": self.category,
            "episode": self.release_episode,
            "summary": self.summary,
            "detail": self.detail,
            "has_image": self.image_file is not None,
            "tags": self.tags,
            "found": found,
            "locked": False,
        }

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
            ev = Evidence(
                evidence_id=raw["evidence_id"],
                title=raw["title"],
                category=raw.get("category", ""),
                release_episode=int(raw["release_episode"]),
                summary=raw.get("summary", ""),
                detail=raw.get("detail", ""),
                image=raw.get("image"),
                tags=list(raw.get("tags") or []),
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

    def released_evidence(self, current_episode: int, manual: set[str] | None = None) -> list[Evidence]:
        manual = manual or set()
        return [e for e in self.sorted_evidence() if e.release_episode <= current_episode or e.evidence_id in manual]

    def is_evidence_released(self, evidence_id: str, current_episode: int, manual: set[str] | None = None) -> bool:
        ev = self.evidence.get(evidence_id)
        return bool(ev and (ev.release_episode <= current_episode or evidence_id in (manual or set())))

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
