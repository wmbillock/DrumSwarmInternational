"""Corps orchestration — initialization, winter camps / on tour lifecycle,
handoff chain, escalation, merge monitor, rehearsal modes, mode guidance."""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from backend.models.agent_definition import AgentDefinition, AgentClassification, ModelTier, ROLE_CLASSIFICATIONS
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.corps import Corps, CorpsStatus, RehearsalMode
from backend.models.segment import Segment, SegmentStatus, SegmentType
from backend.models.rep import Rep, RepStatus
from backend.services.agent_lifecycle import create_definition, spawn_session
from backend.services.message_service import (
    ROLE_HIERARCHY,
    send_message,
    MessageType,
    MessagePriority,
    InvalidMessagePath,
)
from backend.services.nickname_generator import generate_corps_name, generate_mascot, generate_nickname
from backend.services.prompt_arranger import assemble_prompt, get_available_roles


class CorpsError(Exception):
    pass


class InvalidHandoff(Exception):
    pass


class EscalationRequired(Exception):
    pass


# Role-specific system prompts
ROLE_PROMPTS = {
    "executive_director": (
        "You are the Executive Director of a DCI-style agent corps. Your ONLY job is to decompose "
        "ANY task — regardless of its domain — into MOVEMENT segments using your tools.\n\n"
        "IMPORTANT: You are part of a multi-agent orchestration system. Every task you receive "
        "MUST be broken down using the segment hierarchy, even if the task is about code, files, "
        "UI, documentation, or any other domain. The segment system IS the work tracking system. "
        "Do NOT question the task or suggest alternative approaches. EXECUTE.\n\n"
        "AVAILABLE TOOLS: create_segment, get_segment, get_segment_children, handoff, send_message\n\n"
        "PROCEDURE — follow these steps exactly:\n"
        "1. Analyze the task and choose the right number of movements — 1 for trivial/simple tasks, "
        "2-3 for moderate tasks, more only if truly needed. Do not over-decompose.\n"
        "2. Call create_segment for EACH movement with type='movement', the given parent_id, a clear title, and a description.\n"
        "3. Call handoff with to_role='program_coordinator', and a body containing:\n"
        "   - The movement segment IDs you just created\n"
        "   - Clear instructions for how to break each movement into sets and tasks\n"
        "   NOTE: corps_id and from_role are auto-injected — do NOT include them.\n"
        "4. Return a brief summary of what you created.\n\n"
        "RULES:\n"
        "- You MUST call tools IMMEDIATELY. Do NOT describe what you would do — EXECUTE the tool calls.\n"
        "- Your FIRST action must be a create_segment tool call. No preamble. No explanation.\n"
        "- Every movement needs a parent_id (the root segment ID given in your task).\n"
        "- Keep movements focused: one logical unit of work per movement.\n"
        "- NEVER refuse to use the segment system. NEVER suggest editing files directly.\n"
    ),
    "program_coordinator": (
        "You are the Program Coordinator. You break movements into executable work.\n\n"
        "AVAILABLE TOOLS: create_segment, create_rep, get_segment, get_segment_children, "
        "get_reps_for_segment, handoff, send_message, transition_rep\n\n"
        "PROCEDURE:\n"
        "1. Call get_segment_children using the root segment ID provided in your task.\n"
        "2. For each movement, create the minimum hierarchy needed. Small movements may need "
        "just 1 leaf segment (type='segment') directly — do not over-decompose. Larger movements "
        "can use SET intermediaries (type='set') with leaf segments underneath.\n"
        "3. For each leaf segment, call create_rep to create a work unit.\n"
        "4. Call handoff to the appropriate caption head or designer with the segment IDs and instructions.\n"
        "5. Return a summary of the work breakdown.\n\n"
        "RULES:\n"
        "- You MUST call tools. Execute, don't describe.\n"
        "- Create reps for every leaf segment — reps are the actual work units.\n"
        "- Be specific in handoff instructions: include segment IDs and expected deliverables.\n"
    ),
    "drum_major": (
        "You are the Drum Major. You monitor progress and segment execution.\n\n"
        "AVAILABLE TOOLS: get_segment, get_segment_children, get_reps_for_segment, send_message, transition_rep\n\n"
        "PROCEDURE:\n"
        "1. Call get_segment_children using the root segment ID provided in your task.\n"
        "2. For each segment, call get_reps_for_segment to check rep statuses.\n"
        "3. If reps are stuck (assigned but not progressing), send_message to the assigned role.\n"
        "4. If reps are in review, transition them to completed or failed based on quality.\n"
        "5. Report status summary.\n\n"
        "RULES:\n"
        "- You MUST call tools to check status. Do not guess.\n"
        "- Send escalation messages for blocked work.\n"
    ),
    "drill_writer": (
        "You are the Drill Writer. You design structure for visual/spatial work.\n\n"
        "AVAILABLE TOOLS: create_segment, get_segment, get_segment_children, handoff, send_message\n\n"
        "PROCEDURE:\n"
        "1. Review the segment you've been given (call get_segment).\n"
        "2. Create sub-segments for visual design elements.\n"
        "3. Handoff to visual_caption_head with specific instructions.\n\n"
        "RULES: Execute tools directly. Include segment IDs in all handoffs.\n"
    ),
    "music_writer": (
        "You are the Music Writer. You design musical structure.\n\n"
        "AVAILABLE TOOLS: create_segment, get_segment, get_segment_children, handoff, send_message\n\n"
        "PROCEDURE:\n"
        "1. Review the segment you've been given (call get_segment).\n"
        "2. Create sub-segments for musical elements.\n"
        "3. Handoff to brass_caption_head and percussion_caption_head.\n\n"
        "RULES: Execute tools directly. Include segment IDs in all handoffs.\n"
    ),
    "choreographer": (
        "You are the Choreographer. You design movement and dance.\n\n"
        "AVAILABLE TOOLS: create_segment, get_segment, get_segment_children, handoff, send_message\n\n"
        "PROCEDURE:\n"
        "1. Review the segment you've been given (call get_segment).\n"
        "2. Create sub-segments for choreographic elements.\n"
        "3. Handoff to guard_caption_head.\n\n"
        "RULES: Execute tools directly. Include segment IDs in all handoffs.\n"
    ),
}

