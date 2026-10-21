"""The model layer.

PydanticAI on top of the llama.cpp router. The router speaks the OpenAI
compatible API, so it is just a base_url.

Two shapes are offered:

    agent(system, output_type)   a typed agent, for the parts of the debate
                                 that need a validated answer
    chat(messages)               plain text, for the parts that are prose

The models are reasoning models, so the answer arrives in two parts: the
thinking tokens land in reasoning_content and the answer lands in content.
PydanticAI handles the split, and the thinking is kept out of the reply.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, TypeVar

import httpx2
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

OutputT = TypeVar("OutputT", bound=BaseModel)


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


def to_message_history(
    history: list[dict[str, str]],
) -> list[ModelMessage]:
    """Turn the stored transcript into PydanticAI messages."""
    messages: list[ModelMessage] = []
    for entry in history:
        role = entry.get("role", "user")
        content = entry.get("content", "")
        if role == "assistant":
            messages.append(ModelResponse(parts=[]))
            messages[-1].parts.append(_text_part(content))
        else:
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
    return messages


def _text_part(content: str) -> Any:
    """A text part, imported lazily to keep the module import cheap."""
    from pydantic_ai.messages import TextPart

    return TextPart(content=content)


class LLMClient:
    """The model server, wrapped."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 300.0,
        max_tokens: int = 1200,
        temperature: float = 0.8,
        api_key: str = "parallax-local",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.stats = LLMStats()

        self._provider = OpenAIProvider(
            base_url=self.base_url,
            api_key=api_key,
            http_client=httpx2.AsyncClient(timeout=timeout),
        )
        self._model = OpenAIChatModel(
            model,
            provider=self._provider,
            settings={"max_tokens": max_tokens},
        )

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    def agent(
        self,
        system: str,
        output_type: Any = str,
        retries: int = 2,
        temperature: float | None = None,
    ) -> Agent:
        """A typed agent.

        `output_type` is a pydantic model when the answer has to have a
        shape, and the default string when it is prose.
        """
        settings: dict[str, Any] = {
            "temperature": temperature if temperature is not None else self.temperature
        }
        return Agent(
            self._model,
            system_prompt=system,
            output_type=output_type,
            retries=retries,
            model_settings=settings,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int | None = None,
        temperature: float | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> LLMReply:
        """One prose answer.

        Args:
            messages: The conversation, the last entry is the new question
            system: The system prompt
            max_tokens: Answer budget
            temperature: Sampling temperature
            history: Earlier turns, if the caller keeps them separately
        """
        import time

        prompt = messages[-1]["content"] if messages else ""
        agent = self.agent(system or "You are a helpful assistant.", temperature=temperature)

        started = time.time()
        try:
            result = await agent.run(
                prompt,
                message_history=to_message_history(history or []),
            )
        except Exception as exc:
            self.stats.failures += 1
            raise LLMError(f"the model did not answer: {exc}") from exc

        elapsed = time.time() - started
        usage = result.usage
        self.stats.requests += 1
        self.stats.prompt_tokens += usage.input_tokens
        self.stats.completion_tokens += usage.output_tokens
        self.stats.total_seconds += elapsed
        self.stats.latencies.append(elapsed)

        thinking = ""
        for message in result.new_messages():
            for part in getattr(message, "parts", []):
                if type(part).__name__ == "ThinkingPart":
                    thinking += getattr(part, "content", "") or ""

        return LLMReply(
            content=str(result.output),
            reasoning=thinking,
            model=self.model,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            elapsed=elapsed,
        )

    async def typed(
        self,
        system: str,
        prompt: str,
        output_type: type[OutputT],
        retries: int = 2,
        temperature: float | None = None,
    ) -> OutputT:
        """One answer with a guaranteed shape."""
        agent = self.agent(system, output_type=output_type, retries=retries, temperature=temperature)
        try:
            result = await agent.run(prompt)
        except Exception as exc:
            self.stats.failures += 1
            raise LLMError(f"the model did not answer: {exc}") from exc

        usage = result.usage
        self.stats.requests += 1
        self.stats.prompt_tokens += usage.input_tokens
        self.stats.completion_tokens += usage.output_tokens
        return result.output

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def available(self) -> bool:
        """Is the model server up."""
        import httpx2

        try:
            response = httpx2.get(f"{self.base_url}/models", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        """Close the connection."""
        client = getattr(self._provider, "client", None)
        if client is not None:
            await client.close()
