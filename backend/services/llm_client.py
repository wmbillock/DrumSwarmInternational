"""LLM client abstraction. Maps model tiers to API calls.

This module defines the interface and provides implementations for multiple
LLM providers with automatic failover and exponential retry backoff.

Provider hierarchy (default, overridable via DSI_LLM_PRIORITY):
  - Simple text requests → CLI agents (Claude CLI, ChatGPT CLI)
  - Complex requests (images, native tool use) → API clients (Anthropic, OpenAI)
  - Local fallback → Ollama

All providers are treated as interchangeable tools at different quality levels.
The SmartRouter selects the best available provider per-request, with exponential
retry backoff (minimum 5 retries) before failing over to the next provider.

Environment variables:
  DSI_LLM_PRIORITY: Comma-separated provider order (e.g. "ollama,anthropic-api")
  DSI_OLLAMA_MODEL: Override Ollama model for all tiers
  DSI_OLLAMA_URL:   Ollama base URL (default: http://localhost:11434)
  DSI_OLLAMA_NUM_CTX: Ollama context window size (default: 8192)
  DSI_OLLAMA_TIMEOUT: Ollama request timeout in seconds (default: 300)
  DSI_NO_CLI_PROVIDERS: Skip CLI providers (Claude CLI, ChatGPT CLI, etc.)
"""

import json as _json
import logging
import os
import re
import time
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from datetime import datetime, timezone

from backend.models.agent_definition import ModelTier

logger = logging.getLogger(__name__)


