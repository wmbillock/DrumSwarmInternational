"""Dry-run mode — simulate agent execution without real LLM calls.

DryRunToolExecutor records tool calls and returns synthetic results.
DryRunLLMClient uses minimal responses to plan what would happen.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class DryRunToolCall:
    """Record of a tool call made during dry run."""
    tool_name: str
    args: dict[str, Any]
    result: dict[str, Any]


@dataclass
class DryRunResult:
    """Result of a dry-run simulation."""
    role: str
    task: str
    tool_calls: list[DryRunToolCall] = field(default_factory=list)
    plan: str = ""
    estimated_iterations: int = 0


class DryRunToolExecutor:
    """Records tool calls and returns synthetic results."""

    def __init__(self):
        self.calls: list[DryRunToolCall] = []
        self._counter = 0

    def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call in dry-run mode."""
        self._counter += 1
        result = self._synthetic_result(tool_name, args)
        call = DryRunToolCall(tool_name=tool_name, args=args, result=result)
        self.calls.append(call)
        return result

    def _synthetic_result(self, tool_name: str, args: dict) -> dict[str, Any]:
        """Generate a synthetic result based on tool name."""
        fake_id = f"dry-run-{self._counter:04d}"

        if tool_name == "create_segment":
            return {"id": fake_id, "type": args.get("type", "segment"),
                    "title": args.get("title", ""), "status": "pending"}
        elif tool_name == "create_rep":
            return {"id": fake_id, "status": "pending",
                    "segment_id": args.get("segment_id", "")}
        elif tool_name == "transition_rep":
            return {"id": args.get("rep_id", fake_id),
                    "status": args.get("new_status", "pending")}
        elif tool_name == "submit_work":
            return {"id": args.get("rep_id", fake_id), "status": "review"}
        elif tool_name == "handoff":
            return {"status": "handed_off",
                    "from": args.get("from_role", ""),
                    "to": args.get("to_role", "")}
        elif tool_name == "send_message":
            return {"id": fake_id, "type": args.get("type", "status"),
                    "subject": args.get("subject", "")}
        elif tool_name.startswith("get_"):
            return {"id": args.get("segment_id", fake_id),
                    "status": "pending", "title": "Simulated"}
        else:
            return {"status": "ok", "dry_run": True}


def simulate_agent(
    role: str,
    task: str,
    system_prompt: str = "",
) -> DryRunResult:
    """Simulate what an agent would do without making real LLM calls.

    Returns a DryRunResult with the planned actions.
    """
    result = DryRunResult(role=role, task=task)
    result.plan = (
        f"Agent '{role}' would process task: {task[:200]}\n"
        f"System prompt length: {len(system_prompt)} chars\n"
        f"Mode: dry-run (no LLM calls made)"
    )
    result.estimated_iterations = 3  # Reasonable default estimate
    return result
