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


def _link_performer(db: Session, session: AgentSession, role: str) -> None:
    """Audition and link a performer to a session if not already linked."""
    if session.performer_id:
        return
    try:
        from backend.services.performer_service import audition_for_role
        performer = audition_for_role(db, role)
        if performer:
            session.performer_id = performer.id
            db.commit()
            logger.info("Linked performer %s (%s) to session %s for role %s",
                        performer.id, performer.name, session.id, role)
    except Exception as exc:
        logger.warning("Failed to link performer for role %s: %s", role, exc)


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
        # Link performer (reuse from old session or audition a new one)
        _link_performer(db, new_session, role)
        logger.info("Respawned session for role %s: %s -> %s", role, old.id, new_session.id)
        return new_session

    # No prior session exists at all — look up the definition and spawn fresh.
    # This unblocks corps that were created as DB records without running
    # initialize_corps(), which left most roles without any sessions.
    defn = (
        db.query(AgentDefinition)
        .filter(
            AgentDefinition.corps_id == corps_id,
            AgentDefinition.role == role,
        )
        .first()
    )
    if defn:
        _respawn_timestamps[key] = time.time()
        new_session = spawn_session(db, definition_id=defn.id, corps_id=corps_id)
        _link_performer(db, new_session, role)
        logger.info("Spawned fresh session for role %s (no prior session): %s", role, new_session.id)
        return new_session

    logger.warning("No definition found for role %s in corps %s — cannot spawn session", role, corps_id[:8])
    return None
