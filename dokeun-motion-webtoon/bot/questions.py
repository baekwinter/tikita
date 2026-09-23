"""YES/NO 탐정 질문 해석기.

원칙
- 확정된 질문 데이터(questions.json)와 정답(answers.json)만으로 답한다.
- 단순 키워드 포함만으로 답하지 않는다. 인물 조합, 필수 개념, 주어 역할이 모두 맞아야
  같은 질문으로 인정하고, 조금이라도 애매하면 "질문을 조금 더 구체적으로" 로 돌려보낸다.
- 부정형 질문("~하지 않았나요?")은 YES/NO 가 뒤집혀 오답이 될 수 있어 긍정형으로 다시 묻게 한다.
- AI 해석기(선택)는 '공개된 질문 목록 중 어느 것과 같은 뜻인지'만 고른다. 정답은 AI 에게 주지 않는다.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .config import DATA_DIR, load_json


class Verdict(str, Enum):
    YES = "YES"
    NO = "NO"
    IRRELEVANT = "IRRELEVANT"
    UNRELEASED = "UNRELEASED"
    UNCLEAR = "UNCLEAR"
    NEGATIVE_FORM = "NEGATIVE_FORM"
    UNCONFIRMED = "UNCONFIRMED"


VERDICT_LABEL = {
    Verdict.YES: "YES",
    Verdict.NO: "NO",
    Verdict.IRRELEVANT: "관계없음",
    Verdict.UNRELEASED: "아직 공개되지 않은 정보입니다.",
    Verdict.UNCLEAR: "질문을 조금 더 구체적으로 해주세요.",
    Verdict.NEGATIVE_FORM: "질문을 조금 더 구체적으로 해주세요.",
    Verdict.UNCONFIRMED: "질문을 조금 더 구체적으로 해주세요.",
}

VERDICT_HINT = {
    Verdict.UNCLEAR: "인물 이름과 행동을 넣어 예/아니오로 답할 수 있게 물어봐 주세요. 예) 반휘혈이 고백을 녹음했나요?",
    Verdict.NEGATIVE_FORM: "부정형 질문은 답이 헷갈릴 수 있어요. '~했나요?' 처럼 긍정형으로 다시 물어봐 주세요.",
    Verdict.UNCONFIRMED: "방송부가 아직 확인하지 못한 방향의 질문이에요. 다른 방향으로 질문해 보세요.",
    Verdict.UNRELEASED: "다음 회차가 공개된 뒤에 다시 물어봐 주세요.",
}

# 부정 표현. '허락 없이' 같은 무단 개념은 개념 추출 단계에서 먼저 소거되므로 여기서 걸리지 않는다.
NEGATION_RE = re.compile(r"(않|못|아니|없|안(했|한|하|좋|넣|받|들|보|틀|녹|전|왔|갔|됐|된|되))")

SUBJECT_PARTICLES = ("께서", "이가", "은", "는", "이", "가", "도")
OBJECT_PARTICLES = ("에게서", "에게", "한테", "께", "을", "를", "와", "과", "랑", "하고")
OWNER_PARTICLES = ("의",)
# '온하늘이야?', '차세리인가요?' 처럼 이름 뒤에 붙는 서술격 조사는 주어 표지가 아니다.
COPULA_ENDINGS = ("이야", "이에", "이지", "이었", "이냐", "이니", "이라", "이죠", "이다", "이여", "인")


NON_PERSON_ENTITIES = {"2025", "2026", "두사람"}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").lower()
    text = re.sub(r"[\s​]+", "", text)
    return re.sub(r"[^0-9a-z가-힣]", "", text)


@dataclass
class Question:
    question_id: str
    canonical: str
    variations: list[str]
    entity_sets: list[frozenset[str]]
    concept_groups: list[set[str]]
    optional: set[str]
    subject: str | None
    not_subject: set[str]
    subject_strict: bool = False

    @property
    def allowed_concepts(self) -> set[str]:
        out = set(self.optional)
        for g in self.concept_groups:
            out |= g
        return out


@dataclass
class Answer:
    answer: str | None
    minimum_episode: int
    related_evidence: str | None
    response_text: str
    confirmed: bool


@dataclass
class Parsed:
    normalized: str
    residual: str
    entities: frozenset[str]
    concepts: set[str]
    roles: dict[str, str]
    order: list[str]
    negated: bool


@dataclass
class AskResult:
    verdict: Verdict
    question_id: str | None = None
    canonical: str | None = None
    response_text: str = ""
    related_evidence: str | None = None
    normalized: str = ""
    via: str = "rules"
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return VERDICT_LABEL[self.verdict]

    @property
    def hint(self) -> str:
        return VERDICT_HINT.get(self.verdict, "")

    @property
    def counts_toward_limit(self) -> bool:
        """해석하지 못한 질문은 질문 횟수에서 차감하지 않는다."""
        return self.verdict in {Verdict.YES, Verdict.NO, Verdict.IRRELEVANT, Verdict.UNRELEASED}


class QuestionBank:
    def __init__(self, questions_doc: dict, answers_doc: dict):
        lex = questions_doc["lexicon"]
        self.stop_phrases = sorted((normalize(s) for s in lex.get("stop_phrases", [])), key=len, reverse=True)

        alias_pairs = [(normalize(a), canon) for canon, aliases in lex["aliases"].items() for a in aliases]
        alias_pairs.sort(key=lambda p: len(p[0]), reverse=True)
        self._alias_map = dict(alias_pairs)
        self._alias_re = re.compile("|".join(re.escape(a) for a, _ in alias_pairs))
        self.entity_names = set(lex["aliases"].keys())

        concept_pairs = [(normalize(w), c) for c, words in lex["concepts"].items() for w in words]
        concept_pairs.sort(key=lambda p: len(p[0]), reverse=True)
        self._concept_pairs = concept_pairs

        self.questions: dict[str, Question] = {}
        for raw in questions_doc["questions"]:
            m = raw["match"]
            q = Question(
                question_id=raw["question_id"],
                canonical=raw["canonical_question"],
                variations=list(raw.get("accepted_variations", [])),
                entity_sets=[frozenset(s) for s in m.get("entity_sets", [[]])],
                concept_groups=[set(g) for g in m.get("concepts", [])],
                optional=set(m.get("optional", [])),
                subject=m.get("subject"),
                not_subject=set(m.get("not_subject", [])),
                subject_strict=bool(m.get("subject_strict", False)),
            )
            self.questions[q.question_id] = q

        self.answers: dict[str, Answer] = {
            qid: Answer(
                answer=a.get("answer"),
                minimum_episode=int(a.get("minimum_episode", 1)),
                related_evidence=a.get("related_evidence"),
                response_text=a.get("response_text", ""),
                confirmed=bool(a.get("confirmed", False)),
            )
            for qid, a in answers_doc["answers"].items()
        }

        # 정확 일치 사전 (정규화된 표준 질문 + 변형 질문)
        self._exact: dict[str, str] = {}
        for q in self.questions.values():
            for text in [q.canonical, *q.variations]:
                self._exact.setdefault(self._canonical_form(text), q.question_id)

    # ---- 로딩 -------------------------------------------------------------
    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "QuestionBank":
        return cls(load_json(data_dir / "questions.json"), load_json(data_dir / "answers.json"))

    # ---- 파싱 -------------------------------------------------------------
    def _replace_aliases(self, norm: str) -> str:
        return self._alias_re.sub(lambda m: self._alias_map[m.group(0)], norm)

    def _canonical_form(self, text: str) -> str:
        norm = normalize(text)
        for s in self.stop_phrases:
            norm = norm.replace(s, "")
        return self._replace_aliases(norm)

    def parse(self, text: str) -> Parsed:
        norm = self._canonical_form(text)

        # 인물·연도와 문장 속 역할(주어/목적어/소유)
        entities: list[str] = []
        roles: dict[str, str] = {}
        names = sorted(self.entity_names, key=len, reverse=True)
        name_re = re.compile("|".join(re.escape(n) for n in names))
        for m in name_re.finditer(norm):
            name = m.group(0)
            if name not in entities:
                entities.append(name)
            tail = norm[m.end(): m.end() + 3]
            role = None
            if tail.startswith(COPULA_ENDINGS):
                role = None
            elif tail.startswith(OWNER_PARTICLES):
                role = "owner"
            elif tail.startswith(OBJECT_PARTICLES):
                role = "object"
            elif tail.startswith(SUBJECT_PARTICLES):
                role = "subject"
            if role and name not in roles:
                roles[name] = role

        # 개념 추출: 긴 표현부터 소거해 '허락없이'가 '허락'으로 오인되지 않게 한다.
        residual = name_re.sub("#", norm)
        concepts: set[str] = set()
        for word, concept in self._concept_pairs:
            if word and word in residual:
                concepts.add(concept)
                residual = residual.replace(word, "#")

        negated = bool(NEGATION_RE.search(residual))
        return Parsed(norm, residual, frozenset(entities), concepts, roles, entities, negated)

    # ---- 매칭 -------------------------------------------------------------
    def _subject_ok(self, q: Question, p: Parsed) -> bool:
        explicit_subjects = {e for e, r in p.roles.items() if r == "subject"}
        for e in q.not_subject:
            if p.roles.get(e) == "subject":
                return False
        if q.subject:
            role = p.roles.get(q.subject)
            if role == "object" or (role == "owner" and q.subject_strict):
                return False
            if role is None:
                if explicit_subjects - {q.subject}:
                    return False
                if p.order and p.order[0] != q.subject and len(p.order) > 1:
                    # 역할 표지가 없으면 먼저 나온 인물을 주어로 본다
                    others = [e for e in p.order if e in self.entity_names - NON_PERSON_ENTITIES]
                    if others and others[0] != q.subject:
                        return False
        return True

    def match_rules(self, text: str) -> tuple[Question | None, Parsed, str]:
        """(질문, 파싱결과, 사유). 사유: exact | rules | negated | ambiguous | none"""
        p = self.parse(text)
        qid = self._exact.get(p.normalized)
        if qid:
            return self.questions[qid], p, "exact"
        if p.negated:
            return None, p, "negated"
        if not p.concepts:
            return None, p, "none"

        scored: list[tuple[int, Question]] = []
        for q in self.questions.values():
            if p.entities not in q.entity_sets:
                continue
            if not all(g & p.concepts for g in q.concept_groups):
                continue
            if not p.concepts <= q.allowed_concepts:
                continue
            if not self._subject_ok(q, p):
                continue
            score = sum(1 for g in q.concept_groups if g & p.concepts) * 10 + len(p.concepts & q.allowed_concepts)
            scored.append((score, q))
        if not scored:
            return None, p, "none"
        scored.sort(key=lambda s: s[0], reverse=True)
        best_score, best = scored[0]
        rivals = [q for s, q in scored[1:] if s == best_score]
        if rivals:
            a0 = self.answers.get(best.question_id)
            for r in rivals:
                ar = self.answers.get(r.question_id)
                if not a0 or not ar or (a0.answer, a0.minimum_episode) != (ar.answer, ar.minimum_episode):
                    return None, p, "ambiguous"
        return best, p, "rules"

    # ---- 응답 -------------------------------------------------------------
    def answer_for(self, q: Question, current_episode: int, answer_unconfirmed: bool = False) -> AskResult:
        a = self.answers.get(q.question_id)
        if a is None or a.answer is None or (not a.confirmed and not answer_unconfirmed):
            return AskResult(Verdict.UNCONFIRMED, q.question_id)
        if current_episode < a.minimum_episode:
            return AskResult(Verdict.UNRELEASED, q.question_id)
        verdict = Verdict(a.answer)
        return AskResult(
            verdict,
            q.question_id,
            canonical=q.canonical,
            response_text=a.response_text,
            related_evidence=a.related_evidence,
        )

    def ask(
        self,
        text: str,
        current_episode: int,
        answer_unconfirmed: bool = False,
        ai_pick: Callable[[str, list[Question]], str | None] | None = None,
    ) -> AskResult:
        q, p, reason = self.match_rules(text)
        via = reason
        if q is None and reason in {"none", "ambiguous"} and ai_pick is not None:
            # AI 에게는 현재 답할 수 있는(공개·확정) 질문 문장만 보여 준다.
            pool = [
                cand for cand in self.questions.values()
                if (a := self.answers.get(cand.question_id)) and a.confirmed and a.answer
                and a.minimum_episode <= current_episode
            ]
            picked = ai_pick(text, pool) if pool else None
            if picked and picked in self.questions and any(c.question_id == picked for c in pool):
                q, via = self.questions[picked], "ai"
        if q is None:
            verdict = Verdict.NEGATIVE_FORM if reason == "negated" else Verdict.UNCLEAR
            return AskResult(verdict, normalized=p.normalized, via=via)
        result = self.answer_for(q, current_episode, answer_unconfirmed)
        result.normalized = p.normalized
        result.via = via
        return result

    # ---- 검증 -------------------------------------------------------------
    def validate(self, evidence_ids: set[str]) -> list[str]:
        problems: list[str] = []
        for qid, q in self.questions.items():
            if qid not in self.answers:
                problems.append(f"{qid}: answers.json 에 정답 항목이 없습니다")
                continue
            a = self.answers[qid]
            if a.answer not in {None, "YES", "NO", "IRRELEVANT"}:
                problems.append(f"{qid}: answer 값이 올바르지 않습니다 ({a.answer})")
            if a.confirmed and a.answer is None:
                problems.append(f"{qid}: confirmed 인데 answer 가 비어 있습니다")
            if a.related_evidence and a.related_evidence not in evidence_ids:
                problems.append(f"{qid}: 존재하지 않는 증거 {a.related_evidence}")
            for text in [q.canonical, *q.variations]:
                found, _, _ = self.match_rules(text)
                if found is None or found.question_id != qid:
                    got = found.question_id if found else "인식 실패"
                    problems.append(f"{qid}: 예문 '{text}' 이(가) {got} 으로 인식됩니다")
        for qid in self.answers:
            if qid not in self.questions:
                problems.append(f"{qid}: questions.json 에 없는 정답 항목")
        return problems
