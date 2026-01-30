"""Metronome — liveness monitor and accountability enforcer.

A continuous background service that:
- Polls all in_progress reps
- Checks if the owning agent session is still alive
- Reclaims stale reps (resets to pending for reassignment)
- Emits heartbeat events for observability

If work is assigned to you and you're not running it, the metronome
takes it back and puts it on the board for reassignment.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.rep import Rep, RepStatus


@dataclass
class MetronomeResult:
    """Result of a single metronome tick."""
    checked: int = 0
    reclaimed: int = 0
    reclaimed_rep_ids: list[str] = field(default_factory=list)
    timestamp: str = ""


def tick(db: Session, corps_id: str) -> MetronomeResult:
    """Run one metronome tick for a corps.

    Finds all assigned/in_progress reps, checks if their owning session
    is still alive, and reclaims any that are orphaned.
    """
    result = MetronomeResult(timestamp=datetime.now(timezone.utc).isoformat())

    # Find all active reps (assigned or in_progress) for this corps
    active_reps = (
        db.query(Rep)
        .join(Rep.coordinate)
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

    if result.reclaimed > 0:
        db.commit()

    return result
