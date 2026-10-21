"""The turn scenarios.

Slice 1, feature: The turn.
"""

from __future__ import annotations

from src.agentic.emotions import EmotionState
from src.agentic.orchestrator import Orchestrator
from src.agentic.strategies import Context, Strategy


def run(
    orchestrator: Orchestrator,
    message: str,
    state: Context,
    emotion: EmotionState,
    worldview: str = "spherical-earth",
    history: list[dict[str, str]] | None = None,
):
    """One turn, with the usual arguments."""
    return orchestrator.run_turn(
        message=message,
        worldview=worldview,
        alterego="Sam",
        belief="the Earth is flat",
        goal="spherical-earth",
        state=state,
        emotion_state=emotion,
        history=history or [],
    )


def test_the_agent_answers(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """A reply comes back."""
    turn = run(orchestrator, "why is the sky blue", context, emotion)

    assert turn.reply
    assert turn.user_message == "why is the sky blue"


def test_the_agent_uses_the_corpus(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """The facts it used travel with the reply."""
    turn = run(orchestrator, "how do you explain the horizon", context, emotion)

    assert turn.facts
    assert turn.facts[0].uri.startswith("viking://resources/knowledge/spherical-earth")


def test_the_agent_only_uses_its_own_worldview(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """No facts from the other side."""
    turn = run(orchestrator, "how do you explain the horizon", context, emotion)

    for fact in turn.facts:
        assert fact.worldview == "spherical-earth"
    assert "flat-earth" not in " ".join(fact.uri for fact in turn.facts)


def test_the_agent_has_nothing_and_says_so(
    llm, context: Context, emotion: EmotionState
) -> None:
    """No facts, no invention."""
    from src.agentic.orchestrator import Orchestrator
    from tests.conftest import FakeViking

    empty = Orchestrator(llm=llm, viking=FakeViking([]))
    turn = run(empty, "something the corpus does not cover", context, emotion)

    assert turn.facts == []
    assert turn.strategy == str(Strategy.PIVOT)
    assert "do not have anything" in turn.reply.lower()


def test_the_agent_does_not_invent_a_citation(
    llm, context: Context, emotion: EmotionState
) -> None:
    """A reply with no facts carries no citation."""
    from src.agentic.orchestrator import Orchestrator
    from tests.conftest import FakeViking

    empty = Orchestrator(llm=llm, viking=FakeViking([]))
    turn = run(empty, "something the corpus does not cover", context, emotion)

    assert "viking://" not in turn.reply


def test_a_rejected_argument_is_not_used_again(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """The memory of what did not land."""
    context.rejected_count = 2
    context.defensive_score = 0.9

    turn = run(orchestrator, "that is just a trick of the atmosphere", context, emotion)

    assert turn.strategy == str(Strategy.BURDEN_REVERSAL)


def test_agreement_moves_the_mood(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """When the visitor agrees the agent stops pushing."""
    turn = run(orchestrator, "that makes sense, you are right", context, emotion)

    assert context.user_agreed
    assert turn.emotion == "persuaded"


def test_rejection_moves_the_mood(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """When the visitor pushes back the agent gets serious."""
    turn = run(orchestrator, "that is wrong, prove it", context, emotion)

    assert context.user_rejected
    assert context.rejected_count == 1
    assert turn.emotion in {"provoked", "disappointed"}


def test_the_turn_carries_its_numbers(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """The bar shows tokens and time."""
    turn = run(orchestrator, "why is the sky blue", context, emotion)

    assert turn.tokens > 0
    assert turn.elapsed > 0
