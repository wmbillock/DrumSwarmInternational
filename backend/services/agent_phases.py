"""Agent phase protocol — 9-phase workflow adapted to DCI metaphor.

Phases: WARM_UP → GATHER_CONTEXT → PLAN → EXECUTE → REVIEW → VERIFY → SUBMIT → REPORT → COOL_DOWN

Phase controller injects phase-specific guidance messages and provides
heuristic phase detection from tool calls (advisory, not blocking).
"""

import enum
from dataclasses import dataclass, field
from typing import Optional


class AgentPhase(str, enum.Enum):
    WARM_UP = "warm_up"
    GATHER_CONTEXT = "gather_context"
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"
    VERIFY = "verify"
    SUBMIT = "submit"
    REPORT = "report"
    COOL_DOWN = "cool_down"


# Ordered phase sequence
PHASE_ORDER = list(AgentPhase)

# Phase-specific guidance injected into agent context
PHASE_GUIDANCE = {
    AgentPhase.WARM_UP: (
        "PHASE: WARM_UP — You are initializing. Review your role, tools, and any context from previous sessions. "
        "Understand the task before taking action."
    ),
    AgentPhase.GATHER_CONTEXT: (
        "PHASE: GATHER_CONTEXT — Gather all information needed to do your work. "
        "Use get_segment, get_segment_children, get_reps_for_segment to understand the current state. "
        "Do not start executing yet."
    ),
    AgentPhase.PLAN: (
        "PHASE: PLAN — Based on the context gathered, plan your approach. "
        "Decide which tools to call, in what order, and what the expected outcomes are."
    ),
    AgentPhase.EXECUTE: (
        "PHASE: EXECUTE — Execute your plan. Call tools to create segments, reps, transitions, or handoffs. "
        "Stay focused on the current task."
    ),
    AgentPhase.REVIEW: (
        "PHASE: REVIEW — Review the work done so far. Check that outputs match expectations. "
        "Verify segments and reps are in the correct state."
    ),
    AgentPhase.VERIFY: (
        "PHASE: VERIFY — Run verification checks. Ensure quality gates pass and results are valid."
    ),
    AgentPhase.SUBMIT: (
        "PHASE: SUBMIT — Submit completed work. Call submit_work or transition reps to review/completed. "
        "Hand off downstream if needed."
    ),
    AgentPhase.REPORT: (
        "PHASE: REPORT — Provide a summary of what was accomplished, any issues encountered, "
        "and the current state of work."
    ),
    AgentPhase.COOL_DOWN: (
        "PHASE: COOL_DOWN — Wrap up. Ensure all handoffs are sent and no loose ends remain."
    ),
}

# Tool-to-phase heuristic mapping
TOOL_PHASE_HINTS: dict[str, AgentPhase] = {
    "get_segment": AgentPhase.GATHER_CONTEXT,
    "get_segment_children": AgentPhase.GATHER_CONTEXT,
    "get_reps_for_segment": AgentPhase.GATHER_CONTEXT,
    "create_segment": AgentPhase.EXECUTE,
    "create_rep": AgentPhase.EXECUTE,
    "transition_rep": AgentPhase.EXECUTE,
    "submit_work": AgentPhase.SUBMIT,
    "verify_work": AgentPhase.VERIFY,
    "handoff": AgentPhase.SUBMIT,
    "send_message": AgentPhase.REPORT,
}


@dataclass
class PhaseController:
    """Tracks and manages agent phase progression."""
    current_phase: AgentPhase = AgentPhase.WARM_UP
    phase_history: list[AgentPhase] = field(default_factory=list)
    tool_calls_per_phase: dict[str, int] = field(default_factory=dict)

    def advance(self) -> AgentPhase:
        """Advance to the next phase in sequence."""
        self.phase_history.append(self.current_phase)
        idx = PHASE_ORDER.index(self.current_phase)
        if idx < len(PHASE_ORDER) - 1:
            self.current_phase = PHASE_ORDER[idx + 1]
        return self.current_phase

    def set_phase(self, phase: AgentPhase) -> None:
        """Explicitly set the current phase."""
        self.phase_history.append(self.current_phase)
        self.current_phase = phase

    def detect_phase_from_tool(self, tool_name: str) -> Optional[AgentPhase]:
        """Heuristically detect phase from a tool call. Advisory only."""
        hint = TOOL_PHASE_HINTS.get(tool_name)
        if hint and PHASE_ORDER.index(hint) > PHASE_ORDER.index(self.current_phase):
            self.set_phase(hint)
        # Track tool calls per phase
        phase_key = self.current_phase.value
        self.tool_calls_per_phase[phase_key] = self.tool_calls_per_phase.get(phase_key, 0) + 1
        return self.current_phase

    def get_guidance(self) -> str:
        """Get guidance message for the current phase."""
        return PHASE_GUIDANCE.get(self.current_phase, "")

    def get_state(self) -> dict:
        """Serialize phase state for context snapshot."""
        return {
            "current_phase": self.current_phase.value,
            "phase_history": [p.value for p in self.phase_history],
            "tool_calls_per_phase": self.tool_calls_per_phase,
        }

    @classmethod
    def from_state(cls, state: dict) -> "PhaseController":
        """Restore phase state from context snapshot."""
        controller = cls()
        if state:
            controller.current_phase = AgentPhase(state.get("current_phase", "warm_up"))
            controller.phase_history = [AgentPhase(p) for p in state.get("phase_history", [])]
            controller.tool_calls_per_phase = state.get("tool_calls_per_phase", {})
        return controller
