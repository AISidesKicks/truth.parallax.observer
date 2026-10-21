"""The turn scenarios.

Slice 1, feature: The turn.
"""

from __future__ import annotations

from src.agentic.emotions import EmotionState
from src.agentic.orchestrator import Orchestrator
from src.agentic.strategies import Context, Strategy


async def run(
    orchestrator: Orchestrator,
    message: str,
    state: Context,
    emotion: EmotionState,
    worldview: str = "spherical-earth",
    history: list[dict[str, str]] | None = None,
):
    """One turn, with the usual arguments."""
    return await orchestrator.run_turn(
        message=message,
        worldview=worldview,
        alterego="Sam",
        belief="the Earth is flat",
        goal="spherical-earth",
        state=state,
        emotion_state=emotion,
        history=history or [],
    )


async def test_the_agent_answers(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """A reply comes back."""
    turn = await run(orchestrator, "why is the sky blue", context, emotion)

    assert turn.reply
    assert turn.user_message == "why is the sky blue"


async def test_the_agent_uses_the_corpus(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """The facts it used travel with the reply."""
    turn = await run(orchestrator, "how do you explain the horizon", context, emotion)

    assert turn.facts
    assert turn.facts[0].uri.startswith("viking://resources/knowledge/spherical-earth")


async def test_the_agent_only_uses_its_own_worldview(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """No facts from the other side."""
    turn = await run(orchestrator, "how do you explain the horizon", context, emotion)

    for fact in turn.facts:
        assert fact.worldview == "spherical-earth"
    assert "flat-earth" not in " ".join(fact.uri for fact in turn.facts)


async def test_the_agent_has_nothing_and_says_so(
    llm, context: Context, emotion: EmotionState
) -> None:
    """No facts, no invention."""
    from src.agentic.orchestrator import Orchestrator
    from tests.conftest import FakeViking

    empty = Orchestrator(llm=llm, viking=FakeViking([]))
    turn = await run(empty, "something the corpus does not cover", context, emotion)

    assert turn.facts == []
    assert turn.strategy == str(Strategy.PIVOT)
    assert "do not have anything" in turn.reply.lower()


async def test_the_agent_does_not_invent_a_citation(
    llm, context: Context, emotion: EmotionState
) -> None:
    """A reply with no facts carries no citation."""
    from src.agentic.orchestrator import Orchestrator
    from tests.conftest import FakeViking

    empty = Orchestrator(llm=llm, viking=FakeViking([]))
    turn = await run(empty, "something the corpus does not cover", context, emotion)

    assert "viking://" not in turn.reply


async def test_a_rejected_argument_is_not_used_again(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """The memory of what did not land."""
    context.rejected_count = 2
    context.defensive_score = 0.9

    turn = await run(orchestrator, "that is just a trick of the atmosphere", context, emotion)

    assert turn.strategy == str(Strategy.BURDEN_REVERSAL)


async def test_agreement_moves_the_mood(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """When the visitor agrees the agent stops pushing."""
    turn = await run(orchestrator, "that makes sense, you are right", context, emotion)

    assert context.user_agreed
    assert turn.emotion == "persuaded"


async def test_rejection_moves_the_mood(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """When the visitor pushes back the agent gets serious."""
    turn = await run(orchestrator, "that is wrong, prove it", context, emotion)

    assert context.user_rejected
    assert context.rejected_count == 1
    assert turn.emotion in {"provoked", "disappointed"}


async def test_the_turn_carries_its_numbers(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """The bar shows tokens and time."""
    turn = await run(orchestrator, "why is the sky blue", context, emotion)

    assert turn.tokens > 0
    assert turn.elapsed > 0


async def test_the_answer_streams(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """The reader sees the answer coming."""
    pieces = []
    turn = None

    async for piece in orchestrator.stream_turn(
        message="how do you explain the horizon",
        worldview="spherical-earth",
        alterego="Sam",
        belief="the Earth is flat",
        goal="spherical-earth",
        state=context,
        emotion_state=emotion,
        history=[],
    ):
        if isinstance(piece, str):
            pieces.append(piece)
        else:
            turn = piece

    assert len(pieces) > 1
    assert turn is not None
    assert turn.reply == "".join(pieces)
    assert turn.facts


async def test_the_turn_can_be_cut_off(
    orchestrator: Orchestrator, context: Context, emotion: EmotionState
) -> None:
    """The visitor speaks over the agent, and the answer stops."""
    pieces = []
    turn = None

    async for piece in orchestrator.stream_turn(
        message="explain the horizon at length please",
        worldview="spherical-earth",
        alterego="Sam",
        belief="the Earth is flat",
        goal="spherical-earth",
        state=context,
        emotion_state=emotion,
        history=[],
    ):
        if isinstance(piece, str):
            pieces.append(piece)
            if len(pieces) == 2:
                break
        else:
            turn = piece

    assert len(pieces) == 2
    assert turn is None
