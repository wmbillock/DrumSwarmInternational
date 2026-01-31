"""Integration test: full agent loop with MockLLMClient.

Simulates ED → PC → caption head → tech → completion flow.
"""

from backend.database import Base
from backend.models.agent_definition import ModelTier
from backend.services.agent_lifecycle import create_definition, spawn_session
from backend.services.agent_runtime import run_agent
from backend.services.corps_service import create_corps, initialize_corps, ROLE_TOOLS
from backend.services.llm_client import MockLLMClient, LLMResponse, ToolCall
from backend.services.tool_executor import ToolExecutor
from backend.tools import create_tool_registry


class TestIntegrationAgentLoop:
    def test_ed_creates_movements_and_handoffs(self, db):
        """Test that ED can create segments and hand off to PC."""
        corps = create_corps(db, "test-corps")
        sessions = initialize_corps(db, corps.id)

        llm = MockLLMClient()
        registry = create_tool_registry()
        executor = ToolExecutor(registry)

        # Create a root segment for the show
        from backend.services.segment_service import create_segment
        from backend.models.segment import SegmentType
        root = create_segment(db, type=SegmentType.SHOW, title="Test Show")

        ed_session = sessions["executive_director"]

        # Queue: ED creates a movement, then hands off, then responds
        llm.queue_response(LLMResponse(
            content="",
            tool_calls=[ToolCall(
                tool_name="create_segment",
                arguments={"type": "movement", "title": "Movement 1", "parent_id": root.id},
            )],
            stop_reason="tool_use",
        ))
        llm.queue_response(LLMResponse(
            content="",
            tool_calls=[ToolCall(
                tool_name="handoff",
                arguments={"to_role": "program_coordinator", "subject": "Break down Movement 1"},
            )],
            stop_reason="tool_use",
        ))
        llm.queue_response(LLMResponse(
            content="Created 1 movement and handed off to PC.",
            stop_reason="end_turn",
        ))

        events = []
        result = run_agent(
            db, ed_session.id, llm, executor,
            f"Root segment ID: {root.id}. Create movements.",
            on_event=events.append,
            keep_alive=True,
        )

        assert result.status == "completed"
        assert len(result.tool_calls_made) == 2
        assert result.tool_calls_made[0]["tool"] == "create_segment"
        assert result.tool_calls_made[1]["tool"] == "handoff"
        # Check phase state was recorded
        assert result.phase_state is not None

    def test_tech_submits_work(self, db):
        """Test that a tech can pick up a rep and submit work."""
        corps = create_corps(db, "test-corps")
        sessions = initialize_corps(db, corps.id)

        llm = MockLLMClient()
        registry = create_tool_registry()
        executor = ToolExecutor(registry)

        # Create segment + rep
        from backend.services.segment_service import create_segment
        from backend.services.rep_service import create_rep
        from backend.models.segment import SegmentType
        root = create_segment(db, type=SegmentType.SHOW, title="Test")
        mvmt = create_segment(db, type=SegmentType.MOVEMENT, title="Movement 1", parent_id=root.id)
        sset = create_segment(db, type=SegmentType.SET, title="Set 1", parent_id=mvmt.id)
        coord = create_segment(db, type=SegmentType.SEGMENT, title="Task 1", parent_id=sset.id)
        rep = create_rep(db, coord.id)

        tech_session = sessions["brass_tech"]

        # Queue: tech transitions rep, does work, submits
        llm.queue_response(LLMResponse(
            content="",
            tool_calls=[ToolCall(
                tool_name="transition_rep",
                arguments={"rep_id": rep.id, "new_status": "assigned"},
            )],
            stop_reason="tool_use",
        ))
        llm.queue_response(LLMResponse(
            content="",
            tool_calls=[ToolCall(
                tool_name="transition_rep",
                arguments={"rep_id": rep.id, "new_status": "in_progress"},
            )],
            stop_reason="tool_use",
        ))
        llm.queue_response(LLMResponse(
            content="",
            tool_calls=[ToolCall(
                tool_name="submit_work",
                arguments={"rep_id": rep.id, "result": "The answer is 42."},
            )],
            stop_reason="tool_use",
        ))
        llm.queue_response(LLMResponse(
            content="Work submitted successfully.",
            stop_reason="end_turn",
        ))

        result = run_agent(
            db, tech_session.id, llm, executor,
            f"Segment ID: {coord.id}. Do the work.",
            keep_alive=True,
        )

        assert result.status == "completed"
        assert len(result.tool_calls_made) == 3

        # Verify rep is now in review
        from backend.models.rep import Rep
        updated_rep = db.get(Rep, rep.id)
        assert updated_rep.status.value == "review"
        assert updated_rep.result == "The answer is 42."

    def test_failure_fingerprint_blocks_retry(self, db):
        """Test that repeated identical failures get blocked."""
        corps = create_corps(db, "test-corps")
        sessions = initialize_corps(db, corps.id)

        llm = MockLLMClient()
        registry = create_tool_registry()
        executor = ToolExecutor(registry)

        tech_session = sessions["brass_tech"]

        # Queue: tech tries to transition a nonexistent rep 3 times, then gives up
        for _ in range(3):
            llm.queue_response(LLMResponse(
                content="",
                tool_calls=[ToolCall(
                    tool_name="transition_rep",
                    arguments={"rep_id": "nonexistent", "new_status": "assigned"},
                )],
                stop_reason="tool_use",
            ))
        llm.queue_response(LLMResponse(
            content="Could not find the rep.",
            stop_reason="end_turn",
        ))

        result = run_agent(
            db, tech_session.id, llm, executor,
            "Transition rep nonexistent",
            keep_alive=True,
        )

        assert result.status == "completed"
        # Third call should have been blocked by fingerprint
        assert len(result.tool_calls_made) == 3
        # The third result should contain the fingerprint guidance
        third_result = result.tool_calls_made[2]["result"]
        assert not third_result["success"]
        assert "FAILURE PATTERN" in third_result.get("error", "")
