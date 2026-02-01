"""Metronome System Heartbeat Service

Provides ten-hut (wake all) and resume-hut (resume stalled work) commands
for the system-level metronome cron task.

Brass section: Command & Signal dispatch.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.corps import Corps, CorpsStatus
from backend.models.message import MessageType, MessagePriority
from backend.services.message_service import send_message

logger = logging.getLogger(__name__)

# Stalled work threshold: sessions pending for this long with no progress
STALLED_THRESHOLD_MINUTES = 5


@dataclass
class HeartbeatResult:
    """Result of a metronome heartbeat tick."""
    timestamp: str
    ten_hut_sent: int = 0
    resume_hut_sent: int = 0
    corps_pinged: list[str] = field(default_factory=list)
    stalled_corps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def ten_hut(db: Session) -> HeartbeatResult:
    """Send ten-hut (attention/wake) command to all active corps EDs.

    Ten-hut is a wake signal sent to every active corps' executive_director.
    It signals "check your status, ensure work is progressing, cascade to staff as needed."

    Returns:
        HeartbeatResult with counts and corps list
    """
    result = HeartbeatResult(timestamp=datetime.now(timezone.utc).isoformat())

    # Get all active corps (WINTER_CAMPS or ON_TOUR)
    from backend.services.corps_service import ADMIN_CORPS_NAME

    stmt = select(Corps).where(
        Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]),
        Corps.name != ADMIN_CORPS_NAME,
    )
    active_corps = db.scalars(stmt).all()

    for corps in active_corps:
        try:
            # Send ten-hut to ED
            send_message(
                db=db,
                corps_id=corps.id,
                from_role="system",
                to_role="executive_director",
                type=MessageType.TEN_HUT,
                subject="System Heartbeat — Ten-Hut",
                body=(
                    f"TEN-HUT! System heartbeat at {result.timestamp}.\n\n"
                    f"Check status of all work in your corps. Ensure reps are progressing. "
                    f"Cascade to staff as needed. Report any blockers or issues."
                ),
                priority=MessagePriority.NORMAL,
            )
            result.ten_hut_sent += 1
            result.corps_pinged.append(f"{corps.name} ({corps.id[:8]})")
        except Exception as e:
            error_msg = f"Failed to send ten-hut to {corps.name}: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

    return result


def resume_hut(db: Session) -> HeartbeatResult:
    """Detect stalled work and send resume-hut command to affected corps EDs.

    Stalled work is defined as:
    - Agent sessions in PENDING status for >5 minutes with no recent activity
    - Used to identify corps where work is stuck and needs intervention

    Resume-hut is sent ONLY to corps with stalled work, not to all corps.

    Returns:
        HeartbeatResult with counts and stalled corps list
    """
    result = HeartbeatResult(timestamp=datetime.now(timezone.utc).isoformat())
    now = datetime.now(timezone.utc)
    stalled_cutoff = now - timedelta(minutes=STALLED_THRESHOLD_MINUTES)

    # Get all active corps
    from backend.services.corps_service import ADMIN_CORPS_NAME

    stmt = select(Corps).where(
        Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]),
        Corps.name != ADMIN_CORPS_NAME,
    )
    active_corps = db.scalars(stmt).all()

    for corps in active_corps:
        try:
            # Find stalled reps: PENDING and created_at > 5 minutes ago (no progress)
            from backend.models.rep import Rep, RepStatus
            from backend.models.segment import Segment

            stalled_reps = (
                db.query(Rep)
                .join(Segment)
                .filter(
                    Segment.corps_id == corps.id,
                    Rep.status == RepStatus.PENDING,
                    Rep.created_at < stalled_cutoff,
                )
                .all()
            )

            if not stalled_reps:
                continue

            # Build stalled work summary
            stalled_rep_names = [f"{r.segment.name if r.segment else 'Unknown'}:{r.id[:8]}" for r in stalled_reps[:5]]
            stalled_summary = f"{len(stalled_reps)} stalled rep(s): {', '.join(stalled_rep_names)}"
            if len(stalled_reps) > 5:
                stalled_summary += f" (and {len(stalled_reps) - 5} more)"

            # Send resume-hut to ED
            send_message(
                db=db,
                corps_id=corps.id,
                from_role="system",
                to_role="executive_director",
                type=MessageType.RESUME_HUT,
                subject="Resume-Hut — Stalled Work Detected",
                body=(
                    f"RESUME-HUT! Stalled work detected at {result.timestamp}.\n\n"
                    f"{stalled_summary}\n\n"
                    f"These reps have been pending for >{STALLED_THRESHOLD_MINUTES} minutes "
                    f"with no progress. Review and take action: assign agents, investigate blockers, "
                    f"or adjust priorities."
                ),
                priority=MessagePriority.HIGH,
            )
            result.resume_hut_sent += 1
            result.stalled_corps.append(f"{corps.name} ({len(stalled_reps)} stalled)")
        except Exception as e:
            error_msg = f"Failed to check/resume {corps.name}: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

    return result


def heartbeat_tick(db: Session) -> dict:
    """Execute full metronome heartbeat: ten-hut + resume-hut.

    This is the main entry point called by the cron script via /api/heartbeat.

    Returns:
        Combined results from ten-hut and resume-hut operations
    """
    ten_hut_result = ten_hut(db)
    resume_hut_result = resume_hut(db)

    return {
        "timestamp": ten_hut_result.timestamp,
        "ten_hut": {
            "sent": ten_hut_result.ten_hut_sent,
            "corps": ten_hut_result.corps_pinged,
        },
        "resume_hut": {
            "sent": resume_hut_result.resume_hut_sent,
            "stalled_corps": resume_hut_result.stalled_corps,
        },
        "errors": ten_hut_result.errors + resume_hut_result.errors,
    }
