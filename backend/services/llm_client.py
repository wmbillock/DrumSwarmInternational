"""LLM client abstraction. Maps model tiers to API calls.

This module defines the interface and provides a real Anthropic implementation
plus a mock for testing. The runtime uses the client interface, never the
concrete implementation directly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from backend.models.agent_definition import ModelTier


# Model tier → actual model ID mapping
MODEL_TIER_MAP = {
    ModelTier.OPUS: "claude-opus-4-5-20251101",
    ModelTier.SONNET: "claude-sonnet-4-20250514",
    ModelTier.HAIKU: "claude-haiku-4-20250414",
}


@dataclass
class LLMMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ToolCall:
    """Represents an LLM requesting a tool invocation."""
    tool_name: str
    arguments: dict
    call_id: str = ""


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"  # "end_turn", "tool_use"

    @property
    def wants_tool_use(self) -> bool:
        return len(self.tool_calls) > 0


class LLMClient(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
    ) -> LLMResponse:
        """Send messages to the LLM and get a response."""
        ...


class MockLLMClient(LLMClient):
    """Test double for LLM calls. Records calls and returns scripted responses."""

    def __init__(self):
        self.calls: list[dict] = []
        self._responses: list[LLMResponse] = []
        self._default_response = LLMResponse(content="Mock response")

    def queue_response(self, response: LLMResponse) -> None:
        """Queue a response to be returned on the next chat() call."""
        self._responses.append(response)

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
    ) -> LLMResponse:
        self.calls.append({
            "messages": messages,
            "model_tier": model_tier,
            "model_id": MODEL_TIER_MAP[model_tier],
            "tools": tools,
        })
        if self._responses:
            return self._responses.pop(0)
        return self._default_response
