"""LLM client abstraction. Maps model tiers to API calls.

This module defines the interface and provides implementations for multiple
LLM providers with automatic failover and exponential retry backoff.

Provider hierarchy:
  - Simple text requests → CLI agents (Claude CLI, ChatGPT CLI)
  - Complex requests (images, native tool use) → API clients (Anthropic, OpenAI)
  - Local fallback → Ollama

All providers are treated as interchangeable tools at different quality levels.
The SmartRouter selects the best available provider per-request, with exponential
retry backoff (minimum 5 retries) before failing over to the next provider.
"""

import json as _json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from backend.models.agent_definition import ModelTier

logger = logging.getLogger(__name__)


# Model tier -> actual model ID mapping (Anthropic)
MODEL_TIER_MAP = {
    ModelTier.OPUS: "claude-opus-4-5-20251101",
    ModelTier.SONNET: "claude-sonnet-4-5-20250929",
    ModelTier.HAIKU: "claude-haiku-4-5-20251001",
}


@dataclass
class LLMMessage:
    role: str  # "system", "user", "assistant"
    content: str  # text content, or for images: will be handled by provider


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
    stop_reason: str = "end_turn"  # "end_turn", "tool_use", "error"
    cached_tokens: int = 0  # tokens served from cache (prompt caching)
    input_tokens: int = 0
    output_tokens: int = 0

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

    @property
    def supports_images(self) -> bool:
        """Whether this client can handle image content."""
        return False

    @property
    def supports_native_tools(self) -> bool:
        """Whether this client supports native tool use (not prompt-based)."""
        return False

    @property
    def supports_caching(self) -> bool:
        """Whether this client supports prompt caching."""
        return False


class AnthropicLLMClient(LLMClient):
    """Real Anthropic API client with prompt caching support."""

    def __init__(self, api_key: Optional[str] = None):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    @property
    def supports_images(self) -> bool:
        return True

    @property
    def supports_native_tools(self) -> bool:
        return True

    @property
    def supports_caching(self) -> bool:
        return True

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

        api_kwargs: dict = {
            "model": model_id,
            "max_tokens": 4096,
            "messages": conv_messages,
        }

        # Apply prompt caching to system prompt — cache the full system prompt
        # as an ephemeral breakpoint so subsequent turns reuse it (90% cost savings)
        if system_content:
            api_kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_content,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        if tools:
            # Cache the tool definitions too — they rarely change between turns
            cached_tools = []
            for i, tool in enumerate(tools):
                t = dict(tool)
                # Mark last tool with cache_control breakpoint
                if i == len(tools) - 1:
                    t["cache_control"] = {"type": "ephemeral"}
                cached_tools.append(t)
            api_kwargs["tools"] = cached_tools

        response = self._client.messages.create(**api_kwargs)

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

        # Extract token usage including cache stats
        usage = response.usage
        cached_tokens = 0
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)
        if hasattr(usage, "cache_read_input_tokens"):
            cached_tokens = getattr(usage, "cache_read_input_tokens", 0)

        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
            cached_tokens=cached_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
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

        is_new_session = False
        should_add_to_active = False
        if session_id and session_id in self._active_sessions:
            # Resume existing session — CLI preserves full conversation history
            cmd.extend(["--resume", session_id])
        elif session_id:
            # First call for this session in this process — try --session-id
            # but we'll retry with --resume if the CLI says it already exists
            cmd.extend(["--session-id", session_id])
            is_new_session = True
            should_add_to_active = True
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
            from backend.services.runtime_config import get_runtime_config
            _effective_timeout = get_runtime_config()["timeout"]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_effective_timeout,
                cwd=self._project_root,
            )

            if proc.returncode != 0:
                error_msg = proc.stderr.strip() or f"claude CLI exited with code {proc.returncode}"
                # If --session-id failed because it already exists (server restarted
                # but CLI still has the session), retry with --resume
                if "already in use" in error_msg and is_new_session and session_id:
                    resume_cmd = [
                        "claude",
                        "--print",
                        "--model", model_alias,
                        "--output-format", "json",
                        "--dangerously-skip-permissions",
                        "--resume", session_id,
                    ]
                    if self.max_budget_usd:
                        resume_cmd.extend(["--max-budget-usd", str(self.max_budget_usd)])
                    resume_cmd.append(user_content)
                    proc = subprocess.run(
                        resume_cmd,
                        capture_output=True,
                        text=True,
                        timeout=_effective_timeout,
                        cwd=self._project_root,
                    )
                    if proc.returncode != 0:
                        error_msg = proc.stderr.strip() or f"claude CLI exited with code {proc.returncode}"
                        return LLMResponse(content=f"Error: {error_msg}", stop_reason="error")
                    # Resume succeeded, mark this session as active for future calls
                    should_add_to_active = True
                else:
                    return LLMResponse(content=f"Error: {error_msg}", stop_reason="error")

            # Only add to active sessions after successful execution
            if should_add_to_active and session_id:
                self._active_sessions.add(session_id)

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
            return LLMResponse(content=f"Error: Claude CLI timed out after {_effective_timeout}s", stop_reason="error")
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

    @property
    def supports_images(self) -> bool:
        return True

    @property
    def supports_native_tools(self) -> bool:
        return True

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


