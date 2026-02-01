#!/usr/bin/env python3
"""Metronome Orchestrator — System-level swarm heartbeat.

This module orchestrates the entire DCI swarm at the system level:
1. Issues ten-hut (wake) commands to all active corps
2. Issues resume-hut to corps with stalled work
3. Gathers swarm-wide status and generates reports
4. Logs all activity with structured output

Designed to be invoked by scripts/metronome/tick.sh every 5 minutes.
"""

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import create_db_engine, create_session_factory
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.corps import Corps, CorpsStatus, RehearsalMode
from backend.models.rep import Rep, RepStatus
from backend.tools.metronome import tick as corps_tick

# Initialize database connection
# Use the same default path as app.py
engine = create_db_engine()
SessionFactory = create_session_factory(engine)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

# Configuration
STALLED_THRESHOLD_MINUTES = 5
ALERT_THRESHOLD_FAILURES = 3
CORPS_TIMEOUT_SECONDS = 30


@dataclass
class CorpsHealth:
    """Health status for a single corps."""
    corps_id: str
    corps_name: str
    status: str
    rehearsal_mode: str
    active_sessions: int = 0
    completed_sessions: int = 0
    failed_sessions: int = 0
    pending_reps: int = 0
    in_progress_reps: int = 0
    completed_reps: int = 0
    failed_reps: int = 0
    stalled_reps: list[str] = field(default_factory=list)
    ed_responding: bool = False
    pc_responding: bool = False
    last_activity: Optional[str] = None
    tick_duration_ms: int = 0


@dataclass
class SwarmReport:
    """Swarm-wide status report."""
    timestamp: str
    total_corps: int = 0
    active_corps: int = 0
    corps_health: list[CorpsHealth] = field(default_factory=list)
    total_sessions: int = 0
    total_reps: int = 0
    alerts: list[str] = field(default_factory=list)


def get_active_corps(db: Session) -> list[Corps]:
    """Get all active corps (not COMPLETED or DISBANDED)."""
    stmt = select(Corps).where(
        Corps.status.notin_([CorpsStatus.COMPLETED, CorpsStatus.DISBANDED])
    )
    return list(db.execute(stmt).scalars().all())


def detect_stalled_reps(db: Session, corps_id: str) -> list[str]:
    """Detect reps that are pending for >N minutes with no agent activity.

    Returns list of rep IDs that are stalled.
    """
    threshold = datetime.now(timezone.utc) - timedelta(minutes=STALLED_THRESHOLD_MINUTES)

    stmt = (
        select(Rep)
        .where(
            Rep.status == RepStatus.PENDING,
            Rep.created_at < threshold,
        )
        .join(Rep.segment)
    )

    stalled = db.execute(stmt).scalars().all()
    return [rep.id for rep in stalled]


def check_agent_liveness(db: Session, corps_id: str, role: str) -> bool:
    """Check if any agent session for the given role is currently active."""
    stmt = (
        select(AgentSession)
        .join(AgentSession.definition)
        .where(
            AgentSession.corps_id == corps_id,
            AgentSession.status == SessionStatus.ACTIVE,
        )
    )

    sessions = db.execute(stmt).scalars().all()
    return any(s.definition.role == role for s in sessions if s.definition)


