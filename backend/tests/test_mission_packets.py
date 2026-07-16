import pytest

from backend.services.agent_lifecycle import create_definition, spawn_session
from backend.services.mission_packet_service import (
    MissionScopeViolation,
    assert_tool_call_in_scope,
    create_mission_packet,
)
from backend.services.tool_executor import ToolExecutor, ToolRegistry


def test_mission_packet_records_narrow_assignment(db):
    definition = create_definition(
        db,
        role="visual_caption_head",
        system_prompt="Stay in visual scope.",
        tools_allowed=["submit_handoff", "update_rehearsal_block"],
    )
    session = spawn_session(db, definition.id, corps_id="corps-1")

    packet = create_mission_packet(
        db,
        session_id=session.id,
        corps_id="corps-1",
        role="visual_caption_head",
        phase="visual_block",
        target_type="rehearsal_block",
        target_id="block-1",
        allowed_tools=["submit_handoff", "update_rehearsal_block"],
        forbidden_scope=["music_block", "staffing", "unassigned_reps"],
        completion_criteria="Submit one visual-block rehearsal summary for block-1.",
        handoff_target="program_coordinator",
    )

    assert packet.session_id == session.id
    assert packet.target_type == "rehearsal_block"
    assert packet.target_id == "block-1"
    assert packet.completion_criteria == "Submit one visual-block rehearsal summary for block-1."


def test_tool_call_outside_allowed_tools_is_blocked(db):
    definition = create_definition(
        db,
        role="visual_caption_head",
        system_prompt="Stay in visual scope.",
        tools_allowed=["submit_handoff", "update_rehearsal_block"],
    )
    session = spawn_session(db, definition.id, corps_id="corps-1")
    create_mission_packet(
        db,
        session_id=session.id,
        corps_id="corps-1",
        role="visual_caption_head",
        phase="visual_block",
        target_type="rehearsal_block",
        target_id="block-1",
        allowed_tools=["update_rehearsal_block"],
        forbidden_scope=["music_block"],
        completion_criteria="Update block-1 only.",
        handoff_target=None,
    )

    with pytest.raises(MissionScopeViolation, match="Tool submit_handoff is not allowed"):
        assert_tool_call_in_scope(
            db,
            session_id=session.id,
            tool_name="submit_handoff",
            arguments={"target_id": "block-1"},
        )


def test_tool_call_against_wrong_target_is_blocked(db):
    definition = create_definition(
        db,
        role="percussion_caption_head",
        system_prompt="Stay in music scope.",
        tools_allowed=["update_rep"],
    )
    session = spawn_session(db, definition.id, corps_id="corps-1")
    create_mission_packet(
        db,
        session_id=session.id,
        corps_id="corps-1",
        role="percussion_caption_head",
        phase="music_block",
        target_type="rep",
        target_id="rep-1",
        allowed_tools=["update_rep"],
        forbidden_scope=["visual_block", "show_design"],
        completion_criteria="Update rep-1 only.",
        handoff_target="music_judge",
    )

    with pytest.raises(MissionScopeViolation, match="Target rep-2 is outside mission scope"):
        assert_tool_call_in_scope(
            db,
            session_id=session.id,
            tool_name="update_rep",
            arguments={"rep_id": "rep-2"},
        )


def test_tool_executor_returns_structured_scope_blocker(db):
    definition = create_definition(
        db,
        role="percussion_caption_head",
        system_prompt="Stay in music scope.",
        tools_allowed=["update_rep"],
    )
    session = spawn_session(db, definition.id, corps_id="corps-1")
    create_mission_packet(
        db,
        session_id=session.id,
        corps_id="corps-1",
        role="percussion_caption_head",
        phase="music_block",
        target_type="rep",
        target_id="rep-1",
        allowed_tools=["update_rep"],
        forbidden_scope=["visual_block", "show_design"],
        completion_criteria="Update rep-1 only.",
        handoff_target="music_judge",
    )
    registry = ToolRegistry()
    registry.register("update_rep", lambda rep_id: {"rep_id": rep_id})
    executor = ToolExecutor(registry)

    result = executor.execute(db, session.id, "update_rep", {"rep_id": "rep-2"})

    assert result.success is False
    assert result.output["blocked"] is True
    assert result.output["blocker_code"] == "mission_scope_violation"