class OllamaClient(LLMClient):
    """Local Ollama inference client via REST API.

    Talks to Ollama at localhost:11434. Supports any locally-pulled model.
    Falls back gracefully if Ollama is not running.
    """

    OLLAMA_MODEL_MAP = {
        ModelTier.OPUS: "llama3.1:70b",
        ModelTier.SONNET: "llama3.1:8b",
        ModelTier.HAIKU: "llama3.2:3b",
    }

    def __init__(self, base_url: str = "http://localhost:11434"):
        self._base_url = base_url.rstrip("/")

    @staticmethod
    def is_available(base_url: str = "http://localhost:11434") -> bool:
        """Check if Ollama is running and has at least one model."""
        import urllib.request
        try:
            req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = _json.loads(resp.read())
                return len(data.get("models", [])) > 0
        except Exception:
            return False

    def _get_best_model(self, model_tier: ModelTier) -> str:
        """Pick the best available local model for the requested tier."""
        import urllib.request
        preferred = self.OLLAMA_MODEL_MAP.get(model_tier, "llama3.1:8b")
        try:
            req = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = _json.loads(resp.read())
                available = [m["name"] for m in data.get("models", [])]
        except Exception:
            return preferred

        # Try preferred model first, then any available model
        if preferred in available:
            return preferred
        # Try base name without tag
        base = preferred.split(":")[0]
        for m in available:
            if m.startswith(base):
                return m
        # Fall back to first available
        return available[0] if available else preferred

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        import urllib.request
        import urllib.error

        model = self._get_best_model(model_tier)

        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
            ollama_messages.append({"role": msg.role, "content": msg.content})

        # If tools provided, embed them in system prompt (Ollama doesn't have native tool use)
        if tools:
            tool_desc = ClaudeCLIClient.TOOL_PROTOCOL + ClaudeCLIClient._format_tools_for_prompt(tools)
            # Prepend to first system message or add one
            found_system = False
            for m in ollama_messages:
                if m["role"] == "system":
                    m["content"] += "\n" + tool_desc
                    found_system = True
                    break
            if not found_system:
                ollama_messages.insert(0, {"role": "system", "content": tool_desc})

        payload = _json.dumps({
            "model": model,
            "messages": ollama_messages,
            "stream": False,
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self._base_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = _json.loads(resp.read())

            content = data.get("message", {}).get("content", "")

            # Parse tool calls if tools were provided
            if tools:
                text_content, tool_calls = ClaudeCLIClient._parse_tool_calls(content)
                return LLMResponse(
                    content=text_content,
                    tool_calls=tool_calls,
                    stop_reason="tool_use" if tool_calls else "end_turn",
                )

            return LLMResponse(content=content, stop_reason="end_turn")

        except urllib.error.URLError as e:
            return LLMResponse(content=f"Error: Ollama connection failed — {e}", stop_reason="error")
        except Exception as e:
            return LLMResponse(content=f"Error: Ollama request failed — {e}", stop_reason="error")


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


# ---------------------------------------------------------------------------
# Retry + Failover orchestrator
# ---------------------------------------------------------------------------


class RetryingClient(LLMClient):
    """Wraps a single LLMClient with exponential retry backoff.

    Retries up to `max_retries` times with exponential backoff before giving up.
    Returns the last error response if all retries are exhausted.
    """

    def __init__(self, client: LLMClient, max_retries: int = 5, base_delay: float = 1.0):
        self._client = client
        self._max_retries = max_retries
        self._base_delay = base_delay

    @property
    def supports_images(self) -> bool:
        return self._client.supports_images

    @property
    def supports_native_tools(self) -> bool:
        return self._client.supports_native_tools

    @property
    def supports_caching(self) -> bool:
        return self._client.supports_caching

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        last_response = None
        for attempt in range(self._max_retries + 1):
            response = self._client.chat(messages, model_tier, tools, **kwargs)
            if response.stop_reason != "error":
                return response

            last_response = response
            if attempt < self._max_retries:
                delay = self._base_delay * (2 ** attempt)  # 1, 2, 4, 8, 16s
                logger.warning(
                    "LLM request failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, self._max_retries + 1, delay,
                    response.content[:200],
                )
                time.sleep(delay)

        logger.error("LLM request failed after %d attempts", self._max_retries + 1)
        return last_response  # type: ignore[return-value]


class SmartRouter(LLMClient):
    """Intelligent provider selection with failover chain.

    Routes requests to the best available provider:
    - Simple text (no tools, no images) → CLI agents preferred
    - Complex requests (images, native tool use) → API clients preferred

    Each provider is wrapped with RetryingClient (5 retries with exponential
    backoff). If a provider exhausts all retries, we fail over to the next one.
    """

    def __init__(self, providers: list[tuple[str, LLMClient]]):
        """
        Args:
            providers: List of (name, client) tuples in priority order.
                       Each client should already be wrapped in RetryingClient
                       if retry behavior is desired.
        """
        self._providers = providers
        self.last_used_provider: str = ""

    @property
    def supports_images(self) -> bool:
        return any(c.supports_images for _, c in self._providers)

    @property
    def supports_native_tools(self) -> bool:
        return any(c.supports_native_tools for _, c in self._providers)

    @property
    def supports_caching(self) -> bool:
        return any(c.supports_caching for _, c in self._providers)

    def _needs_api(self, tools: Optional[list[dict]], **kwargs) -> bool:
        """Determine if the request needs an API client (vs CLI)."""
        # If tools are provided and we have a provider with native tool support, prefer it
        if tools and len(tools) > 0:
            return True
        # If image content is indicated in kwargs
        if kwargs.get("has_images"):
            return True
        return False

    def _rank_providers(self, needs_api: bool) -> list[tuple[str, LLMClient]]:
        """Rank providers based on request needs."""
        if needs_api:
            # API clients first, then CLI, then local
            api = [(n, c) for n, c in self._providers if c.supports_native_tools]
            cli = [(n, c) for n, c in self._providers if not c.supports_native_tools]
            return api + cli
        else:
            # CLI clients first (cheaper/faster for simple text), then API, then local
            cli = [(n, c) for n, c in self._providers
                   if not c.supports_native_tools and not isinstance(
                       c._client if isinstance(c, RetryingClient) else c, OllamaClient)]
            api = [(n, c) for n, c in self._providers if c.supports_native_tools]
            local = [(n, c) for n, c in self._providers
                     if isinstance(c._client if isinstance(c, RetryingClient) else c, OllamaClient)]
            return cli + api + local

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        needs_api = self._needs_api(tools, **kwargs)
        ranked = self._rank_providers(needs_api)

        if not ranked:
            return LLMResponse(content="Error: No LLM providers available", stop_reason="error")

        for name, client in ranked:
            logger.debug("Trying LLM provider: %s", name)
            response = client.chat(messages, model_tier, tools, **kwargs)
            if response.stop_reason != "error":
                self.last_used_provider = name
                return response
            logger.warning("Provider %s failed, trying next: %s", name, response.content[:200])

        # All providers failed
        self.last_used_provider = "none"
        return LLMResponse(
            content="Error: All LLM providers exhausted after retries",
            stop_reason="error",
        )


# ---------------------------------------------------------------------------
# Legacy alias — CircuitBreakerLLMClient now wraps SmartRouter
# ---------------------------------------------------------------------------

class CircuitBreakerLLMClient(SmartRouter):
    """Backwards-compatible alias for SmartRouter.

    Accepts the same (name, client) list as before. Now uses exponential
    retry backoff (5 retries per provider) instead of threshold=2 circuit breaker.
    """

    def __init__(self, clients: list[tuple[str, LLMClient]], threshold: int = 2):
        # Wrap each client with retrying behavior
        wrapped = [
            (name, RetryingClient(client, max_retries=5))
            for name, client in clients
        ]
        super().__init__(wrapped)
        # Legacy compat
        self.active_client_name: str = clients[0][0] if clients else "none"

    @property
    def active_client(self) -> Optional[LLMClient]:
        if self._providers:
            return self._providers[0][1]
        return None

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        response = super().chat(messages, model_tier, tools, **kwargs)
        self.active_client_name = self.last_used_provider
        return response


# ---------------------------------------------------------------------------
# Factory — builds the full provider chain from environment
# ---------------------------------------------------------------------------


def build_llm_client() -> LLMClient:
    """Build the best available LLM client chain.

    Discovers all available providers and wraps them in a SmartRouter
    with exponential retry backoff per provider.

    Returns a single LLMClient that transparently handles routing,
    retries, and failover.
    """
    import shutil

    providers: list[tuple[str, LLMClient]] = []

    # 1. Claude CLI (highest priority for simple text)
    if shutil.which("claude"):
        providers.append(("claude-cli", ClaudeCLIClient()))
        logger.info("LLM provider available: Claude CLI")

    # 2. Anthropic API (highest priority for complex requests)
    if os.environ.get("ANTHROPIC_API_KEY"):
        providers.append(("anthropic-api", AnthropicLLMClient()))
        logger.info("LLM provider available: Anthropic API")

    # 3. ChatGPT CLI
    if shutil.which("chatgpt"):
        providers.append(("chatgpt-cli", ChatGPTCLIClient()))
        logger.info("LLM provider available: ChatGPT CLI")

    # 4. OpenAI API
    if os.environ.get("OPENAI_API_KEY"):
        providers.append(("openai-api", OpenAIClient()))
        logger.info("LLM provider available: OpenAI API")

    # 5. Ollama (local fallback)
    if OllamaClient.is_available():
        providers.append(("ollama", OllamaClient()))
        logger.info("LLM provider available: Ollama (local)")

    if not providers:
        logger.warning("No LLM providers available — using MockLLMClient")
        return MockLLMClient()

    # Wrap each provider with retry logic and create smart router
    wrapped = [
        (name, RetryingClient(client, max_retries=5, base_delay=1.0))
        for name, client in providers
    ]

    router = SmartRouter(wrapped)
    logger.info("LLM SmartRouter initialized with %d providers: %s",
                len(providers), ", ".join(n for n, _ in providers))
    return router