def gather_corps_health(db: Session, corps: Corps) -> CorpsHealth:
    """Gather health metrics for a single corps."""
    start = datetime.now(timezone.utc)

    health = CorpsHealth(
        corps_id=corps.id,
        corps_name=corps.name or "Unnamed Corps",
        status=corps.status.value if corps.status else "UNKNOWN",
        rehearsal_mode=corps.rehearsal_mode.value if corps.rehearsal_mode else "UNKNOWN",
    )

    # Count sessions by status
    sessions_stmt = select(AgentSession).where(AgentSession.corps_id == corps.id)
    sessions = db.execute(sessions_stmt).scalars().all()

    for session in sessions:
        if session.status == SessionStatus.ACTIVE:
            health.active_sessions += 1
        elif session.status == SessionStatus.COMPLETED:
            health.completed_sessions += 1
        elif session.status in (SessionStatus.FAILED, SessionStatus.TIMED_OUT):
            health.failed_sessions += 1

    # Count reps by status (this is a simplification - ideally filter by corps via segment)
    # For now we'll run the per-corps tick to get accurate numbers
    try:
        tick_result = corps_tick(db, corps.id)
        logger.info(
            f"Corps {corps.id}: checked {tick_result.checked} reps, "
            f"reclaimed {tick_result.reclaimed}, idle_kicked {tick_result.idle_kicked}"
        )
    except Exception as e:
        logger.error(f"Failed to run corps tick for {corps.id}: {e}")

    # Detect stalled reps
    health.stalled_reps = detect_stalled_reps(db, corps.id)

    # Check key agent liveness
    health.ed_responding = check_agent_liveness(db, corps.id, "executive_director")
    health.pc_responding = check_agent_liveness(db, corps.id, "program_coordinator")

    # Calculate last activity (use started_at since AgentSession doesn't have updated_at)
    if sessions:
        latest_session = max(
            (s for s in sessions if s.started_at),
            key=lambda s: s.started_at,
            default=None
        )
        if latest_session and latest_session.started_at:
            health.last_activity = latest_session.started_at.isoformat()

    duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
    health.tick_duration_ms = duration_ms

    return health


