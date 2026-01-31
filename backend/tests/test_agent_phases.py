"""Tests for agent phase protocol."""

from backend.services.agent_phases import AgentPhase, PhaseController, PHASE_ORDER


class TestPhaseController:
    def test_initial_phase(self):
        pc = PhaseController()
        assert pc.current_phase == AgentPhase.WARM_UP

    def test_advance(self):
        pc = PhaseController()
        pc.advance()
        assert pc.current_phase == AgentPhase.GATHER_CONTEXT
        pc.advance()
        assert pc.current_phase == AgentPhase.PLAN

    def test_advance_through_all(self):
        pc = PhaseController()
        for expected in PHASE_ORDER[1:]:
            pc.advance()
            assert pc.current_phase == expected
        # Should stay at last phase
        pc.advance()
        assert pc.current_phase == AgentPhase.COOL_DOWN

    def test_set_phase(self):
        pc = PhaseController()
        pc.set_phase(AgentPhase.EXECUTE)
        assert pc.current_phase == AgentPhase.EXECUTE
        assert pc.phase_history == [AgentPhase.WARM_UP]

    def test_detect_phase_from_tool(self):
        pc = PhaseController()
        pc.detect_phase_from_tool("get_segment")
        assert pc.current_phase == AgentPhase.GATHER_CONTEXT

    def test_detect_phase_only_advances(self):
        pc = PhaseController()
        pc.set_phase(AgentPhase.EXECUTE)
        # Should not go backward to GATHER_CONTEXT
        pc.detect_phase_from_tool("get_segment")
        assert pc.current_phase == AgentPhase.EXECUTE

    def test_detect_phase_submit(self):
        pc = PhaseController()
        pc.detect_phase_from_tool("submit_work")
        assert pc.current_phase == AgentPhase.SUBMIT

    def test_tool_calls_tracked(self):
        pc = PhaseController()
        pc.detect_phase_from_tool("get_segment")
        pc.detect_phase_from_tool("get_segment_children")
        assert pc.tool_calls_per_phase.get("gather_context", 0) == 2

    def test_guidance(self):
        pc = PhaseController()
        g = pc.get_guidance()
        assert "WARM_UP" in g

    def test_serialization_roundtrip(self):
        pc = PhaseController()
        pc.advance()
        pc.advance()
        pc.detect_phase_from_tool("create_segment")
        state = pc.get_state()

        pc2 = PhaseController.from_state(state)
        assert pc2.current_phase == pc.current_phase
        assert len(pc2.phase_history) == len(pc.phase_history)
        assert pc2.tool_calls_per_phase == pc.tool_calls_per_phase