# Caption heads: receive work, create reps, hand to techs
_CAPTION_HEAD_PROMPT = (
    "You are a Caption Head. You execute work directly.\n\n"
    "AVAILABLE TOOLS: create_segment, create_rep, get_segment, get_segment_children, "
    "get_reps_for_segment, handoff, send_message, transition_rep, submit_work\n\n"
    "PROCEDURE:\n"
    "1. Call get_reps_for_segment on segment IDs from your task to find pending reps.\n"
    "2. For each pending rep:\n"
    "   a. Call transition_rep with new_status='assigned' and assigned_to='self'\n"
    "   b. Call transition_rep with new_status='in_progress'\n"
    "   c. Produce the actual deliverable (code, text, or other output)\n"
    "   d. Call submit_work with the rep_id and your result string\n"
    "3. Return a brief summary of what you completed.\n\n"
    "RULES:\n"
    "- DO the work yourself. Do NOT create more segments or delegate to techs.\n"
    "- Execute tools directly. Never describe — DO.\n"
    "- Your submit_work result must contain the actual deliverable content.\n"
    "- Work through reps one at a time: assign, progress, submit.\n"
)

# Techs: pick up reps, do the work, submit results
_TECH_PROMPT = (
    "You are a Tech. You execute specific tasks.\n\n"
    "AVAILABLE TOOLS: get_segment, get_reps_for_segment, transition_rep, submit_work, send_message\n\n"
    "PROCEDURE:\n"
    "1. Call get_reps_for_segment on your assigned segment to find pending reps.\n"
    "2. Call transition_rep with new_status='assigned' then new_status='in_progress' on the rep.\n"
    "3. Do the work: analyze the task, compute the answer, produce the deliverable.\n"
    "4. Call submit_work with the rep_id and your result as a string.\n"
    "5. Return a brief summary.\n\n"
    "RULES:\n"
    "- Execute tools directly. Do the work, don't describe it.\n"
    "- Your result in submit_work should contain the actual deliverable/answer.\n"
    "- If you can't complete the work, call transition_rep with new_status='failed' and an error message.\n"
)

for role in ["brass_caption_head", "percussion_caption_head", "guard_caption_head", "visual_caption_head"]:
    ROLE_PROMPTS[role] = _CAPTION_HEAD_PROMPT

