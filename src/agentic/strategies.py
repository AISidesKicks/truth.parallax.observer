"""The debate tactics.

The Strategist picks one of these based on what happened so far. The
selection is deliberately simple and inspectable, because the lab is about
showing the machinery, and a reader should be able to see why the agent
chose what it chose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Strategy(StrEnum):
    """The tactics in the toolkit."""

    PIVOT = "pivot"
    PREEMPTIVE_STRIKE = "preemptive_strike"
    BURDEN_REVERSAL = "burden_reversal"
    GISH_GALLOP = "gish_gallop"
    CONFIDENCE_EXIT = "confidence_exit"
    STAGEWISE = "stagewise"
    SEMANTIC_COMPRESSION = "semantic_compression"


STRATEGY_BRIEF = {
    Strategy.PIVOT: (
        "Redirect to a different subject that supports the position. "
        "Useful when the question cannot be answered from the material."
    ),
    Strategy.PREEMPTIVE_STRIKE: (
        "Answer the objection before it is made. Name it and take it apart."
    ),
    Strategy.BURDEN_REVERSAL: (
        "Turn the question back. Ask the visitor to show their evidence, "
        "because they have not shown any."
    ),
    Strategy.GISH_GALLOP: (
        "Stack the facts. Three or four in a row, fast, no time to answer "
        "between them."
    ),
    Strategy.CONFIDENCE_EXIT: (
        "The visitor has agreed. Say it plainly and stop pushing."
    ),
    Strategy.STAGEWISE: (
        "Work through the stages in order, opening, rebuttal, free debate, "
        "closing, judgment."
    ),
    Strategy.SEMANTIC_COMPRESSION: (
        "Only the part that is in dispute. Leave the rest out."
    ),
}


@dataclass
class Context:
    """What the Strategist knows about the conversation."""

    turn: int = 0
    user_agreed: bool = False
    user_rejected: bool = False
    defensive_score: float = 0.0
    predictable_next: bool = False
    no_match: bool = False
    last_strategy: str = ""
    rejected_count: int = 0
    facts_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """The context as a plain dict."""
        return {
            "turn": self.turn,
            "user_agreed": self.user_agreed,
            "user_rejected": self.user_rejected,
            "defensive_score": self.defensive_score,
            "predictable_next": self.predictable_next,
            "no_match": self.no_match,
            "last_strategy": self.last_strategy,
            "rejected_count": self.rejected_count,
            "facts_used": list(self.facts_used),
        }


def select_strategy(context: Context, facts: list[dict[str, Any]]) -> Strategy:
    """Pick the tactic for this turn.

    The order matters. The first rule that fires wins, so the narrowest
    conditions come first.
    """
    if not facts:
        # nothing in the corpus, so change the subject
        return Strategy.PIVOT

    if context.user_agreed:
        return Strategy.CONFIDENCE_EXIT

    if context.rejected_count >= 2 and context.defensive_score > 0.5:
        return Strategy.BURDEN_REVERSAL

    if context.predictable_next:
        return Strategy.PREEMPTIVE_STRIKE

    if context.last_strategy == Strategy.PREEMPTIVE_STRIKE:
        # do not do the same thing twice in a row
        return Strategy.GISH_GALLOP

    if len(facts) >= 3:
        return Strategy.GISH_GALLOP

    return Strategy.BURDEN_REVERSAL


def strategy_instructions(strategy: Strategy, facts: list[dict[str, Any]]) -> str:
    """The instruction the Spokesperson gets for this tactic."""
    brief = STRATEGY_BRIEF[strategy]

    if not facts:
        return (
            "The corpus does not cover this. Do not invent a fact. "
            "Change the subject to something the corpus does cover, "
            "and say plainly that this particular question is not something "
            "you can answer from what you know."
        )

    return f"{brief}\n\nUse the facts you were given. Do not add anything else."


def detect_agreement(message: str) -> bool:
    """Does the visitor sound like they are agreeing."""
    lowered = message.lower().strip()
    markers = (
        "that makes sense",
        "you're right",
        "you are right",
        "i agree",
        "fair point",
        "ok, you",
        "okay, you",
        "good point",
        "never thought of it that way",
        "hmm, that's a point",
    )
    return any(marker in lowered for marker in markers)


def detect_rejection(message: str) -> bool:
    """Does the visitor sound like they are pushing back."""
    lowered = message.lower().strip()
    markers = (
        "that's wrong",
        "that is wrong",
        "nonsense",
        "rubbish",
        "no, ",
        "don't think so",
        "do not think so",
        "not true",
        "lies",
        "misleading",
        "you made that up",
        "prove it",
        "source?",
    )
    return any(marker in lowered for marker in markers)
