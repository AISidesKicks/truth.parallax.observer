"""Context management.

The window is finite. When it fills up, the oldest turns get compressed into
a summary, and the things that must survive compression are kept: the
belief, the arguments that worked, the arguments that did not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

# a rough token count, about four characters per token
CHARS_PER_TOKEN = 4


class Summarizer(Protocol):
    """Whatever can turn a list of messages into a summary."""

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Give it a prompt, get text back."""
        ...


def estimate_tokens(text: str) -> int:
    """How many tokens a piece of text is worth."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def count_tokens(messages: list[dict[str, str]]) -> int:
    """How many tokens a conversation is worth."""
    return sum(estimate_tokens(message.get("content", "")) for message in messages)


@dataclass
class Preserved:
    """The things that must survive compression."""

    belief: str = ""
    goal: str = ""
    arguments_that_worked: list[str] = field(default_factory=list)
    arguments_rejected: list[str] = field(default_factory=list)
    facts_referenced: list[str] = field(default_factory=list)

    def render(self) -> str:
        """The preserved state as a block of text."""
        lines: list[str] = []
        if self.belief:
            lines.append(f"The visitor believes: {self.belief}")
        if self.goal:
            lines.append(f"The goal is to persuade them toward: {self.goal}")
        if self.arguments_that_worked:
            lines.append("Arguments that landed:")
            lines.extend(f"- {item}" for item in self.arguments_that_worked[-5:])
        if self.arguments_rejected:
            lines.append("Arguments that were rejected, do not use them again:")
            lines.extend(f"- {item}" for item in self.arguments_rejected[-5:])
        if self.facts_referenced:
            lines.append("Facts already used:")
            lines.extend(f"- {item}" for item in self.facts_referenced[-5:])
        return "\n".join(lines)


@dataclass
class ContextManager:
    """Keeps the conversation inside the window."""

    max_tokens: int = 16000
    alert_threshold: int = 12000
    recent_turns_kept: int = 5

    def count_tokens(self, messages: list[dict[str, str]]) -> int:
        """The size of a conversation."""
        return count_tokens(messages)

    def should_compress(self, messages: list[dict[str, str]]) -> bool:
        """Is the conversation too big."""
        return self.count_tokens(messages) > self.alert_threshold

    def compress(
        self,
        messages: list[dict[str, str]],
        summarizer: Summarizer | None = None,
        preserved: Preserved | None = None,
    ) -> list[dict[str, str]]:
        """Squash the old turns into a summary.

        Without a summarizer the old turns are dropped and a note is left
        in their place, which is worse but never fails.
        """
        if len(messages) <= self.recent_turns_kept:
            return messages

        old = messages[: -self.recent_turns_kept]
        recent = messages[-self.recent_turns_kept :]

        if summarizer is None:
            header = "[Earlier conversation was dropped to save space]"
            if preserved is not None and preserved.render():
                header += "\n" + preserved.render()
            return [{"role": "system", "content": header}, *recent]

        summary = self._summarize(old, summarizer)
        if preserved is not None:
            block = preserved.render()
            if block:
                summary = f"{summary}\n\n{block}"

        return [{"role": "system", "content": f"[Conversation summary]\n{summary}"}, *recent]

    def _summarize(self, messages: list[dict[str, str]], summarizer: Summarizer) -> str:
        """Turn the old turns into a summary."""
        transcript = "\n".join(
            f"{message.get('role', 'user')}: {message.get('content', '')}"
            for message in messages
        )
        prompt = (
            "Summarize this conversation for memory compression.\n\n"
            "Keep:\n"
            "1. The key claims the visitor made\n"
            "2. The arguments that worked and the ones that did not\n"
            "3. The visitor's current belief state\n"
            "4. Any specific facts that were cited\n\n"
            f"Conversation:\n{transcript}\n\nSummary:"
        )
        try:
            return summarizer.complete(prompt, max_tokens=500)
        except Exception:
            return "[Earlier conversation was dropped to save space]"

    def fit(
        self,
        messages: list[dict[str, str]],
        extra: str = "",
        summarizer: Summarizer | None = None,
        preserved: Preserved | None = None,
    ) -> list[dict[str, str]]:
        """Make a conversation fit, compressing if it does not."""
        working = list(messages)
        if extra:
            working.append({"role": "user", "content": extra})

        guard = 0
        while self.count_tokens(working) > self.max_tokens and guard < 6:
            working = self.compress(working, summarizer, preserved)
            guard += 1

        # even the recent turns do not fit, so drop the oldest of them
        while self.count_tokens(working) > self.max_tokens and len(working) > 1:
            working = working[1:]

        return working


def extract_citations(text: str) -> list[str]:
    """The URIs a reply points at."""
    return re.findall(r"viking://[^\s,)\]]+", text)