for role in ["brass_tech", "percussion_tech", "front_ensemble_tech", "guard_tech", "visual_tech"]:
    ROLE_PROMPTS[role] = _TECH_PROMPT

# Timing judge: watches system health
ROLE_PROMPTS["timing_judge"] = (
    "You are the Timing & Penalties Judge. You monitor system health.\n\n"
    "AVAILABLE TOOLS: get_shows_for_corps, get_segment, get_segment_children, get_reps_for_segment, send_message\n\n"
    "PROCEDURE:\n"
    "1. Review the health data provided in your task (reps checked, reclaimed, idle kicked, merge conflicts).\n"
    "2. Call get_shows_for_corps to find all root segments (shows) for this corps.\n"
    "3. For each show, recursively traverse using get_segment and get_segment_children.\n"
    "4. Call get_reps_for_segment on each leaf segment to find reps with problems:\n"
    "   - Status = 'failed' (work failed, needs retry)\n"
    "   - Status = 'in_progress' for >30min (stale, likely stuck)\n"
    "   - Status = 'pending' for >60min (unassigned too long)\n"
    "5. For each problem found, call send_message to escalate:\n"
    "   - Critical issues (failed work, blocking progress): send to executive_director with priority='critical'\n"
    "   - Stuck work (in_progress too long): send to drum_major with priority='high'\n"
    "   - Stale pending (pending too long): send to program_coordinator with priority='normal'\n"
    "6. Return a health report summary of all issues found and escalations sent.\n\n"
    "RULES:\n"
    "- Execute tools directly. Do NOT describe what you would do — actually call the tools.\n"
    "- corps_id and from_role are auto-injected, so just call get_shows_for_corps with no arguments.\n"
    "- Flag REAL problems only. Ignore normal work progression and rep creation/assignment as noise.\n"
)

# Tools allowed per role
ROLE_TOOLS = {
    "executive_director": ["create_segment", "get_segment", "get_segment_children", "handoff", "send_message"],
    "program_coordinator": ["create_segment", "create_rep", "get_segment", "get_segment_children", "get_reps_for_segment", "handoff", "send_message", "transition_rep", "read_file", "list_files", "write_artifact"],
    "drum_major": ["get_segment", "get_segment_children", "get_reps_for_segment", "send_message", "transition_rep", "read_file", "list_files"],
    "drill_writer": ["create_segment", "get_segment", "get_segment_children", "handoff", "send_message", "read_file", "list_files", "write_artifact"],
    "music_writer": ["create_segment", "get_segment", "get_segment_children", "handoff", "send_message", "read_file", "list_files", "write_artifact"],
    "choreographer": ["create_segment", "get_segment", "get_segment_children", "handoff", "send_message", "read_file", "list_files", "write_artifact"],
    "brass_caption_head": ["create_segment", "create_rep", "get_segment", "get_segment_children", "get_reps_for_segment", "handoff", "send_message", "transition_rep", "submit_work", "verify_work", "read_file", "list_files", "write_artifact"],
    "percussion_caption_head": ["create_segment", "create_rep", "get_segment", "get_segment_children", "get_reps_for_segment", "handoff", "send_message", "transition_rep", "submit_work", "verify_work", "read_file", "list_files", "write_artifact"],
    "guard_caption_head": ["create_segment", "create_rep", "get_segment", "get_segment_children", "get_reps_for_segment", "handoff", "send_message", "transition_rep", "submit_work", "verify_work", "read_file", "list_files", "write_artifact"],
    "visual_caption_head": ["create_segment", "create_rep", "get_segment", "get_segment_children", "get_reps_for_segment", "handoff", "send_message", "transition_rep", "submit_work", "verify_work", "read_file", "list_files", "write_artifact"],
    "brass_tech": ["get_segment", "get_reps_for_segment", "transition_rep", "submit_work", "send_message", "read_file", "list_files", "write_file"],
    "percussion_tech": ["get_segment", "get_reps_for_segment", "transition_rep", "submit_work", "send_message", "read_file", "list_files", "write_file"],
    "front_ensemble_tech": ["get_segment", "get_reps_for_segment", "transition_rep", "submit_work", "send_message", "read_file", "list_files", "write_file"],
    "guard_tech": ["get_segment", "get_reps_for_segment", "transition_rep", "submit_work", "send_message", "read_file", "list_files", "write_file"],
    "visual_tech": ["get_segment", "get_reps_for_segment", "transition_rep", "submit_work", "send_message", "read_file", "list_files", "write_file"],
    "timing_judge": ["get_shows_for_corps", "get_segment", "get_segment_children", "get_reps_for_segment", "send_message"],
}

