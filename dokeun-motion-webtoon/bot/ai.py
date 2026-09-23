"""선택 기능: AI 질문 해석 보조.

규칙 기반 해석이 실패했을 때만 호출된다. AI 에게는 '현재 답할 수 있는(공개·확정) 표준 질문 문장'
목록만 주고, 참가자 질문이 그중 어느 것과 같은 뜻인지 ID 하나만 고르게 한다.
정답(YES/NO), 미공개 질문, 최종 정답은 AI 에게 전달하지 않으므로 유출될 수 없다.
API 키가 없거나 호출이 실패하면 None 을 돌려주고, 게임은 규칙 기반으로만 계속 동작한다.
"""
from __future__ import annotations

import logging
import re
from typing import Callable

from .questions import Question

log = logging.getLogger(__name__)

SYSTEM = (
    "너는 한국어 YES/NO 추리 게임의 질문 분류기다. 참가자 질문이 아래 목록의 질문 중 하나와 "
    "'완전히 같은 뜻'(같은 인물, 같은 행동, 같은 주어·대상, 긍정형)일 때만 그 ID 를 출력한다. "
    "조금이라도 뜻이 다르거나, 부정형이거나, 여러 질문이 섞였거나, 확신이 없으면 NONE 을 출력한다. "
    "ID 또는 NONE 한 단어만 출력한다."
)


def make_ai_picker(api_key: str | None, model: str) -> Callable[[str, list[Question]], str | None] | None:
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError:
        log.warning("anthropic 패키지가 없어 AI 질문 해석을 끕니다 (pip install anthropic)")
        return None

    client = anthropic.Anthropic(api_key=api_key, max_retries=1, timeout=15.0)

    def pick(text: str, pool: list[Question]) -> str | None:
        listing = "\n".join(f"{q.question_id}: {q.canonical}" for q in pool)
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=SYSTEM,
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": f"[질문 목록]\n{listing}\n\n[참가자 질문]\n{text[:200]}"}],
            )
        except anthropic.APIError as exc:
            log.warning("AI 질문 해석 호출 실패: %s", type(exc).__name__)
            return None
        if response.stop_reason == "refusal":
            return None
        out = "".join(b.text for b in response.content if b.type == "text").strip()
        m = re.search(r"Q-[A-Z0-9-]+", out)
        ids = {q.question_id for q in pool}
        return m.group(0) if m and m.group(0) in ids else None

    return pick
