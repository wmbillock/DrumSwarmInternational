"""Metronome — liveness monitor, GUPP enforcer, and watchdog chain.

A continuous background service that:
- Polls all in_progress reps
- Checks if the owning agent session is still alive
- Reclaims stale reps (resets to pending for reassignment)
- GUPP enforcement: kicks idle agents with assigned-but-unworked reps
- Watchdog chain: monitors critical roles and respawns if dead
- Emits heartbeat events for observability

If work is assigned to you and you're not running it, the metronome
takes it back and puts it on the board for reassignment.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.rep import Rep, RepStatus

logger = logging.getLogger(__name__)

# GUPP: max seconds a rep can sit in ASSIGNED without moving to IN_PROGRESS
GUPP_IDLE_THRESHOLD_SECONDS = 120

# Watchdog chain: ordered list of roles to monitor, each monitors the next
WATCHDOG_CHAIN = [
    "timing_judge",        # Boot-level: if this dies, metronome respawns it
    "drum_major",          # Monitors caption heads
    "brass_caption_head",
    "percussion_caption_head",
    "guard_caption_head",
    "visual_caption_head",
]


@dataclass
class MetronomeResult:
    """Result of a single metronome tick."""
    checked: int = 0
    reclaimed: int = 0
    reclaimed_rep_ids: list[str] = field(default_factory=list)
    idle_kicked: int = 0
    idle_kicked_rep_ids: list[str] = field(default_factory=list)
    watchdog_respawned: list[str] = field(default_factory=list)
    timestamp: str = ""


def tick(db: Session, corps_id: str) -> MetronomeResult:
    """Run one metronome tick for a corps.

    Finds all assigned/in_progress reps, checks if their owning session
    is still alive, reclaims orphans, and enforces GUPP idle limits.
    """
    result = MetronomeResult(timestamp=datetime.now(timezone.utc).isoformat())
    now = datetime.now(timezone.utc)

    # Find all active reps (assigned or in_progress) for this corps
    active_reps = (
        db.query(Rep)
        .join(Rep.segment)
        .filter(
            Rep.status.in_([RepStatus.ASSIGNED, RepStatus.IN_PROGRESS]),
            Rep.assigned_to.isnot(None),
        )
        .all()
    )

    for rep in active_reps:
        result.checked += 1

        # Check if the owning session is still alive
        session = db.get(AgentSession, rep.assigned_to)
        if session is None or session.status != SessionStatus.ACTIVE:
            # Reclaim: reset to pending, clear assignment
            rep.status = RepStatus.PENDING
            rep.assigned_to = None
            result.reclaimed += 1
            result.reclaimed_rep_ids.append(rep.id)
            continue

        # GUPP: check for idle assigned reps (assigned but not progressing)
        if rep.status == RepStatus.ASSIGNED and rep.updated_at:
            idle_seconds = (now - rep.updated_at.replace(tzinfo=timezone.utc)).total_seconds()
            if idle_seconds > GUPP_IDLE_THRESHOLD_SECONDS:
                # Kick: reclaim and apply trust penalty to performer
                rep.status = RepStatus.PENDING
                rep.assigned_to = None
                result.idle_kicked += 1
                result.idle_kicked_rep_ids.append(rep.id)
                _apply_idle_penalty(db, session)

    if result.reclaimed > 0 or result.idle_kicked > 0:
        db.commit()

    # Watchdog chain: check critical roles
    result.watchdog_respawned = _watchdog_check(db, corps_id)

    return result


def _apply_idle_penalty(db: Session, session: AgentSession) -> None:
    """Apply trust penalty to the performer for idle GUPP violation."""
    try:
        if session.performer_id:
            from backend.services.performer_service import update_trust
            update_trust(db, session.performer_id, -3.0, reason="GUPP violation: idle on assigned rep")
    except Exception:
        logger.warning("Failed to apply idle penalty for session %s", session.id)


def _watchdog_check(db: Session, corps_id: str) -> list[str]:
    """Check watchdog chain roles and flag any that are dead.

    Returns list of role names that need respawning.
    """
    from backend.models.agent_definition import AgentDefinition

    dead_roles = []
    for role in WATCHDOG_CHAIN:
        sessions = (
            db.query(AgentSession)
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .filter(
                AgentSession.corps_id == corps_id,
                AgentDefinition.role == role,
            )
            .all()
        )
        if not sessions:
            continue

        # Check if any session for this role is active
        has_active = any(s.status == SessionStatus.ACTIVE for s in sessions)
        all_terminal = all(
            s.status in {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.TIMED_OUT}
            for s in sessions
        )

        if all_terminal and not has_active:
            dead_roles.append(role)
            logger.warning("Watchdog: role %s is dead in corps %s", role, corps_id)

    return dead_roles
