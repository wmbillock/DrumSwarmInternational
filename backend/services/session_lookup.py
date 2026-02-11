"""Shared session-by-role lookup with auto-respawn."""

import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.agent_definition import AgentDefinition
from backend.services.agent_lifecycle import spawn_session

logger = logging.getLogger(__name__)

# Minimum seconds between respawns for the same (corps, role) pair
_RESPAWN_COOLDOWN_SECONDS = 120
# Track last respawn time per (corps_id, role)
_respawn_timestamps: dict[tuple[str, str], float] = {}


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
    Enforces a cooldown to prevent rapid respawn loops.
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

    # Cooldown check: don't respawn the same role too frequently
    key = (corps_id, role)
    last_respawn = _respawn_timestamps.get(key, 0)
    if (time.time() - last_respawn) < _RESPAWN_COOLDOWN_SECONDS:
        logger.debug(
            "Respawn cooldown active for %s in corps %s (%.0fs remaining)",
            role, corps_id[:8],
            _RESPAWN_COOLDOWN_SECONDS - (time.time() - last_respawn),
        )
        return None

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
        _respawn_timestamps[key] = time.time()
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
