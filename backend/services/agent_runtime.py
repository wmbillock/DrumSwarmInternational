"""Agent runtime. Connects LLM calls to tool execution and session lifecycle.

The runtime manages the agent loop:
1. Load context (definition prompt + optional snapshot warm-up)
2. Send messages to LLM
3. If LLM requests tool use -> check permissions -> execute -> feed result back
4. Repeat until LLM returns end_turn or max iterations reached
5. Save context snapshot on completion
"""

import json
from dataclasses import dataclass, field
from typing import Callable, Optional

from sqlalchemy.orm import Session

from backend.models.agent_definition import AgentDefinition
from backend.models.agent_session import AgentSession
from backend.services.agent_lifecycle import (
    complete_session,
    fail_session,
)
from backend.services.llm_client import LLMClient, LLMMessage, LLMResponse
from backend.services.tool_executor import ToolExecutor, ToolPermissionDenied, ToolNotFound


MAX_ITERATIONS = 20


@dataclass
class RunResult:
    """Result of an agent runtime execution."""
    session_id: str
    final_response: str = ""
    tool_calls_made: list[dict] = field(default_factory=list)
    iterations: int = 0
    status: str = "completed"  # completed, failed, max_iterations
    error: Optional[str] = None


def build_initial_messages(
    definition: AgentDefinition,
    task_description: str,
    context_snapshot: Optional[str] = None,
) -> list[LLMMessage]:
    """Build the initial message list for an agent session.

    Includes system prompt from definition, optional warm-up context
    from a previous session's snapshot, and the task description.
    """
    messages = [
        LLMMessage(role="system", content=definition.system_prompt),
    ]

    if context_snapshot:
        messages.append(
            LLMMessage(
                role="user",
                content=f"Context from previous session:\n{context_snapshot}",
            )
        )
        messages.append(
            LLMMessage(
                role="assistant",
                content="Understood. I have the context from the previous session and will continue from where it left off.",
            )
        )

    messages.append(
        LLMMessage(role="user", content=task_description),
    )

    return messages


def run_agent(
    db: Session,
    session_id: str,
    llm_client: LLMClient,
    tool_executor: ToolExecutor,
    task_description: str,
    context_snapshot: Optional[str] = None,
    max_iterations: int = MAX_ITERATIONS,
    on_event: Optional[Callable[[dict], None]] = None,
) -> RunResult:
    """Execute the agent loop for a session.

    Returns a RunResult with the final response, tool calls made, and status.
    """
    def _emit(event: dict) -> None:
        if on_event:
            on_event(event)

    agent_session = db.get(AgentSession, session_id)
    if agent_session is None:
        raise ValueError(f"Session {session_id} not found")

    definition = db.get(AgentDefinition, agent_session.definition_id)
    if definition is None:
        raise ValueError(f"Definition {agent_session.definition_id} not found")

    _emit({
        "type": "agent_status",
        "role": definition.role,
        "session_id": session_id,
        "status": "running",
    })

    messages = build_initial_messages(definition, task_description, context_snapshot)
    tool_schemas = tool_executor.registry.get_schemas_for_session(db, session_id)

    # Detect CLI client — it handles tool calls internally via MCP
    is_cli_client = hasattr(llm_client, '_make_mcp_config')

    # For CLI client, resolve corps_id from session
    corps_id = ""
    if is_cli_client:
        corps_id = agent_session.corps_id if hasattr(agent_session, 'corps_id') else ""

    result = RunResult(session_id=session_id)

    try:
        if is_cli_client:
            # CLI mode: single call, CLI handles tool loop via MCP
            result.iterations = 1
            response = llm_client.chat(
                messages=messages,
                model_tier=definition.model_tier,
                tools=tool_schemas if tool_schemas else None,
                role=definition.role,
                corps_id=corps_id,
                session_id=session_id,
            )
            result.final_response = response.content
            result.status = "completed" if response.stop_reason != "error" else "failed"
            if response.stop_reason == "error":
                result.error = response.content

            _emit({
                "type": "agent_response",
                "role": definition.role,
                "session_id": session_id,
                "content": response.content,
            })
        else:
            # API mode: iterative tool call loop
            for i in range(max_iterations):
                result.iterations = i + 1

                response = llm_client.chat(
                    messages=messages,
                    model_tier=definition.model_tier,
                    tools=tool_schemas if tool_schemas else None,
                )

                if not response.wants_tool_use:
                    result.final_response = response.content
                    result.status = "completed"

                    _emit({
                        "type": "agent_response",
                        "role": definition.role,
                        "session_id": session_id,
                        "content": response.content,
                    })
                    break

                # Process tool calls
                for tool_call in response.tool_calls:
                    _emit({
                        "type": "tool_call",
                        "role": definition.role,
                        "session_id": session_id,
                        "tool": tool_call.tool_name,
                        "args": tool_call.arguments,
                    })

                    tool_result_data = _execute_tool_call(
                        db, session_id, tool_executor, tool_call.tool_name, tool_call.arguments
                    )
                    result.tool_calls_made.append({
                        "tool": tool_call.tool_name,
                        "arguments": tool_call.arguments,
                        "result": tool_result_data,
                    })

                    _emit({
                        "type": "tool_result",
                        "role": definition.role,
                        "session_id": session_id,
                        "tool": tool_call.tool_name,
                        "result": tool_result_data,
                    })

                    # Feed tool result back into conversation
                    messages.append(
                        LLMMessage(role="assistant", content=response.content or f"[tool_use: {tool_call.tool_name}]")
                    )
                    messages.append(
                        LLMMessage(
                            role="user",
                            content=f"Tool result for {tool_call.tool_name}: {json.dumps(tool_result_data)}",
                        )
                    )
            else:
                result.status = "max_iterations"

        # Save snapshot and complete
        snapshot = json.dumps({
            "final_response": result.final_response,
            "tool_calls": result.tool_calls_made,
            "iterations": result.iterations,
        })
        complete_session(db, session_id, context_snapshot=snapshot)

        _emit({
            "type": "agent_status",
            "role": definition.role,
            "session_id": session_id,
            "status": result.status,
        })

    except Exception as e:
        result.status = "failed"
        result.error = str(e)

        _emit({
            "type": "agent_status",
            "role": definition.role,
            "session_id": session_id,
            "status": "failed",
            "error": str(e),
        })

        try:
            fail_session(db, session_id, error=str(e))
        except Exception:
            pass  # Session may already be in terminal state

    return result


def _execute_tool_call(
    db: Session,
    session_id: str,
    tool_executor: ToolExecutor,
    tool_name: str,
    arguments: dict,
) -> dict:
    """Execute a single tool call, returning a result dict."""
    try:
        tool_result = tool_executor.execute(db, session_id, tool_name, arguments)
        return {"success": tool_result.success, "output": tool_result.output, "error": tool_result.error}
    except ToolPermissionDenied as e:
        return {"success": False, "output": None, "error": str(e)}
    except ToolNotFound as e:
        return {"success": False, "output": None, "error": str(e)}
