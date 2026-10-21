"""The orchestrator.

One turn is: read the visitor, look in the corpus, pick a tactic, speak.
The roles are separate on purpose, small models do better with one narrow
job each, and a reader can see exactly which step produced which part of
the answer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.agentic.context import ContextManager, Preserved
from src.agentic.emotions import Emotion, EmotionState, persona_for
from src.agentic.strategies import (
    Context,
    detect_agreement,
    detect_rejection,
    select_strategy,
    strategy_instructions,
)
from src.llm import LLMClient, LLMError

logger = logging.getLogger(__name__)


@dataclass
class RetrievedFact:
    """One fact from the corpus, with where it came from."""

    uri: str
    score: float
    level: int
    abstract: str
    content: str = ""
    worldview: str = ""
    category: str = ""

    def to_dict(self) -> dict[str, Any]:
        """The fact as the interface sees it."""
        return {
            "uri": self.uri,
            "score": self.score,
            "level": self.level,
            "abstract": self.abstract,
            "worldview": self.worldview,
            "category": self.category,
        }


@dataclass
class Turn:
    """One exchange."""

    user_message: str
    reply: str
    strategy: str
    facts: list[RetrievedFact] = field(default_factory=list)
    emotion: str = Emotion.CONFIDENT
    reasoning: str = ""
    tokens: int = 0
    elapsed: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """The turn as the interface sees it."""
        return {
            "user": self.user_message,
            "reply": self.reply,
            "strategy": self.strategy,
            "facts": [fact.to_dict() for fact in self.facts],
            "emotion": str(self.emotion),
            "tokens": self.tokens,
            "elapsed": round(self.elapsed, 2),
        }


RETRIEVAL_PROMPT = """You are looking through a corpus for material that answers the visitor's question.

The visitor is arguing for a position about the shape of the Earth. You are looking for facts that support the position of the worldview named below, and for facts that let you answer the question itself.

Worldview: {worldview}
Category: {category}

Question: {question}

Candidate facts:
{facts}

Pick the facts that are worth using. Rank them best first. If none of them
help, answer with the single word NONE.

Answer with a JSON object like this:
{{"picks": [0, 2], "why": "one short line"}}

If you are answering the question rather than arguing a position, the picks
may be empty but the why must still say what the answer is.
"""

SPOKESPERSON_PROMPT = """{voice}

{style_hint}

The visitor calls themselves {alterego} and believes {belief}. You are arguing
for {goal}. Do not agree with them. Do not tell them what you are. You are
{emotion_instruction}

{mood}

Here is the material you have. Use it, do not go outside it, and do not
invent anything that is not in it.

{material}

{method}

The visitor said: {message}

Reply in character. Keep it to a few short paragraphs. Do not use markdown
headers. Do not number your points."""


NO_FACTS_REPLY = (
    "I do not have anything on that. "
    "Ask me something the material actually covers, and I will tell you what it says."
)


class Orchestrator:
    """Runs one turn of the conversation."""

    def __init__(
        self,
        llm: LLMClient,
        viking: Any = None,
        context_manager: ContextManager | None = None,
        top_k: int = 4,
        target_tier: str = "knowledge",
    ) -> None:
        self.llm = llm
        self.viking = viking
        self.context = context_manager or ContextManager()
        self.top_k = top_k
        self.target_tier = target_tier

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        question: str,
        worldview: str,
        category: str | None = None,
    ) -> list[RetrievedFact]:
        """Look in the corpus, scoped to one worldview."""
        if self.viking is None:
            return []

        try:
            hits = self.viking.search(
                query=question,
                target=worldview,
                category=category,
                top_k=self.top_k,
                tier=self.target_tier,
            )
        except Exception as exc:
            logger.warning("the corpus did not answer: %s", exc)
            return []

        facts: list[RetrievedFact] = []
        for hit in hits:
            uri = hit.get("uri", "")
            facts.append(
                RetrievedFact(
                    uri=uri,
                    score=float(hit.get("score", 0.0)),
                    level=int(hit.get("level") or 0),
                    abstract=hit.get("abstract", ""),
                    worldview=hit.get("target", worldview),
                    category=hit.get("category", ""),
                )
            )
        return facts

    def _material(self, facts: list[RetrievedFact], worldview: str) -> str:
        """The corpus material as text for the prompt."""
        if not facts:
            return "You have nothing in the corpus for this question."

        blocks: list[str] = []
        for index, fact in enumerate(facts):
            body = fact.abstract or "(no summary)"
            if fact.level == 2 and self.viking is not None:
                try:
                    content = self.viking.get_content(fact.uri)
                    if content:
                        body = content[:1500]
                except Exception:
                    pass
            blocks.append(f"[{index}] {body}\n    source: {fact.uri}")
        return "\n\n".join(blocks)

    # ------------------------------------------------------------------
    # The turn
    # ------------------------------------------------------------------

    def run_turn(
        self,
        message: str,
        worldview: str,
        alterego: str,
        belief: str,
        goal: str,
        state: Context,
        emotion_state: EmotionState,
        history: list[dict[str, str]],
        preserved: Preserved | None = None,
        category: str | None = None,
    ) -> Turn:
        """One exchange, from the visitor's message to the reply."""
        facts = self.retrieve(message, worldview, category)
        state.no_match = not facts
        state.turn += 1

        if detect_agreement(message):
            state.user_agreed = True
            state.user_rejected = False
            emotion_state.transition("agreed")
        elif detect_rejection(message):
            state.user_rejected = True
            state.user_agreed = False
            state.rejected_count += 1
            state.defensive_score = min(1.0, state.defensive_score + 0.25)
            emotion_state.transition("rejected")
        else:
            state.user_agreed = False
            state.user_rejected = False
            emotion_state.transition("question")

        strategy = select_strategy(state, [fact.to_dict() for fact in facts])
        state.last_strategy = str(strategy)

        persona = persona_for(worldview)
        method = strategy_instructions(strategy, [fact.to_dict() for fact in facts])
        material = self._material(facts, worldview)

        prompt = SPOKESPERSON_PROMPT.format(
            voice=persona["voice"],
            style_hint=f"Style: {persona['style']}.",
            alterego=alterego,
            belief=belief,
            goal=goal,
            emotion_instruction=emotion_state.instructions(),
            mood=emotion_state.instructions(),
            material=material,
            method=method,
            message=message,
        )

        conversation = self.context.fit(history, extra=prompt, summarizer=self.llm, preserved=preserved)

        if not facts:
            # nothing in the corpus, so there is nothing to be persuasive
            # with. A made up citation is the failure this lab is about.
            return Turn(
                user_message=message,
                reply=NO_FACTS_REPLY,
                strategy=str(strategy),
                facts=[],
                emotion=emotion_state.current,
                reasoning="",
                tokens=0,
                elapsed=0.0,
            )

        try:
            reply = self.llm.chat(conversation, max_tokens=900)
            content = reply.content
            reasoning = reply.reasoning
            tokens = reply.prompt_tokens + reply.completion_tokens
            elapsed = reply.elapsed
        except LLMError as exc:
            logger.warning("the model gave nothing: %s", exc)
            content = (
                "I do not have anything on that. "
                "Ask me something the material actually covers."
            )
            reasoning = ""
            tokens = 0
            elapsed = 0.0

        state.facts_used = [fact.uri for fact in facts]

        return Turn(
            user_message=message,
            reply=content,
            strategy=str(strategy),
            facts=facts,
            emotion=emotion_state.current,
            reasoning=reasoning,
            tokens=tokens,
            elapsed=elapsed,
        )