# Model tier -> actual model ID mapping (Anthropic)
MODEL_TIER_MAP = {
    ModelTier.OPUS: "claude-opus-4-6",
    ModelTier.SONNET: "claude-sonnet-4-6",
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
class BatchRequest:
    request_id: str
    workload: str
    created_at: float
    api_kwargs: dict


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"  # "end_turn", "tool_use", "error"
    cached_tokens: int = 0  # tokens served from cache (prompt caching)
    input_tokens: int = 0
    output_tokens: int = 0
    request_id: str = ""
    batch_id: str = ""

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
        """Send messages to the LLM and get a response.

        Kwargs:
            model_override: Optional model ID string. When provided, use this
                specific model instead of the tier-based mapping. Allows
                ModelSpec-driven selection to bypass the coarse tier system.
        """
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

    def cleanup_session(self, session_id: str) -> None:
        """Clean up a CLI session after agent work completes. No-op for API clients."""
        pass

    def submit_batch(self) -> Optional[str]:
        """Submit any queued batch requests (if supported)."""
        return None

    def get_batch_status(self) -> dict:
        """Return batch queue/status metrics (if supported)."""
        return {}


class AnthropicLLMClient(LLMClient):
    """Real Anthropic API client with prompt caching support."""

    def __init__(self, api_key: Optional[str] = None):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_SDK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
        self._batch_queue: list[BatchRequest] = []
        self._batch_results: dict[str, LLMResponse] = {}
        self._batch_jobs: dict[str, dict] = {}
        self._batch_lock = threading.Lock()
        self._batch_window_start: Optional[float] = None
        self._batch_threshold_count = int(os.environ.get("ANTHROPIC_BATCH_COUNT", "50"))
        self._batch_threshold_seconds = int(os.environ.get("ANTHROPIC_BATCH_WINDOW_SECONDS", "300"))
        self._batch_metrics = {
            "queued": 0,
            "submitted": 0,
            "completed": 0,
            "errors": 0,
            "fallback_sync": 0,
        }

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
        model_override = kwargs.pop("model_override", None)
        batchable = bool(kwargs.pop("batchable", False))
        allow_deferred = bool(kwargs.pop("allow_deferred", False))
        workload = str(kwargs.pop("workload", "default"))
        submit_batch = bool(kwargs.pop("submit_batch", False))

        if batchable:
            return self._chat_batchable(
                messages=messages,
                model_tier=model_tier,
                tools=tools,
                workload=workload,
                allow_deferred=allow_deferred,
                submit_batch=submit_batch,
            )

        return self._chat_sync(messages, model_tier, tools, model_override=model_override)

    def submit_batch(self) -> Optional[str]:
        return self._submit_batch(force=True)

    def get_batch_status(self) -> dict:
        with self._batch_lock:
            return {
                "queue_size": len(self._batch_queue),
                "jobs": list(self._batch_jobs.values()),
                "metrics": dict(self._batch_metrics),
                "thresholds": {
                    "count": self._batch_threshold_count,
                    "window_seconds": self._batch_threshold_seconds,
                },
            }

    def _chat_sync(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        model_override: Optional[str] = None,
    ) -> LLMResponse:
        model_id = model_override or MODEL_TIER_MAP[model_tier]
        api_kwargs = self._build_api_kwargs(messages, model_id, tools)
        response = self._client.messages.create(**api_kwargs)
        return self._parse_response(response)

    def _chat_batchable(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]],
        workload: str,
        allow_deferred: bool,
        submit_batch: bool,
    ) -> LLMResponse:
        model_id = MODEL_TIER_MAP[model_tier]
        api_kwargs = self._build_api_kwargs(messages, model_id, tools)
        request_id = str(uuid.uuid4())

        with self._batch_lock:
            self._batch_queue.append(BatchRequest(
                request_id=request_id,
                workload=workload,
                created_at=time.time(),
                api_kwargs=api_kwargs,
            ))
            self._batch_metrics["queued"] += 1
            if self._batch_window_start is None:
                self._batch_window_start = time.time()

        batch_id = self._submit_batch(force=submit_batch)

        if allow_deferred:
            return LLMResponse(
                content="",
                stop_reason="queued",
                request_id=request_id,
                batch_id=batch_id or "",
            )

        if request_id in self._batch_results:
            return self._batch_results.pop(request_id)

        self._batch_metrics["fallback_sync"] += 1
        response = self._chat_sync(messages, model_tier, tools)
        response.request_id = request_id
        response.batch_id = batch_id or ""
        return response

    def _submit_batch(self, force: bool = False) -> Optional[str]:
        with self._batch_lock:
            if not self._batch_queue:
                return None
            if not force:
                queue_age = 0
                if self._batch_window_start:
                    queue_age = time.time() - self._batch_window_start
                if len(self._batch_queue) < self._batch_threshold_count and queue_age < self._batch_threshold_seconds:
                    return None

            batch_requests = list(self._batch_queue)
            self._batch_queue.clear()
            self._batch_window_start = None

        batch_id = f"batch-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        job = {
            "batch_id": batch_id,
            "status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "request_count": len(batch_requests),
            "workloads": {},
            "provider_batch_id": None,
        }
        for req in batch_requests:
            job["workloads"][req.workload] = job["workloads"].get(req.workload, 0) + 1

        with self._batch_lock:
            self._batch_jobs[batch_id] = job
            self._batch_metrics["submitted"] += 1

        try:
            if hasattr(self._client, "messages") and hasattr(self._client.messages, "batches"):
                payload = [
                    {"custom_id": req.request_id, "params": req.api_kwargs}
                    for req in batch_requests
                ]
                batch = self._client.messages.batches.create(requests=payload)
                job["provider_batch_id"] = getattr(batch, "id", None)
                job["status"] = "submitted"
                return batch_id
        except Exception as e:
            job["status"] = "error"
            job["error"] = str(e)
            with self._batch_lock:
                self._batch_metrics["errors"] += 1

        # Fallback: process locally to keep results flowing
        self._process_batch_locally(batch_id, batch_requests)
        return batch_id

    def _process_batch_locally(self, batch_id: str, batch_requests: list[BatchRequest]) -> None:
        results = {}
        for req in batch_requests:
            try:
                response = self._client.messages.create(**req.api_kwargs)
                llm_response = self._parse_response(response)
                llm_response.request_id = req.request_id
                llm_response.batch_id = batch_id
                results[req.request_id] = llm_response
            except Exception as e:
                results[req.request_id] = LLMResponse(
                    content=str(e),
                    stop_reason="error",
                    request_id=req.request_id,
                    batch_id=batch_id,
                )
                with self._batch_lock:
                    self._batch_metrics["errors"] += 1

        with self._batch_lock:
            self._batch_results.update(results)
            job = self._batch_jobs.get(batch_id)
            if job:
                job["status"] = "completed"
                job["completed_at"] = datetime.now(timezone.utc).isoformat()
            self._batch_metrics["completed"] += 1

    def _build_api_kwargs(
        self,
        messages: list[LLMMessage],
        model_id: str,
        tools: Optional[list[dict]],
    ) -> dict:
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

        if system_content:
            api_kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_content,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        if tools:
            cached_tools = []
            for i, tool in enumerate(tools):
                t = dict(tool)
                if i == len(tools) - 1:
                    t["cache_control"] = {"type": "ephemeral"}
                cached_tools.append(t)
            api_kwargs["tools"] = cached_tools

        return api_kwargs

    def _parse_response(self, response) -> LLMResponse:
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
        # Budget caps disabled — API providers handle their own rate limits.
        # The budget manager still tracks spend for observability but doesn't gate sessions.
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

        model_override = kwargs.pop("model_override", None)
        model_alias = model_override or self.MODEL_ALIAS.get(model_tier, "sonnet")

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
            # Re-inject system prompt on resume to prevent role identity loss
            resume_sp = system_prompt
            if tools:
                resume_sp += "\n" + self.TOOL_PROTOCOL + self._format_tools_for_prompt(tools)
            if resume_sp.strip():
                cmd.extend(["--system-prompt", resume_sp.strip()])
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

        import subprocess
        try:
            from backend.services.runtime_config import get_runtime_config
            from backend.services.process_registry import get_process_registry, start_tracked_process
            _effective_timeout = get_runtime_config()["timeout"]
            _registry = get_process_registry()

            # Set OTEL env vars so agent sessions export metrics to Prometheus
            env = os.environ.copy()
            env.update({
                "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
                "OTEL_METRICS_EXPORTER": "otlp",
                "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
                "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:9090/api/v1/otlp",
            })

            proc = start_tracked_process(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self._project_root,
                env=env,
            )
            try:
                stdout, stderr = proc.communicate(timeout=_effective_timeout)
            except subprocess.TimeoutExpired:
                from backend.services.process_registry import _kill_tree
                _kill_tree(proc.pid)
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
                return LLMResponse(content=f"Error: Claude CLI timed out after {_effective_timeout}s", stop_reason="error")
            finally:
                _registry.unregister(proc.pid)

            if proc.returncode != 0:
                error_msg = stderr.strip() or f"claude CLI exited with code {proc.returncode}"
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
                    # Re-inject system prompt on retry-resume
                    retry_sp = system_prompt
                    if tools:
                        retry_sp += "\n" + self.TOOL_PROTOCOL + self._format_tools_for_prompt(tools)
                    if retry_sp.strip():
                        resume_cmd.extend(["--system-prompt", retry_sp.strip()])
                    if self.max_budget_usd:
                        resume_cmd.extend(["--max-budget-usd", str(self.max_budget_usd)])
                    resume_cmd.append(user_content)
                    proc2 = start_tracked_process(
                        resume_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=self._project_root,
                        env=env,
                    )
                    try:
                        stdout, stderr = proc2.communicate(timeout=_effective_timeout)
                    except subprocess.TimeoutExpired:
                        from backend.services.process_registry import _kill_tree
                        _kill_tree(proc2.pid)
                        try:
                            proc2.wait(timeout=5)
                        except Exception:
                            pass
                        return LLMResponse(content=f"Error: Claude CLI timed out after {_effective_timeout}s", stop_reason="error")
                    finally:
                        _registry.unregister(proc2.pid)
                    if proc2.returncode != 0:
                        error_msg = stderr.strip() or f"claude CLI exited with code {proc2.returncode}"
                        return LLMResponse(content=f"Error: {error_msg}", stop_reason="error")
                    # Resume succeeded, mark this session as active for future calls
                    should_add_to_active = True
                else:
                    return LLMResponse(content=f"Error: {error_msg}", stop_reason="error")

            # Only add to active sessions after successful execution
            if should_add_to_active and session_id:
                self._active_sessions.add(session_id)

            # Parse JSON output from claude CLI
            raw_content = stdout.strip()
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

        except FileNotFoundError:
            return LLMResponse(content="Error: 'claude' CLI not found in PATH", stop_reason="error")

    def cleanup_session(self, session_id: str) -> None:
        """Remove a finished session from tracking and delete its Claude Code session file."""
        self._active_sessions.discard(session_id)
        # Delete the session JSONL file so it doesn't clutter the user's resume list
        try:
            import pathlib
            # Claude Code stores sessions as JSONL files in the project directory
            project_key = self._project_root.replace("/", "-").lstrip("-")
            sessions_dir = pathlib.Path.home() / ".claude" / "projects" / project_key
            session_file = sessions_dir / f"{session_id}.jsonl"
            if session_file.exists():
                session_file.unlink()
                logger.debug("Cleaned up Claude CLI session file %s", session_file)
            # Also check for session subdirectory
            session_dir = sessions_dir / session_id
            if session_dir.is_dir():
                import shutil
                shutil.rmtree(session_dir, ignore_errors=True)
                logger.debug("Cleaned up Claude CLI session dir %s", session_dir)
        except Exception:
            logger.debug("Session cleanup skipped for %s", session_id, exc_info=True)


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
        model_override = kwargs.pop("model_override", None)
        model_id = model_override or self.OPENAI_MODEL_MAP.get(model_tier, "gpt-4o-mini")

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
    """Runs agents via the Codex CLI or ChatGPT CLI (if available)."""

    def __init__(self, command: str = "chatgpt"):
        self._command = command

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        system_prompt = ""
        user_content = ""
        for msg in messages:
            if msg.role == "system":
                system_prompt += msg.content + "\n"
            elif msg.role == "user":
                user_content = msg.content

        if self._command == "codex":
            # Codex CLI: codex --quiet "<prompt>"
            prompt = user_content
            if system_prompt.strip():
                prompt = system_prompt.strip() + "\n\n" + user_content
            cmd = ["codex", "--quiet", prompt]
        else:
            cmd = ["chatgpt"]
            if system_prompt.strip():
                cmd.extend(["--system", system_prompt.strip()])
            cmd.append(user_content)

        try:
            from backend.services.process_registry import run_tracked_process
            proc = run_tracked_process(cmd, capture_output=True, text=True, timeout=600)
            if proc.returncode != 0:
                return LLMResponse(content=f"Error: {proc.stderr.strip()}", stop_reason="error")
            return LLMResponse(content=proc.stdout.strip(), stop_reason="end_turn")
        except subprocess.TimeoutExpired:
            return LLMResponse(content=f"Error: {self._command} CLI timed out", stop_reason="error")
        except FileNotFoundError:
            return LLMResponse(content=f"Error: '{self._command}' CLI not found", stop_reason="error")


