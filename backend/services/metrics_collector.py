"""Metrics collector — gathers per-session and per-corps performance data.

Feeds the self-improvement loop by tracking duration, iterations, token usage,
success/failure rates, and scores across sessions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.performer import Performer
from backend.models.rep import Rep, RepStatus
from backend.models.score import Score
from backend.models.work_log import WorkLog

logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    """Metrics for a single agent session."""
    session_id: str
    role: str
    status: str
    iterations: int = 0
    tool_calls: int = 0
    duration_seconds: Optional[float] = None
    performer_name: Optional[str] = None
    performer_trust: Optional[float] = None


@dataclass
class RoleMetrics:
    """Aggregate metrics for a role across sessions."""
    role: str
    total_sessions: int = 0
    successful_sessions: int = 0
    failed_sessions: int = 0
    success_rate: float = 0.0
    avg_iterations: float = 0.0
    avg_tool_calls: float = 0.0


@dataclass
class CorpsMetrics:
    """Aggregate metrics for a corps."""
    corps_id: str
    total_sessions: int = 0
    total_reps: int = 0
    completed_reps: int = 0
    failed_reps: int = 0
    rep_completion_rate: float = 0.0
    avg_score: float = 0.0
    role_metrics: list[RoleMetrics] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def collect_session_metrics(db: Session, session_id: str) -> SessionMetrics:
    """Collect metrics for a single session."""
    agent_session = db.get(AgentSession, session_id)
    if not agent_session:
        return SessionMetrics(session_id=session_id, role="unknown", status="unknown")

    from backend.models.agent_definition import AgentDefinition
    defn = db.get(AgentDefinition, agent_session.definition_id)
    role = defn.role if defn else "unknown"

    metrics = SessionMetrics(
        session_id=session_id,
        role=role,
        status=agent_session.status.value,
    )

    # Count work log entries as proxy for iterations/tool calls
    logs = db.query(WorkLog).filter(WorkLog.session_id == session_id).all()
    metrics.tool_calls = sum(1 for l in logs if l.event_type == "tool_call")
    metrics.iterations = sum(1 for l in logs if l.event_type == "iteration")

    # Performer info
    if agent_session.performer_id:
        performer = db.get(Performer, agent_session.performer_id)
        if performer:
            metrics.performer_name = performer.name
            metrics.performer_trust = performer.trust_score

    return metrics


def collect_corps_metrics(db: Session, corps_id: str) -> CorpsMetrics:
    """Collect aggregate metrics for a corps."""
    metrics = CorpsMetrics(corps_id=corps_id)

    sessions = db.query(AgentSession).filter(AgentSession.corps_id == corps_id).all()
    metrics.total_sessions = len(sessions)

    # Role-level aggregation
    role_data: dict[str, dict] = {}
    for s in sessions:
        from backend.models.agent_definition import AgentDefinition
        defn = db.get(AgentDefinition, s.definition_id)
        role = defn.role if defn else "unknown"

        if role not in role_data:
            role_data[role] = {"total": 0, "success": 0, "failed": 0}
        role_data[role]["total"] += 1
        if s.status == SessionStatus.COMPLETED:
            role_data[role]["success"] += 1
        elif s.status == SessionStatus.FAILED:
            role_data[role]["failed"] += 1

    for role, data in role_data.items():
        rm = RoleMetrics(
            role=role,
            total_sessions=data["total"],
            successful_sessions=data["success"],
            failed_sessions=data["failed"],
            success_rate=data["success"] / data["total"] if data["total"] > 0 else 0.0,
        )
        metrics.role_metrics.append(rm)

    # Rep metrics
    from backend.models.segment import Segment
    reps = (
        db.query(Rep)
        .join(Segment)
        .join(AgentSession, AgentSession.corps_id == corps_id)
        .all()
    ) if sessions else []
    # Simpler: just get all reps (will refine when corps→segment link is clearer)
    all_reps = db.query(Rep).all()
    metrics.total_reps = len(all_reps)
    metrics.completed_reps = sum(1 for r in all_reps if r.status == RepStatus.COMPLETED)
    metrics.failed_reps = sum(1 for r in all_reps if r.status == RepStatus.FAILED)
    metrics.rep_completion_rate = (
        metrics.completed_reps / metrics.total_reps if metrics.total_reps > 0 else 0.0
    )

    # Scores
    all_scores = db.query(Score).all()
    if all_scores:
        metrics.avg_score = sum(s.value for s in all_scores) / len(all_scores)

    # Generate recommendations
    metrics.recommendations = _generate_recommendations(metrics)

    return metrics


def _generate_recommendations(metrics: CorpsMetrics) -> list[str]:
    """Generate improvement recommendations based on metrics."""
    recs = []

    # Role-level recommendations
    for rm in metrics.role_metrics:
        if rm.total_sessions >= 3 and rm.success_rate < 0.5:
            recs.append(
                f"Role '{rm.role}' has {rm.success_rate:.0%} success rate — "
                f"consider prompt refinement or model tier upgrade"
            )
        if rm.failed_sessions > rm.successful_sessions:
            recs.append(
                f"Role '{rm.role}' has more failures than successes — review system prompt"
            )

    # Corps-level recommendations
    if metrics.rep_completion_rate < 0.5 and metrics.total_reps > 0:
        recs.append("Low rep completion rate — check for blocking dependencies or resource issues")

    if metrics.avg_score > 0 and metrics.avg_score < 60:
        recs.append("Average score below 60 — consider increasing iteration limits or model tiers")

    return recs
