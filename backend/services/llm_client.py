"""LLM client abstraction. Maps model tiers to API calls.

This module defines the interface and provides a real Anthropic implementation
plus a mock for testing. The runtime uses the client interface, never the
concrete implementation directly.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from backend.models.agent_definition import ModelTier


# Model tier -> actual model ID mapping
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
        **kwargs,
    ) -> LLMResponse:
        """Send messages to the LLM and get a response."""
        ...


class AnthropicLLMClient(LLMClient):
    """Real Anthropic API client."""

    def __init__(self, api_key: Optional[str] = None):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        model_id = MODEL_TIER_MAP[model_tier]

        # Separate system message from conversation messages
        system_content = ""
        conv_messages = []
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                conv_messages.append({"role": msg.role, "content": msg.content})

        kwargs: dict = {
            "model": model_id,
            "max_tokens": 4096,
            "messages": conv_messages,
        }
        if system_content:
            kwargs["system"] = system_content
        if tools:
            kwargs["tools"] = tools

        response = self._client.messages.create(**kwargs)

        # Parse response
        content_text = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    tool_name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                    call_id=block.id,
                ))

        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
        )


class ClaudeCLIClient(LLMClient):
    """Runs agents via the Claude CLI (`claude --print`).

    Tools are embedded in the system prompt using a structured protocol.
    The agent runtime handles the tool execution loop — each chat() call
    is a single LLM turn that may request tool use via a JSON block in
    the response text.
    """

    MODEL_ALIAS = {
        ModelTier.OPUS: "opus",
        ModelTier.SONNET: "sonnet",
        ModelTier.HAIKU: "haiku",
    }

    TOOL_PROTOCOL = """
## Tool Use Protocol

You have access to tools. To call a tool, emit a JSON block fenced with <tool_call> tags:

<tool_call>
{"tool": "tool_name", "arguments": {"arg1": "value1"}}
</tool_call>

You may call ONE tool per response. After calling a tool, STOP and wait for the result.
Do NOT continue reasoning after a tool call — you will receive the result in the next message.

When you have finished all work and need no more tools, respond normally without any <tool_call> tags.