def issue_ten_hut(db: Session, corps_id: str) -> bool:
    """Issue ten-hut (wake) command to a corps' executive director.

    Returns True if successful, False otherwise.
    """
    try:
        logger.info(f"TEN-HUT: Waking corps {corps_id}")
        from backend.models.message import MessageType, MessagePriority
        from backend.services.message_service import send_message

        send_message(
            db=db,
            corps_id=corps_id,
            from_role="system",
            to_role="executive_director",
            type=MessageType.TEN_HUT,
            subject="System Heartbeat — Ten-Hut",
            body=(
                f"TEN-HUT! Orchestrator wake signal at {datetime.now(timezone.utc).isoformat()}.\n\n"
                f"Check status of all work in your corps. Ensure reps are progressing. "
                f"Cascade to staff as needed."
            ),
            priority=MessagePriority.NORMAL,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to issue ten-hut to corps {corps_id}: {e}")
        return False


def issue_resume_hut(db: Session, corps_id: str, stalled_reps: list[str]) -> bool:
    """Issue resume-hut command to a corps' executive director for stalled work.

    Returns True if successful, False otherwise.
    """
    try:
        logger.info(
            f"RESUME-HUT: Alerting corps {corps_id} about {len(stalled_reps)} stalled reps"
        )
        from backend.models.message import MessageType, MessagePriority
        from backend.services.message_service import send_message

        stalled_summary = ", ".join(stalled_reps[:10])
        if len(stalled_reps) > 10:
            stalled_summary += f" (and {len(stalled_reps) - 10} more)"

        send_message(
            db=db,
            corps_id=corps_id,
            from_role="system",
            to_role="executive_director",
            type=MessageType.RESUME_HUT,
            subject="Resume-Hut — Stalled Work Detected",
            body=(
                f"RESUME-HUT! Stalled work detected at {datetime.now(timezone.utc).isoformat()}.\n\n"
                f"Stalled reps: {stalled_summary}\n\n"
                f"These reps have been pending for >{STALLED_THRESHOLD_MINUTES} minutes. "
                f"Review and take action."
            ),
            priority=MessagePriority.HIGH,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to issue resume-hut to corps {corps_id}: {e}")
        return False


def generate_swarm_report(db: Session) -> SwarmReport:
    """Generate a comprehensive swarm-wide status report."""
    timestamp = datetime.now(timezone.utc).isoformat()
    report = SwarmReport(timestamp=timestamp)

    # Get all active corps
    all_corps = get_active_corps(db)
    report.total_corps = len(all_corps)

    for corps in all_corps:
        try:
            # Gather health metrics
            health = gather_corps_health(db, corps)
            report.corps_health.append(health)

            # Update aggregates
            if corps.status == CorpsStatus.ON_TOUR or corps.status == CorpsStatus.WINTER_CAMPS:
                report.active_corps += 1

            report.total_sessions += (
                health.active_sessions + health.completed_sessions + health.failed_sessions
            )
            report.total_reps += (
                health.pending_reps + health.in_progress_reps +
                health.completed_reps + health.failed_reps
            )

            # Issue commands
            issue_ten_hut(db, corps.id)

            if health.stalled_reps:
                issue_resume_hut(db, corps.id, health.stalled_reps)

            # Check for unresponsive corps (neither ED nor PC responding)
            if not health.ed_responding and not health.pc_responding:
                alert = f"RED FLAG: Corps {corps.id} ({health.corps_name}) - No ED/PC response"
                report.alerts.append(alert)
                logger.warning(alert)

        except Exception as e:
            logger.error(f"Failed to process corps {corps.id}: {e}")
            alert = f"ERROR: Failed to process corps {corps.id}: {str(e)}"
            report.alerts.append(alert)

    return report


def write_report(report: SwarmReport, log_dir: Path) -> None:
    """Write the swarm report to disk in both JSON and human-readable formats."""
    timestamp_clean = report.timestamp.replace(":", "-").replace(".", "-")

    # JSON format for machine readability
    json_path = log_dir / f"{timestamp_clean}.json"
    with open(json_path, "w") as f:
        json.dump(asdict(report), f, indent=2)

    logger.info(f"Report written to {json_path}")

    # Also log a human-readable summary
    logger.info("=" * 80)
    logger.info("SWARM STATUS SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Timestamp: {report.timestamp}")
    logger.info(f"Total Corps: {report.total_corps}")
    logger.info(f"Active Corps: {report.active_corps}")
    logger.info(f"Total Sessions: {report.total_sessions}")
    logger.info(f"Total Reps: {report.total_reps}")

    if report.alerts:
        logger.warning(f"ALERTS ({len(report.alerts)}):")
        for alert in report.alerts:
            logger.warning(f"  - {alert}")

    logger.info("-" * 80)
    logger.info("CORPS HEALTH:")
    for health in report.corps_health:
        logger.info(f"  {health.corps_name} ({health.corps_id[:8]}):")
        logger.info(f"    Status: {health.status} | Mode: {health.rehearsal_mode}")
        logger.info(f"    Sessions: {health.active_sessions} active, {health.completed_sessions} completed, {health.failed_sessions} failed")
        logger.info(f"    ED: {'✓' if health.ed_responding else '✗'} | PC: {'✓' if health.pc_responding else '✗'}")
        if health.stalled_reps:
            logger.info(f"    ⚠ {len(health.stalled_reps)} stalled reps")
        logger.info(f"    Tick: {health.tick_duration_ms}ms")

    logger.info("=" * 80)


def write_alerts(report: SwarmReport, alert_log: Path) -> None:
    """Write alerts to the dedicated alert log."""
    if not report.alerts:
        return

    with open(alert_log, "a") as f:
        for alert in report.alerts:
            f.write(f"[{report.timestamp}] {alert}\n")


def main() -> int:
    """Main orchestrator entry point."""
    logger.info("=== Metronome Orchestrator Starting ===")

    try:
        # Create database session
        db = SessionFactory()

        try:
            # Generate swarm report (which also issues commands)
            report = generate_swarm_report(db)

            # Write outputs
            log_dir = Path(__file__).parent.parent.parent / "logs" / "metronome"
            log_dir.mkdir(parents=True, exist_ok=True)

            write_report(report, log_dir)

            alert_log = log_dir / "alerts.log"
            write_alerts(report, alert_log)

            logger.info("=== Metronome Orchestrator Completed Successfully ===")
            return 0

        finally:
            db.close()

    except Exception as e:
        logger.error(f"FATAL: Orchestrator failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