class OllamaClient(LLMClient):
    """Local Ollama inference client via REST API.

    Talks to Ollama at localhost:11434. Supports any locally-pulled model.
    Falls back gracefully if Ollama is not running.

    Environment variables:
        DSI_OLLAMA_MODEL: Override model for all tiers (e.g. "qwen3-coder:30b")
        DSI_OLLAMA_URL: Override Ollama base URL (default: http://localhost:11434)
        DSI_OLLAMA_NUM_CTX: Context window size (default: 8192)
        DSI_OLLAMA_TIMEOUT: Request timeout in seconds (default: 300)
    """

    OLLAMA_MODEL_MAP = {
        ModelTier.OPUS: "qwen2.5-coder:32b",  # Best quality coding model
        ModelTier.SONNET: "deepseek-coder-v2:16b",  # Good coding, fits in RAM with headroom
        ModelTier.HAIKU: "qwen2.5:7b",  # Fast utility model
    }

    def __init__(self, base_url: str | None = None):
        self._base_url = (
            base_url or os.environ.get("DSI_OLLAMA_URL", "http://localhost:11434")
        ).rstrip("/")
        self._num_ctx = int(os.environ.get("DSI_OLLAMA_NUM_CTX", "8192"))
        self._timeout = int(os.environ.get("DSI_OLLAMA_TIMEOUT", "300"))
        self._model_override_env = os.environ.get("DSI_OLLAMA_MODEL")

    @staticmethod
    def is_available(base_url: str = "http://localhost:11434") -> bool:
        """Check if Ollama is running and has at least one model."""
        import urllib.request
        url = os.environ.get("DSI_OLLAMA_URL", base_url)
        try:
            req = urllib.request.Request(f"{url.rstrip('/')}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = _json.loads(resp.read())
                return len(data.get("models", [])) > 0
        except Exception:
            return False

    def _resolve_override(self, model_override: str) -> Optional[str]:
        """Return model_override only if it's available locally in Ollama.

        When the SmartRouter passes a model_override meant for another provider
        (e.g. 'claude-haiku-4-5-20251001'), we should ignore it rather than 404.
        """
        import urllib.request

        try:
            req = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = _json.loads(resp.read())
                available = [m["name"].lower() for m in data.get("models", [])]
        except Exception:
            return None

        override_lower = model_override.lower()
        # Exact match
        if override_lower in available:
            return model_override
        # Base name match (e.g. "qwen2.5-coder" matches "qwen2.5-coder:32b")
        base = override_lower.split(":")[0]
        for m in available:
            if m.startswith(base):
                return model_override

        logger.debug("Ignoring model_override %r — not available in Ollama", model_override)
        return None

    def _get_best_model(self, model_tier: ModelTier) -> str:
        """Pick the best available local model for the requested tier."""
        import urllib.request

        # Environment override takes precedence
        if self._model_override_env:
            return self._model_override_env

        preferred = self.OLLAMA_MODEL_MAP.get(model_tier, "llama3.1:8b")
        try:
            req = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = _json.loads(resp.read())
                available = [m["name"] for m in data.get("models", [])]
        except Exception:
            return preferred

        # Case-insensitive match for preferred model
        preferred_lower = preferred.lower()
        for m in available:
            if m.lower() == preferred_lower:
                return m

        # Try base name without tag (case-insensitive)
        base = preferred.split(":")[0].lower()
        for m in available:
            if m.lower().startswith(base):
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

        model_override = kwargs.pop("model_override", None)
        # Ignore model_override if it's not a locally-available Ollama model
        # (SmartRouter passes provider-specific overrides to all providers)
        if model_override:
            model = self._resolve_override(model_override) or self._get_best_model(model_tier)
        else:
            model = self._get_best_model(model_tier)

        # Convert messages to Ollama format, filtering to valid roles
        ollama_messages = []
        valid_roles = {"system", "user", "assistant"}
        for msg in messages:
            role = msg.role if msg.role in valid_roles else "user"
            ollama_messages.append({"role": role, "content": msg.content})

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
            "options": {
                "num_ctx": self._num_ctx,
            },
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self._base_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
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

        except urllib.error.HTTPError as e:
            logger.warning("Ollama HTTP %d for model %s: %s", e.code, model, e.reason)
            return LLMResponse(
                content=f"Error: Ollama HTTP {e.code} ({e.reason}) for model {model}",
                stop_reason="error",
            )
        except urllib.error.URLError as e:
            logger.warning("Ollama connection failed: %s", e)
            return LLMResponse(content=f"Error: Ollama connection failed — {e}", stop_reason="error")
        except Exception as e:
            logger.warning("Ollama request failed: %s", e)
            return LLMResponse(content=f"Error: Ollama request failed — {e}", stop_reason="error")


class GHCopilotCLIClient(LLMClient):
    """Runs prompts via GitHub Copilot CLI (`gh copilot`).

    No session persistence or native tool support. Tools are embedded
    in the system prompt using the same XML protocol as ClaudeCLIClient.
    """

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

        # Build full prompt (gh copilot takes a single prompt string)
        prompt = user_content
        if tools:
            system_prompt += "\n" + ClaudeCLIClient.TOOL_PROTOCOL + ClaudeCLIClient._format_tools_for_prompt(tools)
        if system_prompt.strip():
            prompt = system_prompt.strip() + "\n\n" + user_content

        cmd = ["gh", "copilot", "suggest", "-t", "shell", prompt]

        try:
            from backend.services.process_registry import get_process_registry, start_tracked_process
            registry = get_process_registry()

            proc = start_tracked_process(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = proc.communicate(timeout=600)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                return LLMResponse(content="Error: gh copilot timed out after 600s", stop_reason="error")
            finally:
                registry.unregister(proc.pid)

            if proc.returncode != 0:
                return LLMResponse(content=f"Error: {stderr.strip()}", stop_reason="error")

            content = stdout.strip()
            if tools:
                text_content, tool_calls = ClaudeCLIClient._parse_tool_calls(content)
                return LLMResponse(
                    content=text_content,
                    tool_calls=tool_calls,
                    stop_reason="tool_use" if tool_calls else "end_turn",
                )
            return LLMResponse(content=content, stop_reason="end_turn")

        except FileNotFoundError:
            return LLMResponse(content="Error: 'gh' CLI not found in PATH", stop_reason="error")


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
        model_override = kwargs.pop("model_override", None)
        self.calls.append({
            "messages": messages,
            "model_tier": model_tier,
            "model_id": model_override or MODEL_TIER_MAP[model_tier],
            "model_override": model_override,
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
            try:
                response = self._client.chat(messages, model_tier, tools, **kwargs)
            except Exception as exc:
                response = LLMResponse(
                    content=f"Error: {type(exc).__name__}: {exc}",
                    stop_reason="error",
                )
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


@dataclass
class ProviderStats:
    """Accumulated usage statistics for a single LLM provider."""
    requests: int = 0
    successes: int = 0
    failures: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0


@dataclass
class FailoverEvent:
    """Record of a failover from one provider to another."""
    timestamp: str = ""
    from_provider: str = ""
    to_provider: str = ""
    error_snippet: str = ""


class SmartRouter(LLMClient):
    """Intelligent provider selection with failover chain.

    Routes requests to the best available provider:
    - Simple text (no tools, no images) → CLI agents preferred
    - Complex requests (images, native tool use) → API clients preferred

    Each provider is wrapped with RetryingClient (5 retries with exponential
    backoff). If a provider exhausts all retries, we fail over to the next one.

    Tracks per-provider usage statistics and failover events for observability.
    """

    MAX_FAILOVER_EVENTS = 50

    def __init__(self, providers: list[tuple[str, LLMClient]]):
        """
        Args:
            providers: List of (name, client) tuples in priority order.
                       Each client should already be wrapped in RetryingClient
                       if retry behavior is desired.
        """
        self._providers = providers
        self.last_used_provider: str = ""
        self._stats: dict[str, ProviderStats] = {name: ProviderStats() for name, _ in providers}
        self._failover_events: list[FailoverEvent] = []
        self._started_at: str = datetime.now(timezone.utc).isoformat()

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
        """Rank providers based on request needs.

        If DSI_LLM_PRIORITY is set (comma-separated provider names), that order
        is used instead of the default heuristic. Example:
            DSI_LLM_PRIORITY=ollama,anthropic-api
        """
        priority = os.environ.get("DSI_LLM_PRIORITY")
        if priority:
            # User-specified order: match by name, append any unmentioned providers
            ordered_names = [n.strip() for n in priority.split(",") if n.strip()]
            by_name = {n: c for n, c in self._providers}
            result = [(n, by_name[n]) for n in ordered_names if n in by_name]
            # Append remaining providers not in the priority list
            mentioned = set(ordered_names)
            for n, c in self._providers:
                if n not in mentioned:
                    result.append((n, c))
            return result

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

    def _record_failover(self, from_provider: str, to_provider: str, error: str) -> None:
        """Record a failover event, keeping only the most recent MAX_FAILOVER_EVENTS."""
        self._failover_events.append(FailoverEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            from_provider=from_provider,
            to_provider=to_provider,
            error_snippet=error[:200],
        ))
        if len(self._failover_events) > self.MAX_FAILOVER_EVENTS:
            self._failover_events = self._failover_events[-self.MAX_FAILOVER_EVENTS:]

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

        prev_failed_name: Optional[str] = None
        prev_error: str = ""

        for name, client in ranked:
            logger.debug("Trying LLM provider: %s", name)
            if name in self._stats:
                self._stats[name].requests += 1

            try:
                response = client.chat(messages, model_tier, tools, **kwargs)
            except Exception as exc:
                logger.warning("Provider %s raised exception: %s", name, exc)
                response = LLMResponse(
                    content=f"Error: {type(exc).__name__}: {exc}",
                    stop_reason="error",
                )

            if response.stop_reason != "error":
                self.last_used_provider = name
                if name in self._stats:
                    self._stats[name].successes += 1
                    self._stats[name].total_input_tokens += response.input_tokens
                    self._stats[name].total_output_tokens += response.output_tokens
                    self._stats[name].total_cached_tokens += response.cached_tokens
                if prev_failed_name is not None:
                    self._record_failover(prev_failed_name, name, prev_error)
                # Record spend in budget manager
                try:
                    from backend.services.budget_manager import get_budget_manager
                    bm = get_budget_manager()
                    bm.record_spend(
                        provider=name,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        session_id=kwargs.get("session_id"),
                        corps_id=kwargs.get("corps_id"),
                    )
                except Exception:
                    pass  # budget tracking is best-effort
                return response

            if name in self._stats:
                self._stats[name].failures += 1
            logger.warning("Provider %s failed, trying next: %s", name, response.content[:200])
            prev_failed_name = name
            prev_error = response.content[:200]

        # All providers failed
        self.last_used_provider = "none"
        if prev_failed_name is not None:
            self._record_failover(prev_failed_name, "none", "All providers exhausted")
        return LLMResponse(
            content="Error: All LLM providers exhausted after retries",
            stop_reason="error",
        )

    def get_usage_stats(self) -> dict:
        """Return accumulated usage statistics for all providers."""
        from dataclasses import asdict

        providers = []
        for name, client in self._providers:
            stats = self._stats.get(name, ProviderStats())
            providers.append({
                "name": name,
                "capabilities": {
                    "supports_images": client.supports_images,
                    "supports_native_tools": client.supports_native_tools,
                    "supports_caching": client.supports_caching,
                },
                "stats": asdict(stats),
            })

        return {
            "active_provider": self.last_used_provider,
            "started_at": self._started_at,
            "providers": providers,
            "failover_events": [asdict(e) for e in self._failover_events],
            "total_requests": sum(s.requests for s in self._stats.values()),
            "total_failures": sum(s.failures for s in self._stats.values()),
        }


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


def build_llm_client(force_mock: bool = False) -> LLMClient:
    """Build the best available LLM client chain.

    Discovers all available providers and wraps them in a SmartRouter
    with exponential retry backoff per provider.

    Returns a single LLMClient that transparently handles routing,
    retries, and failover.

    If force_mock is True, returns MockLLMClient immediately (for tests).
    """
    if force_mock:
        return MockLLMClient()

    import shutil

    providers: list[tuple[str, LLMClient]] = []
    skip_cli = os.environ.get("DSI_NO_CLI_PROVIDERS")

    # 1. Anthropic API (highest priority — direct, reliable, no context injection)
    if os.environ.get("ANTHROPIC_SDK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"):
        try:
            providers.append(("anthropic-api", AnthropicLLMClient()))
            logger.info("LLM provider available: Anthropic API")
        except ImportError:
            logger.warning("ANTHROPIC_API_KEY set but 'anthropic' package not installed — skipping")

    # 2. OpenAI API
    if os.environ.get("OPENAI_API_KEY"):
        try:
            providers.append(("openai-api", OpenAIClient()))
            logger.info("LLM provider available: OpenAI API")
        except ImportError:
            logger.warning("OPENAI_API_KEY set but 'openai' package not installed — skipping")

    # 3. Ollama (local — free, no API limits)
    if OllamaClient.is_available():
        ollama = OllamaClient()
        providers.append(("ollama", ollama))
        model_env = os.environ.get("DSI_OLLAMA_MODEL", "auto")
        logger.info("LLM provider available: Ollama (local, model=%s, num_ctx=%d)",
                     model_env, ollama._num_ctx)

    if skip_cli:
        logger.info("CLI providers skipped (DSI_NO_CLI_PROVIDERS is set)")
    else:
        # 4. Claude CLI (deprioritized — injects CLAUDE.md and full agent context)
        if shutil.which("claude"):
            providers.append(("claude-cli", ClaudeCLIClient()))
            logger.info("LLM provider available: Claude CLI (deprioritized)")

        # 5. GitHub Copilot CLI
        if shutil.which("gh"):
            import subprocess as _sp
            try:
                _sp.run(["gh", "copilot", "--help"], capture_output=True, timeout=5)
                providers.append(("gh-copilot-cli", GHCopilotCLIClient()))
                logger.info("LLM provider available: GitHub Copilot CLI")
            except Exception:
                pass

        # 6. Codex CLI (OpenAI's agent CLI)
        if shutil.which("codex"):
            providers.append(("codex-cli", ChatGPTCLIClient(command="codex")))
            logger.info("LLM provider available: Codex CLI")
        # 6b. ChatGPT CLI (fallback if codex not found)
        elif shutil.which("chatgpt"):
            providers.append(("chatgpt-cli", ChatGPTCLIClient()))
            logger.info("LLM provider available: ChatGPT CLI")

    if not providers:
        logger.warning("No LLM providers available — using MockLLMClient")
        return MockLLMClient()

    # Wrap each provider with retry logic and create smart router
    # CLI clients get 1 retry (they work or they don't), API clients get 5
    wrapped = [
        (name, RetryingClient(
            client,
            max_retries=1 if name.endswith("-cli") else 5,
            base_delay=1.0,
        ))
        for name, client in providers
    ]

    router = SmartRouter(wrapped)
    logger.info("LLM SmartRouter initialized with %d providers: %s",
                len(providers), ", ".join(n for n, _ in providers))
    return router
