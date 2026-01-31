"""Dry-run mode — preview agent behavior without real execution.

DryRunToolExecutor: records calls, returns synthetic results.
SimulationLLMClient: uses Haiku with "plan what you would do" prompt.
"""

from dataclasses import dataclass, field
from typing import Optional

from backend.services.llm_client import LLMClient, LLMMessage, LLMResponse, MockLLMClient
from backend.services.tool_executor import ToolExecutor, ToolRegistry, ToolResult
from backend.models.agent_definition import ModelTier


@dataclass
class DryRunRecord:
    """Record of a simulated tool call."""
    tool_name: str
    arguments: dict
    synthetic_result: dict


class DryRunToolExecutor(ToolExecutor):
    """Records tool calls and returns synthetic results instead of executing."""

    def __init__(self, registry: ToolRegistry):
        super().__init__(registry)
        self.recorded_calls: list[DryRunRecord] = []

    def execute(self, db, session_id: str, tool_name: str, arguments: dict) -> ToolResult:
        """Record the call and return a synthetic success result."""
        synthetic = {
            "id": f"dry-run-{len(self.recorded_calls)}",
            "status": "simulated",
            "tool": tool_name,
        }

        # Produce tool-specific synthetic results
        from backend.models.rep import RepStatus
        from backend.models.segment import SegmentType

        if tool_name == "create_segment":
            synthetic.update({
                "type": arguments.get("type", SegmentType.SEGMENT.value),
                "title": arguments.get("title", "simulated"),
            })
        elif tool_name == "create_rep":
            synthetic.update({
                "segment_id": arguments.get("segment_id", ""),
                "status": RepStatus.PENDING.value,
            })
        elif tool_name in ("transition_rep", "submit_work"):
            synthetic.update({
                "rep_id": arguments.get("rep_id", ""),
                "status": arguments.get("new_status", RepStatus.REVIEW.value),
            })
        elif tool_name == "handoff":
            synthetic.update({
                "from": "simulated",
                "to": arguments.get("to_role", ""),
            })

        record = DryRunRecord(
            tool_name=tool_name,
            arguments=arguments,
            synthetic_result=synthetic,
        )
        self.recorded_calls.append(record)
        return ToolResult(success=True, output=synthetic)

    def get_summary(self) -> str:
        """Return a readable summary of all recorded calls."""
        if not self.recorded_calls:
            return "No tool calls recorded."
        lines = [f"Dry-run recorded {len(self.recorded_calls)} tool calls:"]
        for i, rec in enumerate(self.recorded_calls, 1):
            lines.append(f"  {i}. {rec.tool_name}({rec.arguments})")
        return "\n".join(lines)


class SimulationLLMClient(LLMClient):
    """Wraps another LLM client to inject dry-run planning prompts.

    Forces Haiku tier and adds "plan what you would do" instruction.
    """

    SIMULATION_PREFIX = (
        "SIMULATION MODE: You are in dry-run mode. Instead of executing real actions, "
        "describe what you WOULD do step by step. Call tools as normal — they will return "
        "synthetic results. Focus on demonstrating your decision-making process.\n\n"
    )

    def __init__(self, inner_client: Optional[LLMClient] = None):
        self._inner = inner_client or MockLLMClient()

    def chat(
        self,
        messages: list[LLMMessage],
        model_tier: ModelTier,
        tools: Optional[list[dict]] = None,
        **kwargs,
    ) -> LLMResponse:
        # Inject simulation prefix into system prompt
        modified_messages = []
        for msg in messages:
            if msg.role == "system":
                modified_messages.append(
                    LLMMessage(role="system", content=self.SIMULATION_PREFIX + msg.content)
                )
            else:
                modified_messages.append(msg)

        # Force Haiku to save costs
        return self._inner.chat(modified_messages, ModelTier.HAIKU, tools, **kwargs)
