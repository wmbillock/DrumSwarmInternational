"""System health aggregation for the swarm overview.

Agent identity is based on AgentDefinition (one per role per corps), NOT
AgentSession (ephemeral instances that come and go). When an agent dies
and restarts, it's the same agent with a new session — not a new agent.
"""

from dataclasses import dataclass
from sqlalchemy import func as sqlfunc, and_
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

    Uses bulk queries instead of per-agent queries for performance.
    """
    active_corps_list = (
        db.query(Corps)
        .filter(
            Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]),
            Corps.corps_type != "system",
        )
        .all()
    )

    if not active_corps_list:
        return SwarmHealth(
            status="ok", active_corps=0, total_agents=0, active_agents=0,
            failed_agents=0, total_sessions=0, total_reps=0, completed_reps=0,
            failed_reps=0, stale_reps=0, failure_rate=0.0, corps_summaries=[],
        )

    corps_ids = [c.id for c in active_corps_list]
    corps_map = {c.id: c for c in active_corps_list}

    # Bulk: agent definition counts per corps
    defn_counts = dict(
        db.query(AgentDefinition.corps_id, sqlfunc.count(AgentDefinition.id))
        .filter(AgentDefinition.corps_id.in_(corps_ids))
        .group_by(AgentDefinition.corps_id)
        .all()
    )

    # Bulk: session counts per corps
    session_counts = dict(
        db.query(AgentSession.corps_id, sqlfunc.count(AgentSession.id))
        .filter(AgentSession.corps_id.in_(corps_ids))
        .group_by(AgentSession.corps_id)
        .all()
    )

    # Bulk: active session counts per corps (agents currently alive)
    active_session_corps = dict(
        db.query(AgentSession.corps_id, sqlfunc.count(sqlfunc.distinct(AgentSession.definition_id)))
        .filter(
            AgentSession.corps_id.in_(corps_ids),
            AgentSession.status == SessionStatus.ACTIVE,
        )
        .group_by(AgentSession.corps_id)
        .all()
    )

    # Bulk: failed agents — definitions whose LATEST session is FAILED
    # Use a subquery to find the latest session per definition
    from sqlalchemy import select
    latest_session_sq = (
        select(
            AgentSession.definition_id,
            AgentSession.corps_id,
            sqlfunc.max(AgentSession.started_at).label("max_started"),
        )
        .where(AgentSession.corps_id.in_(corps_ids))
        .group_by(AgentSession.definition_id, AgentSession.corps_id)
        .subquery()
    )

    failed_defn_corps = dict(
        db.query(AgentSession.corps_id, sqlfunc.count(AgentSession.definition_id))
        .join(
            latest_session_sq,
            and_(
                AgentSession.definition_id == latest_session_sq.c.definition_id,
                AgentSession.corps_id == latest_session_sq.c.corps_id,
                AgentSession.started_at == latest_session_sq.c.max_started,
            ),
        )
        .filter(AgentSession.status == SessionStatus.FAILED)
        .group_by(AgentSession.corps_id)
        .all()
    )

    # Rep stats per corps (grouped by status for efficiency)
    rep_total_map: dict[str, int] = {}
    rep_completed_map: dict[str, int] = {}
    rep_failed_map: dict[str, int] = {}

    for corps_id in corps_ids:
        c_sessions = session_counts.get(corps_id, 0)
        if c_sessions == 0:
            continue
        reps = (
            db.query(Rep.status, sqlfunc.count(Rep.id))
            .join(AgentSession, Rep.assigned_to == AgentSession.id, isouter=True)
            .filter(AgentSession.corps_id == corps_id)
            .group_by(Rep.status)
            .all()
        )
        for status, count in reps:
            rep_total_map[corps_id] = rep_total_map.get(corps_id, 0) + count
            if status == RepStatus.COMPLETED:
                rep_completed_map[corps_id] = count
            elif status == RepStatus.FAILED:
                rep_failed_map[corps_id] = count

    # Bulk: failure counts from work log
    failure_counts = dict(
        db.query(WorkLog.corps_id, sqlfunc.count(WorkLog.id))
        .filter(
            WorkLog.corps_id.in_(corps_ids),
            WorkLog.event_type == "failure",
        )
        .group_by(WorkLog.corps_id)
        .all()
    )

    # Assemble results
    total_agents = 0
    active_agents = 0
    failed_agents = 0
    total_sessions = 0
    total_reps = 0
    completed_reps = 0
    failed_reps = 0
    corps_summaries = []

    for corps_id in corps_ids:
        corps = corps_map[corps_id]
        c_total = defn_counts.get(corps_id, 0)
        c_active = active_session_corps.get(corps_id, 0)
        c_failed = failed_defn_corps.get(corps_id, 0)
        c_sessions = session_counts.get(corps_id, 0)
        c_reps_total = rep_total_map.get(corps_id, 0)
        c_reps_completed = rep_completed_map.get(corps_id, 0)
        c_reps_failed = rep_failed_map.get(corps_id, 0)

        total_agents += c_total
        active_agents += c_active
        failed_agents += c_failed
        total_sessions += c_sessions
        total_reps += c_reps_total
        completed_reps += c_reps_completed
        failed_reps += c_reps_failed

        corps_summaries.append({
            "id": corps_id,
            "name": corps.name,
            "status": corps.status.value,
            "mode": corps.mode.value if corps.mode else None,
            "agents_active": c_active,
            "agents_total": c_total,
            "sessions_total": c_sessions,
            "reps_completed": c_reps_completed,
            "reps_total": c_reps_total,
            "failures": failure_counts.get(corps_id, 0),
        })

    failure_rate = round(failed_reps / total_reps * 100, 1) if total_reps > 0 else 0.0

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
        stale_reps=0,
        failure_rate=failure_rate,
        corps_summaries=corps_summaries,
    )
