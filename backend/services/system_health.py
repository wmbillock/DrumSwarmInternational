"""System health aggregation for the swarm overview."""

from dataclasses import dataclass
from sqlalchemy.orm import Session

from backend.models.corps import Corps, CorpsStatus, CorpsMode
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.work_log import WorkLog
from backend.models.rep import Rep, RepStatus


@dataclass
class SwarmHealth:
    active_corps: int
    total_agents: int
    active_agents: int
    failed_agents: int
    total_reps: int
    completed_reps: int
    failed_reps: int
    stale_reps: int
    failure_rate: float
    corps_summaries: list[dict]


def get_swarm_health(db: Session) -> SwarmHealth:
    """Aggregate health metrics across all active corps."""
    active_corps_list = (
        db.query(Corps)
        .filter(Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]))
        .all()
    )

    total_agents = 0
    active_agents = 0
    failed_agents = 0
    total_reps = 0
    completed_reps = 0
    failed_reps = 0
    stale_reps = 0
    corps_summaries = []

    for corps in active_corps_list:
        sessions = db.query(AgentSession).filter(AgentSession.corps_id == corps.id).all()
        c_active = sum(1 for s in sessions if s.status == SessionStatus.ACTIVE)
        c_failed = sum(1 for s in sessions if s.status == SessionStatus.FAILED)

        reps = db.query(Rep).join(
            AgentSession, Rep.assigned_to == AgentSession.id, isouter=True
        ).filter(AgentSession.corps_id == corps.id).all() if sessions else []

        c_total_reps = len(reps)
        c_completed = sum(1 for r in reps if r.status == RepStatus.COMPLETED)
        c_failed_reps = sum(1 for r in reps if r.status == RepStatus.FAILED)

        # Count stale: in_progress but no activity recently
        failure_count = (
            db.query(WorkLog)
            .filter(WorkLog.corps_id == corps.id, WorkLog.event_type == "failure")
            .count()
        )

        total_agents += len(sessions)
        active_agents += c_active
        failed_agents += c_failed
        total_reps += c_total_reps
        completed_reps += c_completed
        failed_reps += c_failed_reps

        corps_summaries.append({
            "id": corps.id,
            "name": corps.name,
            "status": corps.status.value,
            "mode": corps.mode.value if corps.mode else None,
            "agents_active": c_active,
            "agents_total": len(sessions),
            "reps_completed": c_completed,
            "reps_total": c_total_reps,
            "failures": failure_count,
        })

    failure_rate = round(failed_reps / total_reps * 100, 1) if total_reps > 0 else 0.0

    return SwarmHealth(
        active_corps=len(active_corps_list),
        total_agents=total_agents,
        active_agents=active_agents,
        failed_agents=failed_agents,
        total_reps=total_reps,
        completed_reps=completed_reps,
        failed_reps=failed_reps,
        stale_reps=stale_reps,
        failure_rate=failure_rate,
        corps_summaries=corps_summaries,
    )
