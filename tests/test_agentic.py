"""Strategy selection and context compression."""

from __future__ import annotations

from src.agentic.context import ContextManager, Preserved
from src.agentic.strategies import (
    Context,
    Strategy,
    detect_agreement,
    detect_rejection,
    select_strategy,
)

FACTS = [{"uri": "viking://x", "score": 0.8, "level": 1, "abstract": "a"}]


def test_no_facts_means_pivot() -> None:
    """Nothing in the corpus, so change the subject."""
    assert select_strategy(Context(), []) == Strategy.PIVOT


def test_agreement_means_confidence_exit() -> None:
    """The visitor agreed, stop pushing."""
    context = Context(user_agreed=True)
    assert select_strategy(context, FACTS) == Strategy.CONFIDENCE_EXIT


def test_a_defensive_visitor_gets_burden_reversal() -> None:
    """Turn the question back."""
    context = Context(rejected_count=2, defensive_score=0.9)
    assert select_strategy(context, FACTS) == Strategy.BURDEN_REVERSAL


def test_a_predictable_objection_gets_a_preemptive_strike() -> None:
    """Answer it before it is made."""
    context = Context(predictable_next=True)
    assert select_strategy(context, FACTS) == Strategy.PREEMPTIVE_STRIKE


def test_the_same_tactic_is_not_used_twice_in_a_row() -> None:
    """Variety, so it does not sound like a machine."""
    context = Context(last_strategy=str(Strategy.PREEMPTIVE_STRIKE))
    assert select_strategy(context, FACTS) == Strategy.GISH_GALLOP


def test_many_facts_mean_a_gish_gallop() -> None:
    """Stack them."""
    facts = FACTS * 3
    assert select_strategy(Context(), facts) == Strategy.GISH_GALLOP


def test_agreement_is_detected() -> None:
    """The phrase."""
    assert detect_agreement("that makes sense, you are right")
    assert detect_agreement("I agree with that")
    assert not detect_agreement("what is the weather like")


def test_rejection_is_detected() -> None:
    """The phrase."""
    assert detect_rejection("that is wrong, prove it")
    assert detect_rejection("nonsense")
    assert not detect_rejection("tell me more")


def test_a_short_conversation_is_not_compressed() -> None:
    """Nothing to do."""
    manager = ContextManager(recent_turns_kept=5)
    messages = [{"role": "user", "content": "hello"}]

    assert manager.compress(messages) == messages


def test_a_long_conversation_is_compressed() -> None:
    """The old turns go."""
    manager = ContextManager(recent_turns_kept=2)
    messages = [{"role": "user", "content": f"message {i}"} for i in range(10)]

    compressed = manager.compress(messages)

    assert len(compressed) == 3
    assert compressed[0]["role"] == "system"


def test_the_preserved_state_survives_compression() -> None:
    """The belief and the arguments must not be lost."""
    manager = ContextManager(recent_turns_kept=2)
    messages = [{"role": "user", "content": f"message {i}"} for i in range(10)]
    preserved = Preserved(
        belief="the Earth is flat",
        goal="spherical-earth",
        arguments_rejected=["water finds its level"],
    )

    compressed = manager.compress(messages, preserved=preserved)

    assert "the Earth is flat" in compressed[0]["content"]
    assert "water finds its level" in compressed[0]["content"]


def test_the_context_fits_the_window() -> None:
    """A long conversation gets squashed until it fits."""
    manager = ContextManager(max_tokens=500, alert_threshold=200, recent_turns_kept=2)
    messages = [{"role": "user", "content": "word " * 200} for _ in range(20)]

    fitted = manager.fit(messages)

    assert manager.count_tokens(fitted) <= manager.max_tokens
