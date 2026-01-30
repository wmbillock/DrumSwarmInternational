"""Corps orchestration — initialization, tour mode, handoff chain, escalation,
merge monitor, rehearsal modes."""

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_definition import AgentDefinition, ModelTier
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.corps import Corps, CorpsStatus, RehearsalMode
from backend.models.coordinate import Coordinate, CoordinateStatus, CoordinateType
from backend.models.rep import Rep, RepStatus
from backend.services.agent_lifecycle import create_definition, spawn_session
from backend.services.message_service import (
    ROLE_HIERARCHY,
    send_message,
    MessageType,
    MessagePriority,
    InvalidMessagePath,
)


class CorpsError(Exception):
    pass


class InvalidHandoff(Exception):
    pass


class EscalationRequired(Exception):
    pass


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
]

# Handoff chain: design → caption head → tech → performer
# Maps who can hand off work to whom
HANDOFF_CHAIN = {
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


def create_corps(db: Session, name: str, show_id: Optional[str] = None) -> Corps:
    corps = Corps(name=name, show_id=show_id)
    db.add(corps)
    db.commit()
    db.refresh(corps)
    return corps


def initialize_corps(db: Session, corps_id: str) -> dict[str, AgentSession]:
    """Spawn the full hierarchy from definitions, returning role→session map."""
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")

    sessions: dict[str, AgentSession] = {}

    for role, tier, parent_role in CORPS_HIERARCHY:
        defn = create_definition(
            db, role=role,
            system_prompt=f"You are the {role} for this corps.",
            model_tier=tier,
            corps_id=corps_id,
        )
        parent_session_id = sessions[parent_role].id if parent_role else None
        session = spawn_session(
            db, definition_id=defn.id, corps_id=corps_id,
            parent_session_id=parent_session_id,
        )
        sessions[role] = session

    corps.status = CorpsStatus.REHEARSAL
    db.commit()
    return sessions


def start_tour(db: Session, corps_id: str) -> Corps:
    """Enable tour mode — remove human approval gates."""
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    if corps.status not in (CorpsStatus.REHEARSAL, CorpsStatus.TOUR):
        raise CorpsError(f"Cannot start tour from {corps.status.value}")
    corps.tour_mode = True
    corps.status = CorpsStatus.TOUR
    db.commit()
    db.refresh(corps)
    return corps


def stop_tour(db: Session, corps_id: str) -> Corps:
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    corps.tour_mode = False
    corps.status = CorpsStatus.REHEARSAL
    db.commit()
    db.refresh(corps)
    return corps


def set_rehearsal_mode(db: Session, corps_id: str, mode: RehearsalMode) -> Corps:
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    if corps.status not in (CorpsStatus.REHEARSAL, CorpsStatus.TOUR):
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
    coordinate_id: Optional[str] = None,
) -> None:
    """Perform a handoff between roles in the chain."""
    if not validate_handoff(from_role, to_role):
        raise InvalidHandoff(f"{from_role} cannot hand off to {to_role}")
    send_message(
        db, corps_id=corps_id, from_role=from_role, to_role=to_role,
        type=MessageType.HANDOFF, subject=subject, body=body,
        coordinate_id=coordinate_id,
    )


def escalate(
    db: Session,
    corps_id: str,
    from_role: str,
    subject: str,
    body: Optional[str] = None,
    coordinate_id: Optional[str] = None,
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
        priority=MessagePriority.HIGH, coordinate_id=coordinate_id,
    )
    return target


@dataclass
class MergeResult:
    """Result of merge monitor checking completed reps for integration."""
    checked: int = 0
    merged: int = 0
    conflicts: int = 0
    merged_coordinate_ids: list[str] = field(default_factory=list)
    conflict_coordinate_ids: list[str] = field(default_factory=list)


def merge_monitor_check(db: Session, corps_id: str) -> MergeResult:
    """Corps-level process managing integration of completed reps.

    Checks coordinates with completed reps. If all sibling sets under a segment
    are completed, marks the parent as completed too.
    """
    result = MergeResult()

    # Find all coordinates that are completed (leaf sets with completed reps)
    completed_coords = (
        db.query(Coordinate)
        .filter(Coordinate.status == CoordinateStatus.COMPLETED)
        .all()
    )

    # Check parents for merge readiness
    parents_checked: set[str] = set()
    for coord in completed_coords:
        result.checked += 1
        if coord.parent_id and coord.parent_id not in parents_checked:
            parents_checked.add(coord.parent_id)
            parent = db.get(Coordinate, coord.parent_id)
            if parent is None:
                continue

            siblings = (
                db.query(Coordinate)
                .filter(Coordinate.parent_id == parent.id)
                .all()
            )
            all_done = all(s.status == CoordinateStatus.COMPLETED for s in siblings)
            any_failed = any(s.status == CoordinateStatus.FAILED for s in siblings)

            if all_done:
                parent.status = CoordinateStatus.COMPLETED
                db.commit()
                result.merged += 1
                result.merged_coordinate_ids.append(parent.id)
            elif any_failed:
                result.conflicts += 1
                result.conflict_coordinate_ids.append(parent.id)

    return result


def disband_corps(db: Session, corps_id: str) -> Corps:
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    corps.status = CorpsStatus.DISBANDED
    corps.tour_mode = False
    db.commit()
    db.refresh(corps)
    return corps
