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
    """Runs agents via the Claude CLI (`claude --print`) with MCP tools.

    Each chat() call spawns a `claude -p` subprocess with the system prompt,
    user message, and an MCP config pointing to our DCI tool server filtered
    by the agent's role. The CLI handles tool calls internally via MCP.
    """

    MODEL_ALIAS = {
        ModelTier.OPUS: "opus",
        ModelTier.SONNET: "sonnet",
        ModelTier.HAIKU: "haiku",
    }

    def __init__(self, max_budget_usd: Optional[float] = None):
        self.max_budget_usd = max_budget_usd
        self._project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _make_mcp_config(self, role: str, corps_id: str, session_id: str = "") -> str:
        """Generate a temp MCP config JSON file for this role and return its path."""
        import json as _json
        import tempfile

        venv_python = os.path.join(self._project_root, ".venv", "bin", "python")
        if not os.path.exists(venv_python):
            venv_python = "python"

        config = {
            "mcpServers": {
                "dci": {
                    "command": venv_python,
                    "args": [
                        "-m", "backend.mcp_server",
                        "--role", role,
                        "--corps-id", corps_id,
                        "--session-id", session_id,
                    ],
                    "cwd": self._project_root,
                }
            }
        }

        fd, path = tempfile.mkstemp(suffix=".json", prefix="dci-mcp-")
        with os.fdopen(fd, "w") as f:
            _json.dump(config, f)
        return path

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        role: str = "",
        corps_id: str = "",
        session_id: str = "",
    ) -> LLMResponse:
        import subprocess
        import json as _json

        # Extract system prompt and user content
        system_prompt = ""
        user_content = ""
        for msg in messages:
            if msg.role == "system":
                system_prompt += msg.content + "\n"
            elif msg.role == "user":
                user_content = msg.content  # take last user message as the prompt

        model_alias = self.MODEL_ALIAS.get(model_tier, "sonnet")

        cmd = [
            "claude",
            "--print",
            "--model", model_alias,
            "--output-format", "json",
            "--dangerously-skip-permissions",
        ]
        if system_prompt.strip():
            cmd.extend(["--system-prompt", system_prompt.strip()])
        if self.max_budget_usd:
            cmd.extend(["--max-budget-usd", str(self.max_budget_usd)])

        # Generate MCP config if we have role context
        mcp_config_path = None
        if role and corps_id:
            mcp_config_path = self._make_mcp_config(role, corps_id, session_id)
            cmd.extend(["--mcp-config", mcp_config_path])

        cmd.append(user_content)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=self._project_root,
            )

            if proc.returncode != 0:
                error_msg = proc.stderr.strip() or f"claude CLI exited with code {proc.returncode}"
                return LLMResponse(content=f"Error: {error_msg}", stop_reason="error")

            # Parse JSON output
            try:
                data = _json.loads(proc.stdout)
                content = data.get("result", data.get("content", proc.stdout))
                if isinstance(content, list):
                    content = "\n".join(
                        block.get("text", "") for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    ) or str(content)
                return LLMResponse(content=str(content), stop_reason="end_turn")
            except (_json.JSONDecodeError, ValueError):
                return LLMResponse(content=proc.stdout.strip(), stop_reason="end_turn")

        except subprocess.TimeoutExpired:
            return LLMResponse(content="Error: Claude CLI timed out after 300s", stop_reason="error")
        except FileNotFoundError:
            return LLMResponse(content="Error: 'claude' CLI not found in PATH", stop_reason="error")
        finally:
            if mcp_config_path and os.path.exists(mcp_config_path):
                os.unlink(mcp_config_path)


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
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
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