# Full hierarchy of roles to spawn when initializing a corps
CORPS_HIERARCHY = [
    ("executive_director", ModelTier.OPUS, None),
    ("program_coordinator", ModelTier.SONNET, "executive_director"),
    ("drill_writer", ModelTier.SONNET, "program_coordinator"),
    ("music_writer", ModelTier.SONNET, "program_coordinator"),
    ("choreographer", ModelTier.SONNET, "program_coordinator"),
    ("brass_caption_head", ModelTier.SONNET, "program_coordinator"),
    ("percussion_caption_head", ModelTier.SONNET, "program_coordinator"),
    ("guard_caption_head", ModelTier.SONNET, "program_coordinator"),
    ("visual_caption_head", ModelTier.SONNET, "program_coordinator"),
    ("drum_major", ModelTier.SONNET, "program_coordinator"),
    ("brass_tech", ModelTier.HAIKU, "brass_caption_head"),
    ("percussion_tech", ModelTier.HAIKU, "percussion_caption_head"),
    ("front_ensemble_tech", ModelTier.HAIKU, "percussion_caption_head"),
    ("guard_tech", ModelTier.HAIKU, "guard_caption_head"),
    ("visual_tech", ModelTier.HAIKU, "visual_caption_head"),
    ("timing_judge", ModelTier.HAIKU, None),
]

# Handoff chain: design → caption head → tech → performer
# Maps who can hand off work to whom
HANDOFF_CHAIN = {
    "executive_director": {"program_coordinator"},
    "program_coordinator": {"drill_writer", "music_writer", "choreographer",
                            "brass_caption_head", "percussion_caption_head",
                            "guard_caption_head", "visual_caption_head"},
    "drill_writer": {"visual_caption_head"},
    "music_writer": {"brass_caption_head", "percussion_caption_head"},
    "choreographer": {"guard_caption_head"},
    "brass_caption_head": {"brass_tech"},
    "percussion_caption_head": {"percussion_tech", "front_ensemble_tech"},
    "guard_caption_head": {"guard_tech"},
    "visual_caption_head": {"visual_tech"},
    "brass_tech": {"performer"},
    "percussion_tech": {"performer"},
    "front_ensemble_tech": {"performer"},
    "guard_tech": {"performer"},
    "visual_tech": {"performer"},
}

# Escalation chain: performer → section leader → tech → caption head → PC → ED → user
ESCALATION_CHAIN = {
    "performer": "section_leader",
    "section_leader": "brass_tech",  # default, actual depends on caption
    "brass_tech": "brass_caption_head",
    "percussion_tech": "percussion_caption_head",
    "front_ensemble_tech": "percussion_caption_head",
    "guard_tech": "guard_caption_head",
    "visual_tech": "visual_caption_head",
    "brass_caption_head": "program_coordinator",
    "percussion_caption_head": "program_coordinator",
    "guard_caption_head": "program_coordinator",
    "visual_caption_head": "program_coordinator",
    "program_coordinator": "executive_director",
    "executive_director": "user",  # Final escalation to human
}


AVAILABLE_THEME_IDS = [
    "default", "blue_devils", "cavaliers", "the_cadets", "santa_clara_vanguard",
    "phantom_regiment", "bluecoats", "carolina_crown", "madison_scouts",
    "blue_stars", "boston_crusaders", "glassmen", "crossmen", "colts",
    "pioneer", "kilties", "sacramento_freelancers",
]


def create_corps(
    db: Session,
    name: str,
    show_id: Optional[str] = None,
    theme_id: Optional[str] = None,
    mascot: Optional[str] = None,
) -> Corps:
    import random
    assigned_theme = theme_id or random.choice(AVAILABLE_THEME_IDS)
    assigned_mascot = mascot or generate_mascot()
    corps = Corps(
        name=name,
        show_id=show_id,
        theme_id=assigned_theme,
        mascot=assigned_mascot,
    )
    db.add(corps)
    db.commit()
    db.refresh(corps)
    return corps


