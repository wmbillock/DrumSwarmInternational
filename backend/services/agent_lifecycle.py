import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from backend.models.agent_definition import (
    AgentDefinition,
    MAJOR_CHANGE_FIELDS,
    ModelTier,
)
from backend.models.agent_session import AgentSession, SessionStatus, TERMINAL_STATUSES


class InvalidSessionTransition(Exception):
    pass


class PermissionDenied(Exception):
    pass


class ApprovalRequired(Exception):
    pass


# --- Agent Definition Management ---


SUPERVISORY_SINGLETON_ROLES = {
    "executive_director",
    "program_coordinator",
    "drum_major",
    "brass_caption_head",
    "percussion_caption_head",
    "guard_caption_head",
    "visual_caption_head",
}


def create_definition(
    db: Session,
    role: str,
    system_prompt: str,
    model_tier: ModelTier = ModelTier.SONNET,
    tools_allowed: Optional[list[str]] = None,
    corps_id: Optional[str] = None,
    nickname: Optional[str] = None,
) -> AgentDefinition:
    # Enforce one supervisory agent per caption per corps
    if role in SUPERVISORY_SINGLETON_ROLES and corps_id:
        existing = (
            db.query(AgentDefinition)
            .filter(AgentDefinition.role == role,
                    AgentDefinition.corps_id == corps_id,
                    AgentDefinition.version >= 0)  # version -1 = retired
            .first()
        )
        if existing:
            raise ValueError(
                f"Corps {corps_id} already has a {role} "
                f"(definition {existing.id}). Only one is allowed."
            )

    defn = AgentDefinition(
        role=role,
        system_prompt=system_prompt,
        model_tier=model_tier,
        tools_allowed=",".join(tools_allowed) if tools_allowed else "",
        corps_id=corps_id,
        nickname=nickname,
    )
    db.add(defn)
    db.commit()
    db.refresh(defn)
    return defn


def modify_definition(
    db: Session,
    definition_id: str,
    modified_by_session_id: str,
    changes: dict,
    approved: bool = False,
) -> AgentDefinition:
    """Modify an agent definition with tiered approval.

    Minor changes (system_prompt) are free.
    Major changes (tools_allowed, model_tier) require approved=True.
    """
    defn = db.get(AgentDefinition, definition_id)
    if defn is None:
        raise ValueError(f"Definition {definition_id} not found")

    # Check if any changes require approval
    major_changes = set(changes.keys()) & MAJOR_CHANGE_FIELDS
    if major_changes and not approved:
        raise ApprovalRequired(
            f"Changes to {major_changes} require caption head approval"
        )

    for field, value in changes.items():
        if field == "tools_allowed" and isinstance(value, list):
            value = ",".join(value)
        setattr(defn, field, value)

    defn.version += 1
    defn.modified_by = modified_by_session_id
    db.commit()
    db.refresh(defn)
    return defn


def get_definition(db: Session, definition_id: str) -> Optional[AgentDefinition]:
    return db.get(AgentDefinition, definition_id)


# --- Agent Session Lifecycle ---


