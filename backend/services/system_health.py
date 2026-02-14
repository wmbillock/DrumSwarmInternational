"""System health aggregation for the swarm overview.

Agent identity is based on AgentDefinition (one per role per corps), NOT
AgentSession (ephemeral instances that come and go). When an agent dies
and restarts, it's the same agent with a new session — not a new agent.
"""

from dataclasses import dataclass
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from backend.models.corps import Corps, CorpsStatus, CorpsMode
from backend.models.agent_definition import AgentDefinition
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.work_log import WorkLog
from backend.models.rep import Rep, RepStatus


@dataclass
class SwarmHealth:
    status: str             # "ok", "warning", "error" based on health metrics
    active_corps: int
    total_agents: int       # unique agent definitions (roles)
    active_agents: int      # definitions with at least one ACTIVE session
    failed_agents: int      # definitions whose latest session is FAILED
    total_sessions: int     # total session instances (for diagnostics)
    total_reps: int
    completed_reps: int
    failed_reps: int
    stale_reps: int
    failure_rate: float
    corps_summaries: list[dict]


def get_swarm_health(db: Session) -> SwarmHealth:
    """Aggregate health metrics across all active corps.

    Agents are counted by unique AgentDefinition (role), not by session.
    """
    active_corps_list = (
        db.query(Corps)
        .filter(
            Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]),
            Corps.corps_type != "system",
        )
        .all()
    )

    total_agents = 0
    active_agents = 0
    failed_agents = 0
    total_sessions = 0
    total_reps = 0
    completed_reps = 0
    failed_reps = 0
    stale_reps = 0
    corps_summaries = []

    for corps in active_corps_list:
        # Count unique agent definitions (the actual agents)
        definitions = (
            db.query(AgentDefinition)
            .filter(AgentDefinition.corps_id == corps.id)
            .all()
        )
        c_total_agents = len(definitions)

        # For each definition, check if it has an active session (agent is "alive")
        c_active = 0
        c_failed = 0
        for defn in definitions:
            latest_session = (
                db.query(AgentSession)
                .filter(
                    AgentSession.definition_id == defn.id,
                    AgentSession.corps_id == corps.id,
                )
                .order_by(AgentSession.started_at.desc())
                .first()
            )
            if latest_session:
                if latest_session.status == SessionStatus.ACTIVE:
                    c_active += 1
                elif latest_session.status == SessionStatus.FAILED:
                    c_failed += 1

        # Count total sessions for diagnostics
        c_sessions = (
            db.query(AgentSession)
            .filter(AgentSession.corps_id == corps.id)
            .count()
        )

        reps = db.query(Rep).join(
            AgentSession, Rep.assigned_to == AgentSession.id, isouter=True
        ).filter(AgentSession.corps_id == corps.id).all() if c_sessions > 0 else []

        c_total_reps = len(reps)
        c_completed = sum(1 for r in reps if r.status == RepStatus.COMPLETED)
        c_failed_reps = sum(1 for r in reps if r.status == RepStatus.FAILED)

        failure_count = (
            db.query(WorkLog)
            .filter(WorkLog.corps_id == corps.id, WorkLog.event_type == "failure")
            .count()
        )

        total_agents += c_total_agents
        active_agents += c_active
        failed_agents += c_failed
        total_sessions += c_sessions
        total_reps += c_total_reps
        completed_reps += c_completed
        failed_reps += c_failed_reps

        corps_summaries.append({
            "id": corps.id,
            "name": corps.name,
            "status": corps.status.value,
            "mode": corps.mode.value if corps.mode else None,
            "agents_active": c_active,
            "agents_total": c_total_agents,
            "sessions_total": c_sessions,
            "reps_completed": c_completed,
            "reps_total": c_total_reps,
            "failures": failure_count,
        })

    failure_rate = round(failed_reps / total_reps * 100, 1) if total_reps > 0 else 0.0

    # Calculate overall health status
    # "error" if majority of agents failed or failure rate > 50%
    # "warning" if >25% agents failed or failure rate > 10%
    # "ok" otherwise
    failed_pct = (failed_agents / total_agents * 100) if total_agents > 0 else 0
    if failed_pct > 50 or failure_rate > 50:
        health_status = "error"
    elif failed_pct > 25 or failure_rate > 10 or (total_agents > 0 and active_agents / total_agents < 0.5):
        health_status = "warning"
    else:
        health_status = "ok"

    return SwarmHealth(
        status=health_status,
        active_corps=len(active_corps_list),
        total_agents=total_agents,
        active_agents=active_agents,
        failed_agents=failed_agents,
        total_sessions=total_sessions,
        total_reps=total_reps,
        completed_reps=completed_reps,
        failed_reps=failed_reps,
        stale_reps=stale_reps,
        failure_rate=failure_rate,
        corps_summaries=corps_summaries,
    )
