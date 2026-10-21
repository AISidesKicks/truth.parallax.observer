"""The async summarizer.

The context manager needs something that can turn a list of messages into a
summary. The model client is async, so this is the small bridge between the
two.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AsyncSummarizer:
    """Summarises a conversation with the model."""

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    async def complete(self, prompt: str, **kwargs: Any) -> str:
        """One summary."""
        reply = await self.llm.chat(
            [{"role": "user", "content": prompt}],
            system="You summarise conversations. Be short and factual.",
            max_tokens=kwargs.get("max_tokens", 500),
            temperature=0.3,
        )
        return reply.content