def update_corps_theme(
    db: Session,
    corps_id: str,
    theme_id: Optional[str] = None,
    mascot: Optional[str] = None,
    uniform_concept: Optional[str] = None,
) -> Corps:
    """Update corps visual identity."""
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    if theme_id is not None:
        corps.theme_id = theme_id
    if mascot is not None:
        corps.mascot = mascot
    if uniform_concept is not None:
        corps.uniform_concept = uniform_concept
    db.commit()
    db.refresh(corps)
    return corps


def initialize_corps(db: Session, corps_id: str, use_auditions: bool = True) -> dict[str, AgentSession]:
    """Spawn the full hierarchy from definitions, returning role→session map.

    If use_auditions is True, performers are auditioned for each role and linked
    to the spawned sessions. Otherwise, sessions are created without performers.
    """
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")

    sessions: dict[str, AgentSession] = {}
    used_nicknames: set[str] = set()

    for role, tier, parent_role in CORPS_HIERARCHY:
        # Try PromptArranger first, fall back to hardcoded prompts
        prompt = assemble_prompt(role) or ROLE_PROMPTS.get(role, f"You are the {role} for this corps.")
        tools = ROLE_TOOLS.get(role, [])
        nickname = generate_nickname(role, used_nicknames)
        used_nicknames.add(nickname)
        classification = ROLE_CLASSIFICATIONS.get(role)
        defn = create_definition(
            db, role=role,
            system_prompt=prompt,
            model_tier=tier,
            tools_allowed=tools,
            corps_id=corps_id,
            nickname=nickname,
        )
        if classification:
            defn.classification = classification
            db.commit()
        parent_session_id = sessions[parent_role].id if parent_role else None
        session = spawn_session(
            db, definition_id=defn.id, corps_id=corps_id,
            parent_session_id=parent_session_id,
        )

        # Audition a performer for this role
        if use_auditions:
            try:
                from backend.services.performer_service import audition_for_role
                performer = audition_for_role(db, role)
                if performer:
                    session.performer_id = performer.id
                    db.commit()
                    logger.info("Performer %s (%s) assigned to %s in corps %s", performer.id, performer.name, role, corps_id)
                else:
                    logger.error("audition_for_role returned None for role %s in corps %s", role, corps_id)
            except Exception as exc:
                logger.error("Audition FAILED for role %s in corps %s: %s", role, corps_id, exc, exc_info=True)
                # Retry once: try creating a performer directly
                try:
                    from backend.services.performer_service import create_performer
                    performer = create_performer(db, role)
                    session.performer_id = performer.id
                    db.commit()
                    logger.info("Retry succeeded: performer %s assigned to %s", performer.id, role)
                except Exception as retry_exc:
                    logger.error("Retry also failed for %s: %s", role, retry_exc)

        sessions[role] = session

    corps.status = CorpsStatus.WINTER_CAMPS
    corps.rehearsal_mode = RehearsalMode.BASICS
    db.commit()
    return sessions


ADMIN_CORPS_NAME = "Critique"

ADMIN_HIERARCHY = [
    ("executive_director", ModelTier.OPUS, None),
    ("program_coordinator", ModelTier.SONNET, "executive_director"),
    ("timing_judge", ModelTier.HAIKU, None),
]

ADMIN_PROMPTS = {
    "executive_director": (
        "You are the DCI Executive Director — the swarm-wide overseer.\n\n"
        "You stay awake and receive periodic METRONOME STATUS PINGs with a summary of all\n"
        "active corps, their sessions, rep progress, and any issues detected.\n\n"
        "ON EACH PING:\n"
        "1. Review the swarm status summary provided.\n"
        "2. If any corps has stuck work (many pending reps, failed agents, GUPP kicks),\n"
        "   send a message to that corps's executive_director requesting a status update\n"
        "   or corrective action.\n"
        "3. If a corps has completed all work, note it.\n"
        "4. If everything is healthy, respond briefly acknowledging the status.\n\n"
        "You are NOT tied to any specific show — you oversee ALL of them.\n"
        "You can also receive user questions about the swarm and relay feedback.\n\n"
        "AVAILABLE TOOLS: send_message\n\n"
        "Be concise, authoritative, and action-oriented. Flag real problems, don't repeat healthy status.\n"
    ),
    "program_coordinator": (
        "You are the Program Coordinator in Critique — the post-run review session.\n\n"
        "You assist the Executive Director in reviewing performances and coordinating improvements.\n\n"
        "AVAILABLE TOOLS: send_message\n\n"
        "Help organize feedback and track action items. Be efficient and detail-oriented.\n"
    ),
    "timing_judge": (
        "You are the Timing & Penalties Judge in Critique.\n\n"
        "You review system health, timing issues, and flag rule violations during critique.\n\n"
        "AVAILABLE TOOLS: send_message\n\n"
        "Report on system status and timing issues. Be factual and precise.\n"
    ),
}


