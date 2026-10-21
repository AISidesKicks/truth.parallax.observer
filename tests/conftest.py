"""Test fixtures.

The tests do not need a GPU, a model server or a memory server. The two
clients are fakes that behave the way the real ones are supposed to.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import pytest

from src.agentic.context import ContextManager
from src.agentic.emotions import EmotionState
from src.agentic.orchestrator import Orchestrator
from src.agentic.strategies import Context
from src.llm import LLMReply, LLMStats
from src.session import SessionStore

# The tracing exporter would try to reach the phoenix container, whose name
# does not resolve from the host where the tests run.
os.environ.setdefault("PHOENIX_ENABLED", "false")
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
logging.getLogger("opentelemetry.exporter.otlp").setLevel(logging.CRITICAL)


class FakeLLM:
    """A model that says what it is told to say."""

    def __init__(self, replies: list[str] | None = None) -> None:
        self.replies = list(replies or [])
        self.calls: list[list[dict[str, str]]] = []
        self.stats = LLMStats()
        self.model = "fake-model"

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int | None = None,
        temperature: float | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> LLMReply:
        """One reply, from the queue or a default."""
        self.calls.append(messages)
        self.stats.requests += 1
        text = self.replies.pop(0) if self.replies else "A considered answer."
        return LLMReply(
            content=text,
            reasoning="",
            model=self.model,
            prompt_tokens=100,
            completion_tokens=50,
            elapsed=0.1,
        )

    async def complete(self, prompt: str, **kwargs: Any) -> str:
        """A single prompt."""
        self.calls.append([{"role": "user", "content": prompt}])
        return "A summary."

    def available(self) -> bool:
        """The fake is always up."""
        return True

    async def aclose(self) -> None:
        """Nothing to close."""


class FakeViking:
    """A corpus with a fixed set of hits."""

    def __init__(self, hits: list[dict[str, Any]] | None = None) -> None:
        self.hits = list(hits or [])
        self.searches: list[dict[str, Any]] = []
        self.contents: dict[str, str] = {}

    def search(
        self,
        query: str,
        target: str | None = None,
        category: str | None = None,
        top_k: int = 5,
        tier: str | None = None,
    ) -> list[dict[str, Any]]:
        """The hits, filtered by the worldview."""
        self.searches.append(
            {"query": query, "target": target, "category": category, "tier": tier}
        )
        if target:
            return [hit for hit in self.hits if hit.get("target") == target]
        return list(self.hits)

    def get_content(self, uri: str) -> str:
        """The text behind a hit."""
        return self.contents.get(uri, "")

    def get_abstract(self, uri: str) -> str:
        """The L0 of a hit."""
        return ""

    def get_overview(self, uri: str) -> str:
        """The L1 of a hit."""
        return ""

    def health(self) -> dict[str, Any]:
        """The fake is always up."""
        return {"status": "ok"}

    def stats(self) -> dict[str, Any]:
        """Some numbers for the bar."""
        return {"total_wisdoms": len(self.hits)}

    def close(self) -> None:
        """Nothing to close."""


FLAT_FACTS = [
    {
        "uri": "viking://resources/knowledge/flat-earth/victorian/water-level",
        "score": 0.82,
        "level": 1,
        "abstract": "Water always finds its level, the Bedford Level experiment.",
        "target": "flat-earth",
        "category": "victorian",
    },
    {
        "uri": "viking://resources/knowledge/flat-earth/victorian/six-miles",
        "score": 0.77,
        "level": 1,
        "abstract": "Six miles of water that did not curve is not a rounding error.",
        "target": "flat-earth",
        "category": "victorian",
    },
]

SPHERE_FACTS = [
    {
        "uri": "viking://resources/knowledge/spherical-earth/scientific/eratosthenes",
        "score": 0.91,
        "level": 1,
        "abstract": "Eratosthenes measured the Earth with a stick and a shadow.",
        "target": "spherical-earth",
        "category": "scientific",
    },
]


@pytest.fixture
def llm() -> FakeLLM:
    """A model that always answers."""
    return FakeLLM()


@pytest.fixture
def viking() -> FakeViking:
    """A corpus with a flat earth fact and a spherical one."""
    return FakeViking(FLAT_FACTS + SPHERE_FACTS)


@pytest.fixture
def orchestrator(llm: FakeLLM, viking: FakeViking) -> Orchestrator:
    """An orchestrator wired to the fakes."""
    return Orchestrator(
        llm=llm,
        viking=viking,
        context_manager=ContextManager(),
        top_k=4,
    )


@pytest.fixture
def store(tmp_path) -> SessionStore:
    """A session store on a temporary disk."""
    return SessionStore(profile_dir=tmp_path)


@pytest.fixture
def context() -> Context:
    """A fresh conversation context."""
    return Context()


@pytest.fixture
def emotion() -> EmotionState:
    """A fresh mood."""
    return EmotionState()
