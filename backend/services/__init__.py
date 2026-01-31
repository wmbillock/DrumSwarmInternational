"""DCI Swarm — Service Layer."""

from backend.services.segment_service import (
    create_segment, get_segment, get_children, rollup_status,
)
from backend.services.rep_service import create_rep, transition_rep, get_reps_for_segment
from backend.services.agent_lifecycle import (
    create_definition, modify_definition, spawn_session,
    complete_session, fail_session, timeout_session, check_tool_permission,
)
from backend.services.message_service import send_message, poll_messages, acknowledge_message
from backend.services.scoring_service import (
    record_score, record_penalty, compute_composite, get_scores_for_rep,
)
from backend.services.corps_service import (
    create_corps, initialize_corps, start_tour, stop_tour,
    set_rehearsal_mode, validate_handoff, handoff, escalate,
    merge_monitor_check, disband_corps,
)
from backend.services.show_service import (
    create_show, get_show, list_shows, activate_show, complete_show, toggle_tour,
)
from backend.services.improvement import run_basics, run_critique, run_banquet
from backend.services.support_staff import create_support_staff_definitions, spawn_support_staff

__all__ = [
    "create_segment", "get_segment", "get_children", "rollup_status",
    "create_rep", "transition_rep", "get_reps_for_segment",
    "create_definition", "modify_definition", "spawn_session",
    "complete_session", "fail_session", "timeout_session", "check_tool_permission",
    "send_message", "poll_messages", "acknowledge_message",
    "record_score", "record_penalty", "compute_composite", "get_scores_for_rep",
    "create_corps", "initialize_corps", "start_tour", "stop_tour",
    "set_rehearsal_mode", "validate_handoff", "handoff", "escalate",
    "merge_monitor_check", "disband_corps",
    "create_show", "get_show", "list_shows", "activate_show", "complete_show", "toggle_tour",
    "run_basics", "run_critique", "run_banquet",
    "create_support_staff_definitions", "spawn_support_staff",
]
