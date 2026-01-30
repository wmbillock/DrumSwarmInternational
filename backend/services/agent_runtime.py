"""Agent runtime. Connects LLM calls to tool execution and session lifecycle.

The runtime manages the agent loop:
1. Load context (definition prompt + optional snapshot warm-up)
2. Send messages to LLM
3. If LLM requests tool use → check permissions → execute → feed result back
4. Repeat until LLM returns end_turn or max iterations reached
5. Save context snapshot on completion
"""

import json
from dataclasses import dataclass, field
from typing import Optional

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
) -> RunResult:
    """Execute the agent loop for a session.

    Returns a RunResult with the final response, tool calls made, and status.
    """
    agent_session = db.get(AgentSession, session_id)
    if agent_session is None:
        raise ValueError(f"Session {session_id} not found")

    definition = db.get(AgentDefinition, agent_session.definition_id)
    if definition is None:
        raise ValueError(f"Definition {agent_session.definition_id} not found")

    messages = build_initial_messages(definition, task_description, context_snapshot)
    tool_schemas = tool_executor.registry.get_schemas_for_session(db, session_id)

    result = RunResult(session_id=session_id)

    try:
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
                break

            # Process tool calls
            for tool_call in response.tool_calls:
                tool_result_data = _execute_tool_call(
                    db, session_id, tool_executor, tool_call.tool_name, tool_call.arguments
                )
                result.tool_calls_made.append({
                    "tool": tool_call.tool_name,
                    "arguments": tool_call.arguments,
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

    except Exception as e:
        result.status = "failed"
        result.error = str(e)
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
