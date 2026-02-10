"""Shared session-by-role lookup with auto-respawn."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.agent_definition import AgentDefinition
from backend.services.agent_lifecycle import spawn_session

logger = logging.getLogger(__name__)


def find_session_for_role(
    db: Session,
    corps_id: str,
    role: str,
) -> Optional[AgentSession]:
    """Find the most relevant session for a role WITHOUT creating a new one.

    Returns an active session if one exists, otherwise the most recent
    terminal (completed/failed) session. Returns None if no session exists
    at all for this role in this corps.
    """
    # Try active first
    active = (
        db.query(AgentSession)
        .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
        .filter(
            AgentSession.corps_id == corps_id,
            AgentDefinition.role == role,
            AgentSession.status == SessionStatus.ACTIVE,
        )
        .first()
    )
    if active:
        return active

    # Return most recent terminal session (caller decides whether to respawn)
    return (
        db.query(AgentSession)
        .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
        .filter(
            AgentSession.corps_id == corps_id,
            AgentDefinition.role == role,
        )
        .order_by(AgentSession.started_at.desc())
        .first()
    )


def find_or_respawn_session(
    db: Session,
    corps_id: str,
    role: str,
) -> Optional[AgentSession]:
    """Find an active session for a role, or respawn from the most recent one.

    Returns the AgentSession object (callers can use .id if they only need the ID).
    Carries over context_snapshot from old sessions for continuity.
    """
    # Try active first
    active = (
        db.query(AgentSession)
        .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
        .filter(
            AgentSession.corps_id == corps_id,
            AgentDefinition.role == role,
            AgentSession.status == SessionStatus.ACTIVE,
        )
        .first()
    )
    if active:
        return active

    # Find most recent session (completed or failed) and respawn
    old = (
        db.query(AgentSession)
        .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
        .filter(
            AgentSession.corps_id == corps_id,
            AgentDefinition.role == role,
        )
        .order_by(AgentSession.started_at.desc())
        .first()
    )
    if old:
        new_session = spawn_session(
            db,
            definition_id=old.definition_id,
            corps_id=corps_id,
            parent_session_id=old.parent_session_id,
        )
        if old.context_snapshot:
            new_session.context_snapshot = old.context_snapshot
            db.commit()
        logger.info("Respawned session for role %s: %s -> %s", role, old.id, new_session.id)
        return new_session

    return None