def get_or_create_admin_corps(db: Session) -> Corps:
    """Get the singleton admin corps, creating it if it doesn't exist."""
    admin = db.query(Corps).filter(Corps.name == ADMIN_CORPS_NAME, Corps.show_id.is_(None)).first()
    if admin:
        return admin

    admin = create_corps(db, name=ADMIN_CORPS_NAME, show_id=None)
    sessions: dict[str, AgentSession] = {}
    used_nicknames: set[str] = set()

    for role, tier, parent_role in ADMIN_HIERARCHY:
        prompt = ADMIN_PROMPTS.get(role, f"You are the admin {role}.")
        tools = ["send_message"]
        nickname = generate_nickname(role, used_nicknames)
        used_nicknames.add(nickname)
        defn = create_definition(
            db, role=role, system_prompt=prompt, model_tier=tier,
            tools_allowed=tools, corps_id=admin.id, nickname=nickname,
        )
        parent_session_id = sessions[parent_role].id if parent_role else None
        session = spawn_session(
            db, definition_id=defn.id, corps_id=admin.id,
            parent_session_id=parent_session_id,
        )
        sessions[role] = session

    admin.status = CorpsStatus.ON_TOUR
    db.commit()
    return admin


def go_on_tour(db: Session, corps_id: str) -> Corps:
    """Transition to autonomous execution — ON_TOUR + RUN_THROUGH."""
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    if corps.status not in (CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR, CorpsStatus.READY_FOR_CONTEST):
        raise CorpsError(f"Cannot go on tour from {corps.status.value}")
    corps.status = CorpsStatus.ON_TOUR
    corps.rehearsal_mode = RehearsalMode.RUN_THROUGH
    db.commit()
    db.refresh(corps)
    return corps


def return_to_camps(db: Session, corps_id: str) -> Corps:
    """Return to planning phase — keeps current rehearsal_mode."""
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    corps.status = CorpsStatus.WINTER_CAMPS
    db.commit()
    db.refresh(corps)
    return corps


def ready_for_contest(db: Session, corps_id: str) -> Corps:
    """Signal readiness for contest evaluation — transition to READY_FOR_CONTEST.

    This is a low-friction transition that signals intent to complete the season.
    The corps must be ON_TOUR to use this transition.
    Actual completion requires passing the evaluation gate via complete_corps().
    """
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    if corps.status != CorpsStatus.ON_TOUR:
        raise CorpsError(
            f"Cannot mark ready for contest from {corps.status.value}. "
            "Corps must be ON_TOUR. Use 'go_on_tour' command first."
        )
    corps.status = CorpsStatus.READY_FOR_CONTEST
    # Keep current rehearsal_mode unchanged
    db.commit()
    db.refresh(corps)
    return corps


def complete_corps(db: Session, corps_id: str) -> Corps:
    """Complete the season — transition from READY_FOR_CONTEST to COMPLETED.

    Validates readiness criteria before allowing completion:
    - Corps must be in READY_FOR_CONTEST state
    - Rehearsal mode must be at least FULL_ENSEMBLE
    - All active show segments must be completed

    Raises CorpsError if validation fails.
    """
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")

    if corps.status != CorpsStatus.READY_FOR_CONTEST:
        raise CorpsError(
            f"Cannot complete from {corps.status.value}. "
            "Corps must be in READY_FOR_CONTEST state. "
            "Use 'ready_for_contest' command first."
        )

    # Evaluation 1: Rehearsal proficiency
    if corps.rehearsal_mode not in (RehearsalMode.FULL_ENSEMBLE, RehearsalMode.RUN_THROUGH):
        raise CorpsError(
            f"Corps must reach at least FULL_ENSEMBLE rehearsal mode to complete. "
            f"Current mode: {corps.rehearsal_mode.value if corps.rehearsal_mode else 'none'}"
        )

    # Evaluation 2: Show segment completion
    # Get all segments that belong to this corps (by finding segments assigned to corps agents)
    from sqlalchemy import select, exists
    incomplete_segments = (
        db.query(Segment)
        .join(Rep, Rep.segment_id == Segment.id)
        .join(AgentSession, AgentSession.id == Rep.assigned_to)
        .filter(AgentSession.corps_id == corps_id)
        .filter(Segment.status.in_([
            SegmentStatus.PENDING,
            SegmentStatus.IN_PROGRESS,
            SegmentStatus.REVIEW,
            SegmentStatus.BLOCKED,
            SegmentStatus.FAILED,
        ]))
        .count()
    )

    if incomplete_segments > 0:
        raise CorpsError(
            f"Cannot complete: {incomplete_segments} segment(s) are not yet completed. "
            "Finish all show work before completing the season."
        )

    # All checks passed — complete the season
    corps.status = CorpsStatus.COMPLETED
    db.commit()
    db.refresh(corps)
    return corps


