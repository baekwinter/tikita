"""캐릭터 감정·관계 질문의 공개용 결정론적 해석기.

운영진용 딥 바이블이나 정답표를 참가자 입력/LLM에 전달하지 않는다. 이 모듈은
검수된 공개 답변 projection(`character_qa.json`)만 읽으며, 사건 정답 질문은 별도의
sealed 결과로 돌려 기존 `/정답` 흐름과 분리한다.

자연어 이해는 3단계로 나뉜다.
  1. 인물·관계 식별: 질문에 등장한 인물과 그 문장 속 역할(주어/목적어), "두 사람/서로"
     같은 관계 표현의 대상까지 판정한다.
  2. 질문 의도·감정 개념 식별: 좋아함/거절함/거절당함(오해)/교제/질투/인지/원인(왜) 등
     개념과 의도(STATE/BELIEF/CAUSE/IDENTITY)를 뽑는다.
  3. 확정 데이터 조회: 정확 일치 → 방향·개념·의도 구조 매칭 → (방향 상충 후보를 뺀)
     유사도 보조 순으로 답을 찾는다. 방향이 반대인 질문은 유사도가 높아도 같은 질문으로
     보지 않는다. 대상이 불명확하면 CLARIFY 로 되묻는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
import re
import unicodedata

from .config import DATA_DIR, load_json


STAGE_EVIDENCE = {
    "INTRO": frozenset(),
    "ACT1": frozenset({"E-01"}),
    "ACT2": frozenset({"E-06"}),
    "ACT3": frozenset({"E-03"}),
    "ACT4": frozenset({"E-04"}),
}

ALIASES = {
    "반휘혈": ("반휘혈", "휘혈", "휘혈이", "부장"),
    "온하늘": ("온하늘", "하늘", "하늘이", "아나운서"),
    "차세리": ("차세리", "세리", "세리랑", "작가"),
    "남궁호": ("남궁호", "궁호", "궁호가", "기술담당"),
}

_ALIAS_TO_CANONICAL = {
    alias: canonical for canonical, aliases in ALIASES.items() for alias in aliases
}
_ALIAS_RE = re.compile("|".join(re.escape(alias) for alias in sorted(_ALIAS_TO_CANONICAL, key=len, reverse=True)))

# 관계 표현(두 사람/둘/서로/쌍방). 기본 대상은 정본상 주 로맨스 축(반휘혈·온하늘).
_PAIR_MARKERS = ("두사람", "두명", "둘이", "둘은", "둘의", "둘다", "둘", "그둘", "두분", "둘사이")
_MUTUAL_MARKERS = ("서로", "쌍방", "양쪽", "상호")
DEFAULT_PAIR = frozenset({"반휘혈", "온하늘"})

# 조사 → 역할. 이름 바로 뒤 문자열로 판정한다.
_SUBJECT_PARTICLES = ("께서", "은", "는", "이", "가", "도")
_OBJECT_PARTICLES = ("에게서", "에게", "한테", "께", "을", "를", "와", "과", "랑", "하고")

# 감정/사건 개념 사전. 긴 표현을 앞에 둬 부분 오인을 줄인다.
# BELIEF(오해·믿음) 신호는 정규화로 지워지면 안 되므로 원문 기준으로 검사한다.
_CONCEPT_WORDS: list[tuple[str, str]] = [
    # 거절당함(오해·믿음) — '거절함'보다 먼저 검사
    ("거절당했다고생각", "거절당함"), ("거절당했다고믿", "거절당함"), ("거절당했다고느", "거절당함"),
    ("거절당했다고", "거절당함"), ("거절당했", "거절당함"), ("거절당", "거절당함"),
    ("차였다고", "거절당함"), ("차였", "거절당함"),
    ("싫어한다고생각", "거절당함"), ("싫어한다고믿", "거절당함"), ("싫어한다고", "거절당함"),
    ("자길거절", "거절당함"), ("자기를거절", "거절당함"), ("자신을거절", "거절당함"),
    # 거절함(주체가 상대를 거절)
    ("거절했", "거절함"), ("거절하", "거절함"), ("거절", "거절함"),
    ("퇴짜", "거절함"), ("찼", "거절함"),
    # 상호
    ("서로좋아", "상호"), ("쌍방", "상호"), ("서로마음", "상호"), ("양쪽다", "상호"), ("서로", "상호"),
    # 교제
    ("사귀는사이", "교제"), ("사귀", "교제"), ("연애", "교제"), ("커플", "교제"), ("연인", "교제"),
    # 좋아함
    ("좋아", "좋아함"), ("사랑", "좋아함"), ("호감", "좋아함"), ("마음이있", "좋아함"),
    ("마음있", "좋아함"), ("마음이", "좋아함"), ("반했", "좋아함"), ("설레", "좋아함"),
    ("아껴", "좋아함"), ("아끼", "좋아함"), ("아낀", "좋아함"), ("소중", "좋아함"),
    # 싫어함(단순)
    ("싫어", "싫어함"), ("미워", "싫어함"),
    # 질투
    ("질투", "질투"), ("시기", "질투"),
    # 인지/앎
    ("알고있", "인지"), ("알았", "인지"), ("눈치", "인지"), ("알아", "인지"), ("알던", "인지"),
    # 답장/의미/전달
    ("답장", "답장"), ("회신", "답장"),
    ("무슨뜻", "의미이해"), ("의미를이해", "의미이해"), ("의미", "의미이해"), ("뜻인지", "의미이해"),
    ("전달되지", "전달실패"), ("전달안", "전달실패"), ("전송실패", "전달실패"), ("미전송", "전달실패"),
    # 우정
    ("우정", "우정"), ("친구", "우정"),
]

# 원인·동기(왜/어떻게) 신호.
_CAUSE_WORDS = ("왜", "어째서", "무슨이유", "어떤이유", "무슨까닭", "어떻게해서")


def normalize_character_question(text: str) -> str:
    value = unicodedata.normalize("NFC", text or "").lower()
    value = _ALIAS_RE.sub(lambda match: _ALIAS_TO_CANONICAL[match.group(0)], value)
    value = re.sub(r"(인가요|하나요|했나요|인가|이야|야|니|나요|어요|아요|해요|해|함|했어|거야|적이)", "", value)
    return re.sub(r"[^0-9a-z가-힣]", "", value)


def _norm_raw(text: str) -> str:
    """별칭만 정규화하고 어미는 보존한다(방향 신호 유지용)."""
    value = unicodedata.normalize("NFC", text or "").lower()
    value = _ALIAS_RE.sub(lambda match: _ALIAS_TO_CANONICAL[match.group(0)], value)
    return re.sub(r"\s+", "", value)


def _people(text: str) -> frozenset[str]:
    return frozenset(name for name in ALIASES if name in text)


def _roles(raw: str) -> dict[str, str]:
    """별칭 정규화된 원문에서 각 인물의 역할(subject/object)을 조사로 판정."""
    names = sorted(ALIASES, key=len, reverse=True)
    name_re = re.compile("|".join(re.escape(n) for n in names))
    roles: dict[str, str] = {}
    for m in name_re.finditer(raw):
        name = m.group(0)
        if name in roles:
            continue
        tail = raw[m.end(): m.end() + 4]
        if tail.startswith(_OBJECT_PARTICLES):
            roles[name] = "object"
        elif tail.startswith(_SUBJECT_PARTICLES):
            roles[name] = "subject"
    return roles


def _concepts(raw: str) -> set[str]:
    residual = raw
    found: set[str] = set()
    for word, concept in _CONCEPT_WORDS:
        if word in residual:
            found.add(concept)
            residual = residual.replace(word, "·")
    return found


def _intent(raw: str, concepts: set[str]) -> str:
    if any(w in raw for w in _CAUSE_WORDS):
        return "CAUSE"
    if "거절당함" in concepts:
        return "BELIEF"
    return "STATE"


@dataclass(frozen=True)
class Signals:
    """질문 또는 canonical 에서 뽑은 해석 신호."""
    people: frozenset[str]
    roles: dict[str, str]
    concepts: frozenset[str]
    intent: str
    pair: bool          # 관계 표현(두 사람/서로) 포함 여부
    mutual: bool        # 상호(서로/쌍방) 여부
    subject: str | None
    object: str | None


def analyze(text: str) -> Signals:
    raw = _norm_raw(text)
    people = _people(raw)
    roles = _roles(raw)
    concepts = _concepts(raw)
    intent = _intent(raw, concepts)
    pair = any(m in raw for m in _PAIR_MARKERS)
    mutual = any(m in raw for m in _MUTUAL_MARKERS) or "상호" in concepts
    subject = next((p for p, r in roles.items() if r == "subject"), None)
    obj = next((p for p, r in roles.items() if r == "object"), None)
    return Signals(people, roles, frozenset(concepts), intent, pair, mutual, subject, obj)


# 방향이 상충하면 절대 같은 질문으로 보지 않을 개념쌍
_OPPOSITE = {
    frozenset({"거절함", "거절당함"}),
    frozenset({"좋아함", "싫어함"}),
    frozenset({"교제", "상호"}),  # '사귀는가(교제)'와 '서로 좋아하는가(상호)'는 다른 질문
}


def _direction_conflict(a: Signals, b: Signals) -> bool:
    """두 신호의 감정 방향이 상충하는가."""
    # 방향 개념 상충
    for pair in _OPPOSITE:
        if (pair & a.concepts) and (pair & b.concepts) and (pair & a.concepts) != (pair & b.concepts):
            return True
    # 같은 방향 개념을 공유하는데 주어/목적어가 뒤바뀌면 상충
    shared = a.concepts & b.concepts & {"좋아함", "거절함", "거절당함", "싫어함", "인지"}
    if shared and a.subject and b.subject and not a.mutual and not b.mutual:
        if a.subject != b.subject and a.people == b.people and len(a.people) >= 2:
            return True
    return False


@dataclass(frozen=True)
class CharacterAnswer:
    question_id: str
    canonical: str
    response_text: str
    kind: str
    minimum_stage: str
    feature_flag: str | None = None
    aliases: tuple[str, ...] = ()
    intent: str = "STATE"
    minimum_episode: int | None = None


class CharacterQuestionBank:
    def __init__(self, doc: dict):
        self.items = [
            CharacterAnswer(
                question_id=row["id"],
                canonical=row["question"],
                response_text=row["approved_public_answer"],
                kind=row.get("answer_kind", "INFO"),
                minimum_stage=row.get("minimum_stage", "INTRO"),
                feature_flag=row.get("feature_flag"),
                aliases=tuple(a for a in row.get("aliases", []) if a),
                minimum_episode=row.get("minimum_episode"),
            )
            for row in doc.get("questions", [])
        ]
        self._normalized = {q.question_id: normalize_character_question(q.canonical) for q in self.items}
        # canonical 신호(방향 판정용): canonical + 첫 alias 를 함께 반영
        self._signals: dict[str, Signals] = {q.question_id: analyze(q.canonical) for q in self.items}
        self._exact: dict[str, CharacterAnswer] = {}
        for item in self.items:
            for phrase in (item.canonical, *item.aliases):
                if value := normalize_character_question(phrase):
                    self._exact.setdefault(value, item)

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "CharacterQuestionBank":
        return cls(load_json(data_dir / "character_qa.json"))

    # ---- 대상(인물) 해석 --------------------------------------------------
    def _resolve_people(self, sig: Signals) -> tuple[frozenset[str], bool]:
        """(대상 인물집합, clarify 필요 여부). 관계 표현의 대상까지 결정한다."""
        if sig.people:
            return sig.people, False
        if sig.pair or sig.mutual:
            # 인물 미명시 + 관계 표현. 감정/교제/상호/오해 개념이면 주 로맨스 축으로 본다.
            if sig.concepts & {"좋아함", "상호", "교제", "거절함", "거절당함", "싫어함"}:
                return DEFAULT_PAIR, False
            # 그 외(동기 등)도 두 선배(휘혈·하늘) 맥락이 기본이나, 개념이 전혀 없으면 애매.
            if sig.intent == "CAUSE" or sig.concepts:
                return DEFAULT_PAIR, False
            return frozenset(), True  # 진짜 불명확 → CLARIFY
        return frozenset(), False

    # ---- 매칭 -------------------------------------------------------------
    def match(self, text: str) -> CharacterAnswer | None:
        norm = normalize_character_question(text)
        if not norm:
            return None
        # 1) 정확 일치 (canonical/alias)
        if norm in self._exact:
            return self._exact[norm]

        sig = analyze(text)
        target, need_clarify = self._resolve_people(sig)
        if need_clarify:
            return self._clarify()

        # 2) 구조 매칭: 대상 인물 + 개념 교집합 + 방향 무충돌 + 의도 호환
        structural = self._structural_match(text, sig, target)
        if structural is not None:
            return structural

        # 3) 유사도 보조 (방향 상충 후보 제외)
        return self._fuzzy_match(norm, sig, target)

    def _structural_match(self, text: str, sig: Signals, target: frozenset[str]) -> CharacterAnswer | None:
        if not sig.concepts and sig.intent != "CAUSE":
            return None
        scored: list[tuple[float, CharacterAnswer]] = []
        for item in self.items:
            csig = self._signals[item.question_id]
            # 인물 대상 확인: 관계형이면 대상집합 일치/부분집합 허용
            if target:
                cpeople = csig.people if csig.people else (DEFAULT_PAIR if (csig.pair or csig.mutual) else frozenset())
                if cpeople:
                    if not (target <= cpeople or cpeople <= target):
                        continue
                elif csig.people and not (target & csig.people):
                    continue
            # 개념 교집합
            shared = sig.concepts & csig.concepts
            if sig.intent == "CAUSE":
                if csig.intent != "CAUSE" and "왜" not in normalize_character_question(item.canonical):
                    # 동기 질문은 CAUSE 의도 항목(또는 canonical 에 '왜')으로만
                    if not shared:
                        continue
            elif not shared:
                continue
            # 방향 무충돌
            if _direction_conflict(sig, csig):
                continue
            # 주어 방향 일치 가산
            score = 3.0 * len(shared)
            if sig.subject and csig.subject and sig.subject == csig.subject:
                score += 2.0
            if sig.mutual and csig.mutual:
                score += 2.0
            if sig.intent == csig.intent:
                score += 1.0
            score += SequenceMatcher(None, normalize_character_question(text),
                                     self._normalized[item.question_id]).ratio()
            scored.append((score, item))
        if not scored:
            return None
        scored.sort(key=lambda r: r[0], reverse=True)
        if len(scored) > 1 and abs(scored[0][0] - scored[1][0]) < 0.5:
            # 동점에 가까우면 방향/주어로 최종 구분, 그래도 모호하면 유사도로 넘긴다
            top = [it for sc, it in scored if abs(sc - scored[0][0]) < 0.5]
            best = self._disambiguate(sig, top)
            if best is not None:
                return best
        return scored[0][1]

    def _disambiguate(self, sig: Signals, candidates: list[CharacterAnswer]) -> CharacterAnswer | None:
        # 주어가 명시됐으면 주어 일치 항목 우선
        if sig.subject:
            same = [c for c in candidates if self._signals[c.question_id].subject == sig.subject]
            if len(same) == 1:
                return same[0]
        # 상호 여부 일치
        mutual = [c for c in candidates if self._signals[c.question_id].mutual == sig.mutual]
        if len(mutual) == 1:
            return mutual[0]
        return None

    def _fuzzy_match(self, norm: str, sig: Signals, target: frozenset[str]) -> CharacterAnswer | None:
        scored: list[tuple[float, CharacterAnswer]] = []
        for item in self.items:
            csig = self._signals[item.question_id]
            if sig.people and csig.people and sig.people != csig.people:
                continue
            if _direction_conflict(sig, csig):
                continue
            ratio = SequenceMatcher(None, norm, self._normalized[item.question_id]).ratio()
            if ratio >= 0.72:
                scored.append((ratio, item))
        if not scored:
            return None
        scored.sort(key=lambda row: row[0], reverse=True)
        if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.04:
            return None
        return scored[0][1]

    def _clarify(self) -> CharacterAnswer:
        return CharacterAnswer(
            question_id="__CLARIFY__",
            canonical="",
            response_text="누구에 대한 질문인지 알려 주세요. 예: 반휘혈과 온하늘, 차세리와 온하늘.",
            kind="CLARIFY",
            minimum_stage="INTRO",
        )

    # ---- 공개 게이팅 ------------------------------------------------------
    @staticmethod
    def available(item: CharacterAnswer, released_evidence: set[str], finale: bool,
                  current_episode: int | None = None) -> bool:
        # stage 게이팅과 episode 게이팅을 모두 만족해야 공개 (더 엄격한 쪽 적용).
        if item.minimum_stage in {"FINALE", "FINAL_IDENTITY"}:
            stage_ok = finale
        else:
            stage_ok = STAGE_EVIDENCE.get(item.minimum_stage, frozenset()).issubset(released_evidence)
        episode_ok = True
        if item.minimum_episode is not None:
            episode_ok = (current_episode or 0) >= item.minimum_episode
        return stage_ok and episode_ok

    def _gated(self, item: CharacterAnswer, kind: str, text: str) -> CharacterAnswer:
        return CharacterAnswer(
            item.question_id, item.canonical, text, kind, item.minimum_stage,
            item.feature_flag, item.aliases, item.intent, item.minimum_episode,
        )

    def answer(
        self,
        text: str,
        released_evidence: set[str],
        finale: bool,
        enabled_flags: set[str] | None = None,
        current_episode: int | None = None,
    ) -> CharacterAnswer | None:
        item = self.match(text)
        if item is None:
            return None
        if item.kind == "CLARIFY":
            return item
        enabled_flags = enabled_flags or set()
        if item.feature_flag and item.feature_flag not in enabled_flags:
            return self._gated(item, "UNKNOWN", "현재 확정된 자료만으로는 확인할 수 없어요.")
        if item.minimum_stage == "FINAL_IDENTITY" and not finale:
            return self._gated(item, "SEALED", item.response_text)
        if not self.available(item, released_evidence, finale, current_episode):
            return self._gated(item, "UNRELEASED", "아직 공개되지 않은 정보입니다.")
        return item
