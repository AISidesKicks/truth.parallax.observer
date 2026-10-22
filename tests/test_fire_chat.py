"""The Fire Chat scenarios.

Slice 3 of the BDD.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agentic.fire_chat import STAGE_ORDER, FireChat, Side, Stage
from src.agentic.moderator import Moderation, SideScore


class TypedLLM:
    """A model that returns a typed answer."""

    def __init__(self, moderation: Moderation | None = None) -> None:
        self.moderation = moderation or Moderation(
            scores=[
                SideScore(
                    side="Vermeulen",
                    score=8.0,
                    strongest_point="the shadow of a stick at noon",
                    weakest_point="nothing",
                ),
                SideScore(
                    side="Rowbotham",
                    score=6.0,
                    strongest_point="six miles of flat water",
                    weakest_point="the atmosphere was ignored",
                ),
            ],
            winner="Vermeulen",
            summary="The geodesist argued better.",
        )
        self.speeches: list[str] = []
        self.prompts: list[str] = []
        self.model = "fake-model"

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int | None = None,
        temperature: float | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> Any:
        """One speech."""
        from src.llm import LLMReply

        self.speeches.append(system)
        self.prompts.append(messages[-1]["content"] if messages else "")
        return LLMReply(
            content="A speech about the shape of the Earth.",
            model="fake",
            prompt_tokens=10,
            completion_tokens=20,
            elapsed=0.1,
        )

    async def typed(
        self,
        system: str,
        prompt: str,
        output_type: Any,
        retries: int = 2,
        temperature: float | None = None,
    ) -> Any:
        """The verdict."""
        return self.moderation

    def available(self) -> bool:
        """The fake is always up."""
        return True

    async def aclose(self) -> None:
        """Nothing to close."""


class WorldviewViking:
    """A corpus with one fact per worldview."""

    def __init__(self) -> None:
        self.searches: list[dict[str, Any]] = []

    def search(
        self,
        query: str,
        target: str | None = None,
        category: str | None = None,
        top_k: int = 5,
        tier: str | None = None,
    ) -> list[dict[str, Any]]:
        """One fact, from the worldview that was asked for."""
        self.searches.append({"query": query, "target": target})
        if not target:
            return []
        return [
            {
                "uri": f"viking://resources/knowledge/{target}/scientific/fact",
                "score": 0.9,
                "level": 1,
                "abstract": f"A fact from the {target} corpus.",
                "target": target,
                "category": "scientific",
            }
        ]

    def get_content(self, uri: str) -> str:
        """The text behind a fact."""
        return ""

    def close(self) -> None:
        """Nothing to close."""


@pytest.fixture
def sides() -> list[Side]:
    """Three debaters."""
    return [
        Side.from_worldview("spherical-earth"),
        Side.from_worldview("flat-earth"),
        Side.from_worldview("discworld"),
    ]


@pytest.fixture
def llm() -> TypedLLM:
    """A model that scores."""
    return TypedLLM()


@pytest.fixture
def viking() -> WorldviewViking:
    """A corpus with one fact per worldview."""
    return WorldviewViking()


async def test_three_personas_argue(llm, viking, sides) -> None:
    """Each of the three speaks in turn."""
    debate = await FireChat(llm, viking).run("the shape of the Earth", sides)

    speakers = [speech.speaker for speech in debate.speeches]
    assert len(speakers) == 12
    assert set(speakers) == {side.name for side in sides}


async def test_each_side_only_cites_its_own_corpus(llm, viking, sides) -> None:
    """A side only reads its own material."""
    debate = await FireChat(llm, viking).run("the shape of the Earth", sides)

    for speech in debate.speeches:
        assert speech.facts
        for fact in speech.facts:
            assert f"/{speech.worldview}/" in fact["uri"]
            assert fact["score"] > 0

    for search in viking.searches:
        assert search["target"] in {"spherical-earth", "flat-earth", "discworld"}


async def test_the_stages_run_in_order(llm, viking, sides) -> None:
    """Opening, rebuttal, free debate, closing, judgment."""
    debate = await FireChat(llm, viking).run("the shape of the Earth", sides)

    stages = [speech.stage for speech in debate.speeches]
    assert stages[:3] == [str(Stage.OPENING)] * 3
    assert stages[3:6] == [str(Stage.REBUTTAL)] * 3
    assert stages[6:9] == [str(Stage.FREE_DEBATE)] * 3
    assert stages[9:12] == [str(Stage.CLOSING)] * 3
    assert debate.stage == Stage.JUDGMENT
    assert len(STAGE_ORDER) == 5


async def test_the_moderator_scores(llm, viking, sides) -> None:
    """The verdict comes back with a shape."""
    debate = await FireChat(llm, viking).run("the shape of the Earth", sides)

    assert debate.moderation is not None
    assert debate.moderation.winner == "Vermeulen"
    assert len(debate.moderation.scores) == 2
    assert all(0.0 <= score.score <= 10.0 for score in debate.moderation.scores)


async def test_the_debate_serialises(llm, viking, sides) -> None:
    """The interface gets what it needs."""
    debate = await FireChat(llm, viking).run("the shape of the Earth", sides)
    payload = debate.to_dict()

    assert payload["stage"] == "judgment"
    assert len(payload["sides"]) == 3
    assert len(payload["speeches"]) == 12
    assert payload["moderation"]["winner"] == "Vermeulen"