Available tools:
"""

    def __init__(self, max_budget_usd: Optional[float] = None):
        self.max_budget_usd = max_budget_usd
        self._project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._active_sessions: set[str] = set()  # session IDs that have been initialized

    @staticmethod
    def _format_tools_for_prompt(tools: list[dict]) -> str:
        """Format tool schemas as a readable prompt section."""
        import json as _json
        lines = []
        for t in tools:
            name = t.get("name", "unknown")
            desc = t.get("description", "")
            schema = t.get("input_schema", {})
            props = schema.get("properties", {})
            required = set(schema.get("required", []))
            params = []
            for pname, pdef in props.items():
                req = " (required)" if pname in required else ""
                ptype = pdef.get("type", "string")
                pdesc = pdef.get("description", "")
                params.append(f"    - {pname}: {ptype}{req} — {pdesc}")
            lines.append(f"### {name}\n{desc}")
            if params:
                lines.append("  Parameters:\n" + "\n".join(params))
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _parse_tool_calls(text: str) -> tuple[str, list[ToolCall]]:
        """Extract tool calls from <tool_call> tags in response text."""
        import json as _json
        import re

        tool_calls = []
        pattern = re.compile(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', re.DOTALL)
        matches = pattern.findall(text)
        for match in matches:
            try:
                data = _json.loads(match)
                tool_calls.append(ToolCall(
                    tool_name=data.get("tool", ""),
                    arguments=data.get("arguments", {}),
                    call_id=f"cli_{id(match)}",
                ))
            except (_json.JSONDecodeError, ValueError):
                continue

        # Content is everything outside the tool_call tags
        content = pattern.sub("", text).strip()
        return content, tool_calls

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        *,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        import subprocess
        import json as _json

        # Extract system prompt and last user message from messages
        system_prompt = ""
        user_content = ""
        for msg in messages:
            if msg.role == "system":
                system_prompt += msg.content + "\n"
            elif msg.role == "user":
                user_content = msg.content  # take last user message

        model_alias = self.MODEL_ALIAS.get(model_tier, "sonnet")

        cmd = [
            "claude",
            "--print",
            "--model", model_alias,
            "--output-format", "json",
            "--dangerously-skip-permissions",
        ]

        if session_id and session_id in self._active_sessions:
            # Resume existing session — CLI preserves full conversation history
            cmd.extend(["--resume", session_id])
        elif session_id:
            # First call for this session — set up system prompt and tools
            cmd.extend(["--session-id", session_id])
            self._active_sessions.add(session_id)
            if tools:
                system_prompt += "\n" + self.TOOL_PROTOCOL + self._format_tools_for_prompt(tools)
            if system_prompt.strip():
                cmd.extend(["--system-prompt", system_prompt.strip()])
        else:
            # No session — one-shot (legacy behavior)
            if tools:
                system_prompt += "\n" + self.TOOL_PROTOCOL + self._format_tools_for_prompt(tools)
            if system_prompt.strip():
                cmd.extend(["--system-prompt", system_prompt.strip()])

        if self.max_budget_usd:
            cmd.extend(["--max-budget-usd", str(self.max_budget_usd)])

        cmd.append(user_content)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self._project_root,
            )

            if proc.returncode != 0:
                error_msg = proc.stderr.strip() or f"claude CLI exited with code {proc.returncode}"
                return LLMResponse(content=f"Error: {error_msg}", stop_reason="error")

            # Parse JSON output from claude CLI
            raw_content = proc.stdout.strip()
            try:
                data = _json.loads(raw_content)
                content = data.get("result", data.get("content", raw_content))
                if isinstance(content, list):
                    content = "\n".join(
                        block.get("text", "") for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    ) or str(content)
                content = str(content)
            except (_json.JSONDecodeError, ValueError):
                content = raw_content

            # Parse tool calls from the response text
            text_content, tool_calls = self._parse_tool_calls(content)

            return LLMResponse(
                content=text_content,
                tool_calls=tool_calls,
                stop_reason="tool_use" if tool_calls else "end_turn",
            )

        except subprocess.TimeoutExpired:
            return LLMResponse(content="Error: Claude CLI timed out after 120s", stop_reason="error")
        except FileNotFoundError:
            return LLMResponse(content="Error: 'claude' CLI not found in PATH", stop_reason="error")


class OpenAIClient(LLMClient):
    """OpenAI API client using the openai SDK."""

    OPENAI_MODEL_MAP = {
        ModelTier.OPUS: "gpt-4o",
        ModelTier.SONNET: "gpt-4o-mini",
        ModelTier.HAIKU: "gpt-4o-mini",
    }

    def __init__(self, api_key: Optional[str] = None):
        import openai
        self._client = openai.OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        model_id = self.OPENAI_MODEL_MAP.get(model_tier, "gpt-4o-mini")

        # Convert messages
        oai_messages = []
        for msg in messages:
            if msg.role == "system":
                oai_messages.append({"role": "system", "content": msg.content})
            elif msg.role == "user":
                oai_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                oai_messages.append({"role": "assistant", "content": msg.content})

        call_kwargs: dict = {
            "model": model_id,
            "messages": oai_messages,
        }

        # Convert tool schemas to OpenAI function calling format
        if tools:
            oai_tools = []
            for t in tools:
                oai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", {}),
                    },
                })
            call_kwargs["tools"] = oai_tools

        response = self._client.chat.completions.create(**call_kwargs)
        choice = response.choices[0]

        content = choice.message.content or ""
        tool_calls = []
        if choice.message.tool_calls:
            import json as _json
            for tc in choice.message.tool_calls:
                tool_calls.append(ToolCall(
                    tool_name=tc.function.name,
                    arguments=_json.loads(tc.function.arguments) if tc.function.arguments else {},
                    call_id=tc.id,
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
        )


class ChatGPTCLIClient(LLMClient):
    """Runs agents via the ChatGPT CLI (if available)."""

    def __init__(self):
        pass

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        import subprocess
        import json as _json

        system_prompt = ""
        user_content = ""
        for msg in messages:
            if msg.role == "system":
                system_prompt += msg.content + "\n"
            elif msg.role == "user":
                user_content = msg.content

        cmd = ["chatgpt"]
        if system_prompt.strip():
            cmd.extend(["--system", system_prompt.strip()])
        cmd.append(user_content)

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if proc.returncode != 0:
                return LLMResponse(content=f"Error: {proc.stderr.strip()}", stop_reason="error")
            return LLMResponse(content=proc.stdout.strip(), stop_reason="end_turn")
        except subprocess.TimeoutExpired:
            return LLMResponse(content="Error: chatgpt CLI timed out", stop_reason="error")
        except FileNotFoundError:
            return LLMResponse(content="Error: 'chatgpt' CLI not found", stop_reason="error")


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
        **kwargs,
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


class CircuitBreakerLLMClient(LLMClient):
    """Wraps multiple LLM clients with automatic failover.

    Tracks consecutive failures per client. After `threshold` consecutive
    failures, trips the circuit breaker and switches to the next client.
    """

    def __init__(self, clients: list[tuple[str, LLMClient]], threshold: int = 2):
        self._clients = clients  # [(name, client), ...]
        self._threshold = threshold
        self._failures: dict[str, int] = {name: 0 for name, _ in clients}
        self._tripped: set[str] = set()
        self._active_index = 0
        self.active_client_name: str = clients[0][0] if clients else "none"

    @property
    def active_client(self) -> Optional[LLMClient]:
        for i in range(len(self._clients)):
            idx = (self._active_index + i) % len(self._clients)
            name, client = self._clients[idx]
            if name not in self._tripped:
                self._active_index = idx
                self.active_client_name = name
                return client
        return None

    def _record_failure(self, name: str) -> None:
        self._failures[name] = self._failures.get(name, 0) + 1
        if self._failures[name] >= self._threshold:
            self._tripped.add(name)
            # Advance to next client
            self._active_index = (self._active_index + 1) % len(self._clients)

    def _record_success(self, name: str) -> None:
        self._failures[name] = 0

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        client = self.active_client
        if client is None:
            return LLMResponse(
                content="Error: All LLM clients have tripped circuit breakers",
                stop_reason="error",
            )

        name = self.active_client_name
        response = client.chat(messages, model_tier, tools, **kwargs)

        if response.stop_reason == "error":
            self._record_failure(name)
            # If this client just tripped, try the next one immediately
            next_client = self.active_client
            if next_client is not None and next_client is not client:
                return next_client.chat(messages, model_tier, tools, **kwargs)
        else:
            self._record_success(name)

        return response
