from typing import Optional

from sqlalchemy import case
from sqlalchemy.orm import Session

from backend.models.message import (
    Message,
    MessagePriority,
    MessageType,
    PRIORITY_ORDER,
)


# Role hierarchy — defines the valid communication paths.
# Key: role, Value: set of roles this role can send messages to.
# Roles not listed here cannot send messages at all.
ROLE_HIERARCHY = {
    # Administrative
    "executive_director": {
        "program_coordinator",
        "drill_writer",
        "music_writer",
        "choreographer",
        "brass_caption_head",
        "percussion_caption_head",
        "guard_caption_head",
        "visual_caption_head",
        "drum_major",
    },
    # Design staff
    "program_coordinator": {
        "executive_director",
        "drill_writer",
        "music_writer",
        "choreographer",
        "brass_caption_head",
        "percussion_caption_head",
        "guard_caption_head",
        "visual_caption_head",
        "drum_major",
    },
    "drill_writer": {"program_coordinator", "visual_caption_head"},
    "music_writer": {"program_coordinator", "brass_caption_head", "percussion_caption_head"},
    "choreographer": {"program_coordinator", "guard_caption_head"},
    # Caption heads
    "brass_caption_head": {
        "program_coordinator",
        "percussion_caption_head",
        "guard_caption_head",
        "visual_caption_head",
        "brass_tech",
        "drum_major",
    },
    "percussion_caption_head": {
        "program_coordinator",
        "brass_caption_head",
        "guard_caption_head",
        "visual_caption_head",
        "percussion_tech",
        "front_ensemble_tech",
        "drum_major",
    },
    "guard_caption_head": {
        "program_coordinator",
        "brass_caption_head",
        "percussion_caption_head",
        "visual_caption_head",
        "guard_tech",
        "drum_major",
    },
    "visual_caption_head": {
        "program_coordinator",
        "brass_caption_head",
        "percussion_caption_head",
        "guard_caption_head",
        "visual_tech",
        "drum_major",
    },
    # Drum major — liaison between staff and performers
    "drum_major": {
        "program_coordinator",
        "brass_caption_head",
        "percussion_caption_head",
        "guard_caption_head",
        "visual_caption_head",
        "horn_sergeant",
        "center_snare",
        "guard_captain",
    },
    # Techs
    "brass_tech": {"brass_caption_head", "section_leader", "performer"},
    "percussion_tech": {"percussion_caption_head", "section_leader", "performer"},
    "front_ensemble_tech": {"percussion_caption_head", "section_leader", "performer"},
    "guard_tech": {"guard_caption_head", "section_leader", "performer"},
    "visual_tech": {"visual_caption_head", "section_leader", "performer"},
    # Caption lead performers
    "horn_sergeant": {"drum_major", "brass_caption_head", "section_leader"},
    "center_snare": {"drum_major", "percussion_caption_head", "section_leader"},
    "guard_captain": {"drum_major", "guard_caption_head", "section_leader"},
    # Section leaders
    "section_leader": {"horn_sergeant", "center_snare", "guard_captain", "brass_tech", "percussion_tech", "front_ensemble_tech", "guard_tech", "visual_tech", "performer"},
    # Performers — can only report up
    "performer": {"section_leader"},
    # Timing & Penalties Judge — oversight and monitoring role
    "timing_judge": {"executive_director", "drum_major"},
}

# System role can send to any role (used by subscriptions, metronome, etc.)
# Added after dict construction to avoid forward reference
ROLE_HIERARCHY["system"] = set(ROLE_HIERARCHY.keys())

# User can direct message any staff/leadership role
ROLE_HIERARCHY["user"] = {
    "executive_director", "program_coordinator", "drum_major",
    "drill_writer", "music_writer", "choreographer",
    "brass_caption_head", "percussion_caption_head",
    "guard_caption_head", "visual_caption_head",
}

# Message types restricted by role category
# Directives can only come from staff/leadership, not performers
DIRECTIVE_ALLOWED_ROLES = {
    "user",
    "executive_director",
    "program_coordinator",
    "drill_writer",
    "music_writer",
    "choreographer",
    "brass_caption_head",
    "percussion_caption_head",
    "guard_caption_head",
    "visual_caption_head",
    "drum_major",
    "timing_judge",
}


class InvalidMessagePath(Exception):
    pass


class InvalidMessageType(Exception):
    pass


def send_message(
    db: Session,
    corps_id: str,
    from_role: str,
    type: MessageType,
    subject: str,
    body: Optional[str] = None,
    to_role: Optional[str] = None,
    to_session_id: Optional[str] = None,
    from_session_id: Optional[str] = None,
    priority: MessagePriority = MessagePriority.NORMAL,
    segment_id: Optional[str] = None,
) -> Message:
    # Validate the sender role exists in hierarchy
    if from_role not in ROLE_HIERARCHY:
        raise InvalidMessagePath(f"Unknown sender role: {from_role}")

    # Validate message type permissions
    if type == MessageType.DIRECTIVE and from_role not in DIRECTIVE_ALLOWED_ROLES:
        raise InvalidMessageType(
            f"Role {from_role} cannot send directives"
        )

    # Validate the communication path if a target role is specified
    if to_role is not None:
        allowed_targets = ROLE_HIERARCHY.get(from_role, set())
        if to_role not in allowed_targets:
            raise InvalidMessagePath(
                f"Role {from_role} cannot message {to_role}"
            )

    msg = Message(
        corps_id=corps_id,
        from_role=from_role,
        from_session_id=from_session_id,
        to_role=to_role,
        to_session_id=to_session_id,
        type=type,
        priority=priority,
        subject=subject,
        body=body,
        segment_id=segment_id,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def poll_messages(
    db: Session,
    corps_id: str,
    role: Optional[str] = None,
    session_id: Optional[str] = None,
    unacknowledged_only: bool = True,
) -> list[Message]:
    """Poll messages for a role or session, ordered by priority then creation time."""
    query = db.query(Message).filter(Message.corps_id == corps_id)

    if unacknowledged_only:
        query = query.filter(Message.acknowledged_at.is_(None))

    if session_id is not None:
        query = query.filter(
            (Message.to_session_id == session_id)
            | (Message.to_session_id.is_(None))
        )

    if role is not None:
        query = query.filter(
            (Message.to_role == role)
            | (Message.to_role.is_(None))  # broadcasts
        )

    # Order by priority (critical first), then by creation time
    priority_ordering = case(
        (Message.priority == MessagePriority.CRITICAL, 0),
        (Message.priority == MessagePriority.HIGH, 1),
        (Message.priority == MessagePriority.NORMAL, 2),
        (Message.priority == MessagePriority.LOW, 3),
        else_=99,
    )
    query = query.order_by(priority_ordering, Message.created_at)

    return query.all()


def acknowledge_message(db: Session, message_id: str) -> Message:
    from datetime import datetime, timezone

    msg = db.get(Message, message_id)
    if msg is None:
        raise ValueError(f"Message {message_id} not found")
    msg.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    return msg
