"""The agentic layer.

Orchestrator, strategist, spokesperson, moderator. The roles are separate so
a small model only ever has one narrow job.
"""

from src.agentic.context import ContextManager, Preserved
from src.agentic.emotions import Emotion, EmotionState, persona_for
from src.agentic.orchestrator import Orchestrator, RetrievedFact, Turn
from src.agentic.strategies import Context, Strategy

__all__ = [
    "Context",
    "ContextManager",
    "Emotion",
    "EmotionState",
    "Orchestrator",
    "Preserved",
    "RetrievedFact",
    "Strategy",
    "Turn",
    "persona_for",
]