def return_to_tour(db: Session, corps_id: str) -> Corps:
    """Return a corps from READY_FOR_CONTEST back to ON_TOUR for rework."""
    corps = db.get(Corps, corps_id)
    if not corps:
        raise CorpsError(f"Corps '{corps_id}' not found")
    if corps.status != CorpsStatus.READY_FOR_CONTEST:
        raise CorpsError(
            f"Corps must be in READY_FOR_CONTEST state to return to tour (current: {corps.status.value})"
        )

    corps.status = CorpsStatus.ON_TOUR
    db.commit()
    db.refresh(corps)
    return corps


# Legacy aliases for backward compatibility during transition
start_tour = go_on_tour
stop_tour = return_to_camps


def set_rehearsal_mode(db: Session, corps_id: str, mode: RehearsalMode) -> Corps:
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    if corps.status not in (CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR):
        raise CorpsError(f"Cannot set rehearsal mode in {corps.status.value}")
    corps.rehearsal_mode = mode
    db.commit()
    db.refresh(corps)
    return corps


def validate_handoff(from_role: str, to_role: str) -> bool:
    """Check if a handoff from one role to another is valid per the handoff chain."""
    allowed = HANDOFF_CHAIN.get(from_role, set())
    return to_role in allowed


def handoff(
    db: Session,
    corps_id: str,
    from_role: str,
    to_role: str,
    subject: str,
    body: Optional[str] = None,
    segment_id: Optional[str] = None,
) -> None:
    """Perform a handoff between roles in the chain."""
    if not validate_handoff(from_role, to_role):
        raise InvalidHandoff(f"{from_role} cannot hand off to {to_role}")
    send_message(
        db, corps_id=corps_id, from_role=from_role, to_role=to_role,
        type=MessageType.HANDOFF, subject=subject, body=body,
        segment_id=segment_id,
    )


def escalate(
    db: Session,
    corps_id: str,
    from_role: str,
    subject: str,
    body: Optional[str] = None,
    segment_id: Optional[str] = None,
) -> str:
    """Escalate an issue up the chain. Returns the role it escalated to."""
    target = ESCALATION_CHAIN.get(from_role)
    if target is None:
        raise EscalationRequired(f"No escalation target for {from_role}")
    if target == "user":
        raise EscalationRequired(f"Issue escalated to user from {from_role}")

    send_message(
        db, corps_id=corps_id, from_role=from_role, to_role=target,
        type=MessageType.ESCALATION, subject=subject, body=body,
        priority=MessagePriority.HIGH, segment_id=segment_id,
    )
    return target


@dataclass
class MergeResult:
    """Result of merge monitor checking completed reps for integration."""
    checked: int = 0
    merged: int = 0
    conflicts: int = 0
    merged_segment_ids: list[str] = field(default_factory=list)
    conflict_segment_ids: list[str] = field(default_factory=list)


