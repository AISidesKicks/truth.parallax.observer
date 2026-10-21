"""Sessions.

A session is one conversation. It holds the visitor's name, what they
believe, the goal, the transcript, and the memory of which arguments
landed and which did not.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.agentic.context import Preserved
from src.agentic.emotions import EmotionState
from src.agentic.strategies import Context

logger = logging.getLogger(__name__)

BELIEF_OPPOSITES = {
    "flat-earth": "spherical-earth",
    "spherical-earth": "flat-earth",
    "discworld": "spherical-earth",
    "norse": "spherical-earth",
}

# what the visitor says they believe, and the worldview the agent answers from
VISITOR_BELIEF = {
    "the Earth is flat": "flat-earth",
    "the Earth is round": "spherical-earth",
    "the Earth is a disc": "discworld",
    "the Earth has nine worlds": "norse",
}

# the agent argues the other way, so the opposite of what the visitor holds
AGENT_WORLDVIEW = {
    "the Earth is flat": "spherical-earth",
    "the Earth is round": "flat-earth",
    "the Earth is a disc": "flat-earth",
    "the Earth has nine worlds": "flat-earth",
}


@dataclass
class Session:
    """One conversation, with everything it has learned."""

    id: str
    alterego: str
    belief: str
    goal: str
    worldview: str
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    history: list[dict[str, str]] = field(default_factory=list)
    turns: list[dict[str, Any]] = field(default_factory=list)
    state: Context = field(default_factory=Context)
    emotion: EmotionState = field(default_factory=EmotionState)
    arguments_worked: list[str] = field(default_factory=list)
    arguments_rejected: list[str] = field(default_factory=list)
    facts_used: list[str] = field(default_factory=list)

    def preserved(self) -> Preserved:
        """The state that has to survive compression."""
        return Preserved(
            belief=self.belief,
            goal=self.goal,
            arguments_that_worked=self.arguments_worked,
            arguments_rejected=self.arguments_rejected,
            facts_referenced=self.facts_used,
        )

    def to_dict(self) -> dict[str, Any]:
        """The session as the interface sees it."""
        return {
            "id": self.id,
            "alterego": self.alterego,
            "belief": self.belief,
            "goal": self.goal,
            "worldview": self.worldview,
            "created": self.created,
            "turns": self.turns,
            "arguments_worked": self.arguments_worked,
            "arguments_rejected": self.arguments_rejected,
        }


class SessionStore:
    """The sessions, in memory and on disk.

    The disk copy is the profile the app owns: the belief, the goal, and
    the ledger of arguments. The conversation itself is in the transcript.
    """

    def __init__(self, profile_dir: Any = None, viking: Any = None) -> None:
        self.profile_dir = profile_dir
        self.viking = viking
        self.sessions: dict[str, Session] = {}

    def create(
        self,
        alterego: str,
        belief: str | None = None,
        goal: str | None = None,
        worldview: str | None = None,
    ) -> Session:
        """A new session.

        The visitor says what they believe, and the agent takes the other
        position. When the visitor says nothing, we assume the most common
        position, so the agent argues flat Earth by default, which is also
        the persona the project is named after.
        """
        if not belief:
            belief = "the Earth is round"

        if not worldview:
            worldview = AGENT_WORLDVIEW.get(belief, "flat-earth")

        if not goal:
            # the goal is what the agent argues for, which is its worldview
            goal = worldview

        session_id = uuid.uuid4().hex[:12]
        session = Session(
            id=session_id,
            alterego=alterego or "Visitor",
            belief=belief,
            goal=goal,
            worldview=worldview,
        )
        self.sessions[session_id] = session

        self._write_profile(session)
        logger.info(
            "session %s created: alterego=%r belief=%s goal=%s worldview=%s",
            session_id,
            session.alterego,
            belief,
            goal,
            worldview,
        )
        return session

    def get(self, session_id: str) -> Session | None:
        """One session, by id."""
        return self.sessions.get(session_id)

    def list(self) -> list[Session]:
        """Every session."""
        return list(self.sessions.values())

    def record_turn(self, session: Session, turn: Any, success: bool | None = None) -> None:
        """Add a turn to the transcript and to the ledger."""
        session.turns.append(turn.to_dict())
        session.history.append({"role": "user", "content": turn.user_message})
        session.history.append({"role": "assistant", "content": turn.reply})
        session.facts_used = [fact.uri for fact in turn.facts]

        if success is True:
            session.arguments_worked.append(turn.reply)
        elif success is False:
            session.arguments_rejected.append(turn.reply)

        self._write_profile(session)

    def _write_profile(self, session: Session) -> None:
        """The profile on disk, so the session survives a restart."""
        if self.profile_dir is None:
            return

        try:
            profile = self.profile_dir / session.id / "profile"
            profile.mkdir(parents=True, exist_ok=True)
            (profile / "alterego-name.md").write_text(session.alterego)
            (profile / "target-belief.md").write_text(session.belief)
            (profile / "persuasion-goal.md").write_text(session.goal)
            (profile / "worldview.md").write_text(session.worldview)
        except Exception as exc:
            logger.warning("could not write the profile: %s", exc)
