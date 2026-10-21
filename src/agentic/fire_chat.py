"""Fire Chat, the three way debate.

Three personas, each with its own worldview and its own corpus, arguing in
turn while a moderator watches. The stages are fixed and visible, because the
point of the lab is to see the machinery:

    opening      every side states its case
    rebuttal     every side answers the one before it
    free debate  every side answers whatever it likes
    closing      every side says its last word
    judgment     the moderator scores

Each side only ever reads its own corpus. A flat earther arguing against a
geodesist must not be able to quote the geodesy material, and the transcript
has to show that it did not.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from src.agentic.emotions import persona_for
from src.agentic.moderator import Moderation, Moderator

logger = logging.getLogger(__name__)


class Stage(StrEnum):
    """The stages of the debate."""

    OPENING = "opening"
    REBUTTAL = "rebuttal"
    FREE_DEBATE = "free_debate"
    CLOSING = "closing"
    JUDGMENT = "judgment"


STAGE_ORDER = [
    Stage.OPENING,
    Stage.REBUTTAL,
    Stage.FREE_DEBATE,
    Stage.CLOSING,
    Stage.JUDGMENT,
]

STAGE_BRIEF = {
    Stage.OPENING: (
        "State your case. Two or three sentences, from your own material. "
        "Do not answer anybody yet, this is your opening."
    ),
    Stage.REBUTTAL: (
        "Answer the side that spoke before you. Name the point you are "
        "answering, then take it apart with your own material."
    ),
    Stage.FREE_DEBATE: (
        "Say what you want to say. Attack whatever you think is weakest, "
        "or make the case for your own position."
    ),
    Stage.CLOSING: (
        "Your last word. Two sentences on why you are right and the other "
        "side is not."
    ),
}


@dataclass
class Side:
    """One debater."""

    name: str
    worldview: str
    persona: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_worldview(cls, worldview: str, name: str | None = None) -> Side:
        """A side, with the persona of its worldview."""
        persona = persona_for(worldview)
        return cls(
            name=name or persona.get("name", worldview),
            worldview=worldview,
            persona=persona,
        )


@dataclass
class Speech:
    """One turn of one side."""

    speaker: str
    worldview: str
    text: str
    stage: str
    facts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """The speech as the interface sees it."""
        return {
            "speaker": self.speaker,
            "worldview": self.worldview,
            "text": self.text,
            "stage": self.stage,
            "facts": self.facts,
        }


@dataclass
class Debate:
    """The whole debate."""

    sides: list[Side]
    speeches: list[Speech] = field(default_factory=list)
    stage: Stage = Stage.OPENING
    moderation: Moderation | None = None

    @property
    def transcript(self) -> list[dict[str, str]]:
        """The debate as plain text, for the moderator."""
        return [
            {"speaker": speech.speaker, "text": speech.text} for speech in self.speeches
        ]

    def to_dict(self) -> dict[str, Any]:
        """The debate as the interface sees it."""
        return {
            "stage": str(self.stage),
            "sides": [
                {"name": side.name, "worldview": side.worldview} for side in self.sides
            ],
            "speeches": [speech.to_dict() for speech in self.speeches],
            "moderation": (
                self.moderation.model_dump() if self.moderation is not None else None
            ),
        }


class FireChat:
    """Runs the debate."""

    def __init__(
        self,
        llm: Any,
        viking: Any = None,
        top_k: int = 3,
    ) -> None:
        self.llm = llm
        self.viking = viking
        self.top_k = top_k
        self.moderator = Moderator(llm)

    # ------------------------------------------------------------------
    # The stages
    # ------------------------------------------------------------------

    async def run(self, topic: str, sides: list[Side]) -> Debate:
        """Run the whole debate, stage by stage."""
        debate = Debate(sides=sides)

        for stage in STAGE_ORDER:
            debate.stage = stage
            if stage == Stage.JUDGMENT:
                break

            for index, side in enumerate(sides):
                speech = await self.speak(debate, side, stage, topic, index)
                debate.speeches.append(speech)

        debate.stage = Stage.JUDGMENT
        debate.moderation = await self.moderator.score(
            debate.transcript,
            [side.name for side in sides],
        )
        return debate

    async def speak(
        self,
        debate: Debate,
        side: Side,
        stage: Stage,
        topic: str,
        index: int,
    ) -> Speech:
        """One side speaks."""
        material = await self._material(topic, side.worldview)
        previous = debate.speeches[-1].speaker if debate.speeches else "nobody"

        system = (
            f"{side.persona.get('voice', 'You are a debater.')}\n\n"
            f"Style: {side.persona.get('style', 'plain')}.\n"
            "You are in a debate with other people. You argue from your own "
            "material and you do not have anybody else's.\n\n"
            f"Here is your material:\n{material}\n\n"
            f"This is the {stage} round. {STAGE_BRIEF[stage]}\n\n"
            f"The last person to speak was {previous}."
        )

        try:
            reply = await self.llm.chat(
                [{"role": "user", "content": f"The topic is: {topic}"}],
                system=system,
                max_tokens=500,
            )
            text = reply.content
        except Exception as exc:
            logger.warning("%s could not speak: %s", side.name, exc)
            text = "I have nothing to add."

        return Speech(
            speaker=side.name,
            worldview=side.worldview,
            text=text,
            stage=str(stage),
            facts=self._last_facts,
        )

    async def _material(self, topic: str, worldview: str) -> str:
        """This side's material, and only this side's."""
        self._last_facts = []

        if self.viking is None:
            return "You have no material."

        try:
            hits = self.viking.search(
                query=topic,
                target=worldview,
                top_k=self.top_k,
                tier="knowledge",
            )
        except Exception as exc:
            logger.warning("the corpus did not answer: %s", exc)
            return "You have no material."

        if not hits:
            return "You have no material on this."

        self._last_facts = [hit.get("uri", "") for hit in hits]

        blocks: list[str] = []
        for index, hit in enumerate(hits):
            body = hit.get("abstract", "")
            if hit.get("level") == 2:
                try:
                    content = self.viking.get_content(hit.get("uri", ""))
                    if content:
                        body = content[:1200]
                except Exception:
                    pass
            blocks.append(f"[{index}] {body}\n    source: {hit.get('uri', '')}")

        return "\n\n".join(blocks)