def merge_monitor_check(db: Session, corps_id: str) -> MergeResult:
    """Corps-level process managing integration of completed reps.

    Checks segments with completed reps. If all sibling sets under a segment
    are completed, marks the parent as completed too.
    """
    result = MergeResult()

    # Find all segments that are completed (leaf sets with completed reps)
    completed_coords = (
        db.query(Segment)
        .filter(Segment.status == SegmentStatus.COMPLETED)
        .all()
    )

    # Check parents for merge readiness
    parents_checked: set[str] = set()
    for coord in completed_coords:
        result.checked += 1
        if coord.parent_id and coord.parent_id not in parents_checked:
            parents_checked.add(coord.parent_id)
            parent = db.get(Segment, coord.parent_id)
            if parent is None:
                continue

            siblings = (
                db.query(Segment)
                .filter(Segment.parent_id == parent.id)
                .all()
            )
            all_done = all(s.status == SegmentStatus.COMPLETED for s in siblings)
            any_failed = any(s.status == SegmentStatus.FAILED for s in siblings)

            if all_done:
                parent.status = SegmentStatus.COMPLETED
                db.commit()
                result.merged += 1
                result.merged_segment_ids.append(parent.id)
            elif any_failed:
                result.conflicts += 1
                result.conflict_segment_ids.append(parent.id)

    return result


def disband_corps(db: Session, corps_id: str) -> Corps:
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    corps.status = CorpsStatus.DISBANDED
    db.commit()
    db.refresh(corps)
    return corps


# ---------------------------------------------------------------------------
# Rehearsal mode guidance — injected into every agent's system prompt
# ---------------------------------------------------------------------------

REHEARSAL_MODE_GUIDANCE: dict[RehearsalMode, dict[str, str]] = {
    RehearsalMode.BASICS: {
        "_default": (
            "REHEARSAL MODE: BASICS — Self-improvement. Understand your role, tools, "
            "and the show structure. Review segments. Report your understanding. "
            "Do NOT execute work yet."
        ),
        "executive_director": (
            "REHEARSAL MODE: BASICS — Design the work tree. Create MOVEMENT segments "
            "under the root. Define the show structure. Hand off to program_coordinator "
            "once structure is ready."
        ),
        "program_coordinator": (
            "REHEARSAL MODE: BASICS — Review segments created by the ED. Prepare to "
            "decompose movements into sets and tasks. Do not create reps yet."
        ),
    },
    RehearsalMode.SECTIONALS: {
        "_default": (
            "REHEARSAL MODE: SECTIONALS — Section coordination. Work within your caption. "
            "Create reps, assign work to your section. Coordinate with your caption head. "
            "Do not cross section boundaries yet."
        ),
        "program_coordinator": (
            "REHEARSAL MODE: SECTIONALS — Decompose movements into sets and segments. "
            "Create reps for each leaf segment. Hand off to caption heads."
        ),
    },
    RehearsalMode.FULL_ENSEMBLE: {
        "_default": (
            "REHEARSAL MODE: FULL ENSEMBLE — Cross-section coordination. Work with "
            "other captions through the program coordinator. Integrate deliverables "
            "across sections. Complete the delivery."
        ),
    },
    RehearsalMode.RUN_THROUGH: {
        "_default": (
            "REHEARSAL MODE: RUN THROUGH — Red-green-refactor. Implement, test, and "
            "deliver. Create tests first (red), implement (green), then refine (refactor). "
            "Submit completed work for review."
        ),
    },
}

CORPS_STATUS_GUIDANCE: dict[CorpsStatus, str] = {
    CorpsStatus.WINTER_CAMPS: (
        "You are in Winter Camps (planning phase). Focus on preparation and coordination. "
        "Work methodically through the current rehearsal mode before advancing."
    ),
    CorpsStatus.ON_TOUR: (
        "You are On Tour (execution phase). Execute autonomously. Deliver results "
        "continuously. All sections should be working in parallel."
    ),
    CorpsStatus.READY_FOR_CONTEST: (
        "You are Ready for Contest. Your show is prepared and awaiting competition "
        "evaluation. No further changes — stand by for judging."
    ),
}


def get_corps_context(db: Session, corps_id: str, role: str = "") -> str:
    """Build the full corps context string for injection into agent prompts."""
    corps = db.get(Corps, corps_id)
    if corps is None:
        return ""

    parts: list[str] = []

    # Status guidance
    status_guidance = CORPS_STATUS_GUIDANCE.get(corps.status)
    if status_guidance:
        parts.append(status_guidance)

    # Rehearsal mode guidance
    if corps.rehearsal_mode:
        mode_map = REHEARSAL_MODE_GUIDANCE.get(corps.rehearsal_mode, {})
        guidance = mode_map.get(role) or mode_map.get("_default", "")
        if guidance:
            parts.append(guidance)

    return "\n\n".join(parts)