def spawn_session(
    db: Session,
    definition_id: str,
    corps_id: str,
    parent_session_id: Optional[str] = None,
) -> AgentSession:
    defn = db.get(AgentDefinition, definition_id)
    if defn is None:
        raise ValueError(f"Definition {definition_id} not found")

    if parent_session_id is not None:
        parent = db.get(AgentSession, parent_session_id)
        if parent is None:
            raise ValueError(f"Parent session {parent_session_id} not found")

    session = AgentSession(
        definition_id=definition_id,
        corps_id=corps_id,
        parent_session_id=parent_session_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Record metrics event
    try:
        from backend.services.metrics import record_event, MetricType
        record_event(
            db, MetricType.AGENT_SESSION_STARTED,
            corps_id=corps_id, session_id=session.id,
            agent_role=defn.role,
        )
    except Exception:
        pass  # metrics are best-effort

    return session


def complete_session(
    db: Session,
    session_id: str,
    context_snapshot: Optional[str] = None,
) -> AgentSession:
    return _terminate_session(
        db, session_id, SessionStatus.COMPLETED, context_snapshot=context_snapshot
    )


def fail_session(
    db: Session,
    session_id: str,
    error: Optional[str] = None,
    context_snapshot: Optional[str] = None,
) -> AgentSession:
    return _terminate_session(
        db, session_id, SessionStatus.FAILED, error=error, context_snapshot=context_snapshot
    )


def timeout_session(
    db: Session,
    session_id: str,
    context_snapshot: Optional[str] = None,
) -> AgentSession:
    return _terminate_session(
        db, session_id, SessionStatus.TIMED_OUT, context_snapshot=context_snapshot
    )


def _terminate_session(
    db: Session,
    session_id: str,
    new_status: SessionStatus,
    error: Optional[str] = None,
    context_snapshot: Optional[str] = None,
) -> AgentSession:
    session = db.get(AgentSession, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    if session.status in TERMINAL_STATUSES:
        raise InvalidSessionTransition(
            f"Session already in terminal state {session.status.value}"
        )

    if session.status != SessionStatus.ACTIVE:
        raise InvalidSessionTransition(
            f"Cannot transition from {session.status.value} to {new_status.value}"
        )

    session.status = new_status
    session.ended_at = datetime.now(timezone.utc)
    if error is not None:
        session.error = error
    if context_snapshot is not None:
        session.context_snapshot = context_snapshot
    db.commit()
    db.refresh(session)

    # Record metrics event
    try:
        from backend.services.metrics import record_event, MetricType
        mt = (MetricType.AGENT_SESSION_COMPLETED if new_status == SessionStatus.COMPLETED
              else MetricType.AGENT_SESSION_FAILED)
        role_type = session.definition.role if session.definition else "unknown"
        duration = None
        if session.started_at and session.ended_at:
            duration = (session.ended_at - session.started_at).total_seconds()
        record_event(
            db, mt, corps_id=session.corps_id, session_id=session.id,
            agent_role=role_type, value=duration, unit="seconds",
        )
    except Exception:
        pass  # metrics are best-effort

    try:
        from backend.models.capability_ledger import LedgerEntryType
        from backend.services.capability_ledger_service import record_entry
        from backend.services.achievement_detector import check_performer_achievements, check_corps_achievements
        from backend.models.performer import Performer
        from backend.models.corps import Corps

        entry_type = None
        if new_status == SessionStatus.COMPLETED:
            entry_type = LedgerEntryType.SESSION_COMPLETED
        elif new_status in (SessionStatus.FAILED, SessionStatus.TIMED_OUT):
            entry_type = LedgerEntryType.SESSION_FAILED

        role_type = session.definition.role if session.definition else "unknown"
        performer_name = None
        performer = None
        if session.performer_id:
            performer = db.get(Performer, session.performer_id)
            if performer:
                performer_name = performer.name

        if entry_type:
            record_entry(
                db,
                role_type=role_type,
                entry_type=entry_type,
                performer_id=session.performer_id,
                performer_name=performer_name,
                corps_id=session.corps_id,
                session_id=session.id,
            )

        # Update performer trust score and session counters
        if performer:
            try:
                from backend.services.performer_service import record_session_completion
                success = new_status == SessionStatus.COMPLETED
                record_session_completion(db, performer.id, success)
            except Exception as exc:
                logger.debug("Failed to record session completion for performer %s: %s", performer.id, exc)

            check_performer_achievements(
                db,
                performer.id,
                performer.name,
                corps_id=session.corps_id,
                role_type=performer.role_type,
            )

        corps = db.get(Corps, session.corps_id)
        if corps:
            check_corps_achievements(db, corps.id, corps.name)
    except Exception:
        pass
    return session


def cascade_fail_children(
    db: Session,
    parent_session_id: str,
    error: str = "parent session terminated",
) -> int:
    """Transition all ACTIVE child sessions to FAILED when parent dies.

    Delegates to session_guard.cascade_fail_children for the actual logic.
    Returns the number of children cascade-failed.
    """
    from backend.services.session_guard import cascade_fail_children as _cascade
    return _cascade(db, parent_session_id, error=error)


def is_alive(db: Session, session_id: str) -> bool:
    session = db.get(AgentSession, session_id)
    if session is None:
        return False
    return session.status == SessionStatus.ACTIVE


def get_children(db: Session, session_id: str) -> list[AgentSession]:
    return (
        db.query(AgentSession)
        .filter(AgentSession.parent_session_id == session_id)
        .all()
    )


def check_tool_permission(db: Session, session_id: str, tool_name: str) -> bool:
    """Check if a session's definition allows a specific tool."""
    session = db.get(AgentSession, session_id)
    if session is None:
        return False
    defn = db.get(AgentDefinition, session.definition_id)
    if defn is None:
        return False
    return tool_name in defn.tools_allowed_list
