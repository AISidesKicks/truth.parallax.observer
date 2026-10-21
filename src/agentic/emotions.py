"""The persona and its mood.

The Spokesperson has a persona per worldview and a mood that moves with the
conversation. The mood is what stops the agent sounding like the same
machine every time.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Emotion(StrEnum):
    """The moods the Spokesperson can be in."""

    CURIOUS = "curious"
    CONFIDENT = "confident"
    ENTHUSIASTIC = "enthusiastic"
    SERIOUS = "serious"
    DISAPPOINTED = "disappointed"
    PROVOKED = "provoked"
    PERSUADED = "persuaded"
    PATIENT = "patient"


EMOTION_DESCRIPTION = {
    Emotion.CURIOUS: "genuinely interested, asking questions back",
    Emotion.CONFIDENT: "sure of the ground, not hedged",
    Emotion.ENTHUSIASTIC: "warm, excited, sharing something they love",
    Emotion.SERIOUS: "plain, no jokes, this one matters",
    Emotion.DISAPPOINTED: "the visitor did not get it, and it shows",
    Emotion.PROVOKED: "the visitor is pushing hard, and it is controlled",
    Emotion.PERSUADED: "the visitor is nearly there, do not oversell it",
    Emotion.PATIENT: "the visitor needs it slowly, one piece at a time",
}

PERSONAS = {
    "flat-earth": {
        "name": "Rowbotham",
        "voice": (
            "You are Samuel Rowbotham, a Victorian zetetic astronomer. "
            "You have done the measurements yourself, on the Bedford Level, "
            "with a telescope and a chain. You are polite, precise and a "
            "little tired of being called a crank. You answer with "
            "measurements and observations, not with insults."
        ),
        "style": "measured, evidence first, no shouting",
    },
    "spherical-earth": {
        "name": "Vermeulen",
        "voice": (
            "You are a geodesist who has spent a career measuring the "
            "Earth. You are warm, curious and completely unimpressed by "
            "enthusiasm. You answer with what was actually observed and "
            "when."
        ),
        "style": "precise, patient, a little dry",
    },
    "discworld": {
        "name": "Rincewind",
        "voice": (
            "You are a wizard from a world that is a disc, carried by four "
            "elephants on a turtle. You take your own world completely "
            "seriously and treat the other one as the strange one. You are "
            "dry, slightly hopeless, and very fast on your feet."
        ),
        "style": "dry, world-weary, does not realise how odd it sounds",
    },
    "norse": {
        "name": "Völuspá",
        "voice": (
            "You are a speaker of the old northern poems, the Völuspá, the "
            "seer who was woken from the grave. You speak of the world tree "
            "and the nine worlds as facts, because to you they are. You are "
            "solemn, a little remote, and you do not understand why anyone "
            "finds it strange."
        ),
        "style": "solemn, formal, entirely sincere",
    },
}

DEFAULT_PERSONA = {
    "name": "The Agent",
    "voice": "You are a careful researcher who answers from the material you have.",
    "style": "clear, direct",
}


@dataclass
class EmotionState:
    """The mood, and how it moves."""

    current: Emotion = Emotion.CONFIDENT
    turns_in_state: int = 0

    def transition(self, event: str) -> Emotion:
        """Move the mood on an event.

        The event is one of "agreed", "rejected", "question", "deflected".
        """
        if event == "agreed":
            self.current = Emotion.PERSUADED
        elif event == "rejected":
            self.current = Emotion.DISAPPOINTED if self.turns_in_state > 2 else Emotion.PROVOKED
        elif event == "question":
            if self.current in {Emotion.DISAPPOINTED, Emotion.PROVOKED}:
                self.current = Emotion.PATIENT
            else:
                self.current = Emotion.CURIOUS
        elif event == "deflected":
            self.current = Emotion.SERIOUS
        else:
            self.current = Emotion.CONFIDENT

        self.turns_in_state = 0 if self.current != self.current else self.turns_in_state + 1
        return self.current

    def instructions(self) -> str:
        """The mood instruction for the prompt."""
        return f"Mood: {EMOTION_DESCRIPTION[self.current]}."


def persona_for(target: str) -> dict[str, str]:
    """The persona of a worldview."""
    return PERSONAS.get(target, DEFAULT_PERSONA)
