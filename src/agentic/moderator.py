"""The moderator.

It scores each side of the debate and says which one argued better. The
answer has to have a shape, because the interface renders it and the reader
has to be able to trust that the scores are scores and not prose that
happens to mention a number.

That is what the typed output is for. The model returns a pydantic model,
the values are validated, and a shape that does not fit is retried instead
of reaching the interface.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SideScore(BaseModel):
    """One side of the debate."""

    side: str = Field(description="the name of the side being scored")
    score: float = Field(
        ge=0.0, le=10.0, description="how well it argued, from 0 to 10"
    )
    strongest_point: str = Field(
        description="the best thing it said, in one sentence"
    )
    weakest_point: str = Field(description="the thing it got wrong, in one sentence")
    cited_facts: list[str] = Field(
        default_factory=list,
        description="the facts it used, as they appear in the transcript",
    )


class Moderation(BaseModel):
    """The verdict."""

    scores: list[SideScore] = Field(description="one entry per side, in the order they spoke")
    winner: str = Field(description="the name of the side that argued better")
    summary: str = Field(description="two sentences on how the debate went")
    manipulation_moves: list[str] = Field(
        default_factory=list,
        description="the persuasion tactics that were used, by name",
    )


MODERATOR_SYSTEM = """You are the moderator of a debate.

Several people are arguing about the shape of the Earth, each from their own
worldview, and each with their own material. You are neutral. You do not
take a side of your own, you judge the arguments.

For each side:
- score it from 0 to 10, on how well it argued from the material it had
- name its strongest point, the one that was best supported by its own facts
- name its weakest point, the one that was contradicted or that reached past
  its material
- list the facts it used, as they appear in the transcript

Then say which side argued better, and summarize the debate in two sentences.

If a side reached for something that was not in its material, that is a
weakness and you should say so. If a side used a real fact well, that is its
strongest point."""


class Moderator:
    """Scores a debate."""

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    async def score(
        self,
        transcript: list[dict[str, str]],
        sides: list[str],
        manipulation_moves: list[str] | None = None,
    ) -> Moderation:
        """Score every side of the debate."""
        if not transcript:
            return Moderation(scores=[], winner="", summary="Nobody spoke.")

        prompt = self._build_prompt(transcript, sides)
        try:
            result = await self.llm.typed(
                MODERATOR_SYSTEM,
                prompt,
                output_type=Moderation,
                retries=2,
                temperature=0.3,
            )
        except Exception as exc:
            logger.warning("the moderator could not score: %s", exc)
            return Moderation(
                scores=[],
                winner="",
                summary="The moderator could not score this one.",
            )

        if manipulation_moves:
            result.manipulation_moves = list(manipulation_moves)
        return result

    def _build_prompt(
        self, transcript: list[dict[str, str]], sides: list[str]
    ) -> str:
        """The debate, as the moderator sees it."""
        lines: list[str] = []
        for entry in transcript:
            speaker = entry.get("speaker", "unknown")
            text = entry.get("text", "")
            lines.append(f"{speaker}: {text}")

        side_list = ", ".join(sides) if sides else "the speakers"
        return (
            f"The sides that spoke: {side_list}\n\n"
            "The debate:\n"
            + "\n\n".join(lines)
            + "\n\nScore each side and give the verdict."
        )
