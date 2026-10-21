"""The chat client.

Talks to the llama.cpp router over the OpenAI compatible API. The models
answer in two passes, the thinking tokens land in reasoning_content and the
answer lands in content, so the token budget has to cover both and an empty
answer with a finished reason means the budget was too small.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class LLMReply:
    """One answer from the model."""

    content: str
    reasoning: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    elapsed: float = 0.0

    @property
    def tokens_per_second(self) -> float:
        """How fast the tokens came out."""
        if self.elapsed <= 0 or self.completion_tokens == 0:
            return 0.0
        return self.completion_tokens / self.elapsed


@dataclass
class LLMStats:
    """Running totals for the monitoring bar."""

    requests: int = 0
    failures: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_seconds: float = 0.0
    latencies: list[float] = field(default_factory=list)

    @property
    def average_latency(self) -> float:
        """Mean latency in seconds."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def p95_latency(self) -> float:
        """The slow tail, in seconds."""
        if not self.latencies:
            return 0.0
        ordered = sorted(self.latencies)
        index = int(len(ordered) * 0.95)
        return ordered[min(index, len(ordered) - 1)]


class LLMError(RuntimeError):
    """The model server could not be reached or gave nothing usable."""


class LLMClient:
    """A thin chat client with a thinking aware token budget."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 300.0,
        max_tokens: int = 1200,
        thinking_budget: int = 1500,
        temperature: float = 0.8,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.thinking_budget = thinking_budget
        self.temperature = temperature
        self.stats = LLMStats()

        self._client = httpx.Client(
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    def close(self) -> None:
        """Close the connection."""
        self._client.close()

    def available(self) -> bool:
        """Is the model server up."""
        try:
            response = self._client.get(f"{self.base_url}/models", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        retries: int = 2,
        json_mode: bool = False,
    ) -> LLMReply:
        """One chat completion.

        Args:
            messages: The conversation
            max_tokens: Answer budget, on top of the thinking budget
            temperature: Sampling temperature
            retries: How many times to try with a bigger budget
            json_mode: Ask for a JSON answer

        Raises:
            LLMError: The server gave nothing usable
        """
        budget = max_tokens or self.max_tokens
        best = ""

        for attempt in range(retries + 1):
            payload: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_tokens": budget + self.thinking_budget,
                "temperature": temperature if temperature is not None else self.temperature,
                "stream": False,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            started = time.time()
            try:
                response = self._client.post(f"{self.base_url}/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                self.stats.failures += 1
                logger.warning("chat failed: %s", exc)
                if attempt == retries:
                    raise LLMError(f"the model server did not answer: {exc}") from exc
                budget *= 2
                continue

            elapsed = time.time() - started
            choice = data["choices"][0]
            message = choice.get("message", {})
            content = (message.get("content") or "").strip()
            reasoning = (message.get("reasoning_content") or "").strip()

            usage = data.get("usage", {})
            self.stats.requests += 1
            self.stats.prompt_tokens += usage.get("prompt_tokens", 0)
            self.stats.completion_tokens += usage.get("completion_tokens", 0)
            self.stats.total_seconds += elapsed
            self.stats.latencies.append(elapsed)

            if len(content) > len(best):
                best = content

            if content:
                return LLMReply(
                    content=content,
                    reasoning=reasoning,
                    model=data.get("model", self.model),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    elapsed=elapsed,
                )

            budget *= 2

        raise LLMError(f"the model gave nothing usable after {retries + 1} tries")

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """A single prompt, no conversation."""
        reply = self.chat([{"role": "user", "content": prompt}], **kwargs)
        return reply.content
