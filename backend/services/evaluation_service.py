"""Evaluation service — post-show evaluation of performer trust and corps performance.

After a show completes, evaluate each performer's contributions and adjust trust scores
based on rep scores, session outcomes, and penalties.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.performer import Performer
from backend.models.rep import Rep
from backend.models.score import Score

logger = logging.getLogger(__name__)


def evaluate_corps(db: Session, corps_id: str) -> dict:
    """Evaluate all performers in a corps after show completion.

    Returns a summary of trust adjustments made.
    """
    from backend.services.performer_service import record_session_completion

    sessions = (
        db.query(AgentSession)
        .filter(
            AgentSession.corps_id == corps_id,
            AgentSession.performer_id.isnot(None),
        )
        .all()
    )

    results = []
    for session in sessions:
        performer = db.get(Performer, session.performer_id)
        if not performer:
            continue

        # Determine success from session status
        success = session.status == SessionStatus.COMPLETED

        # Get average score for this session's reps
        avg_score = _get_session_avg_score(db, session)

        # Record session outcome
        try:
            record_session_completion(db, performer.id, success=success, score=avg_score)
        except Exception as e:
            logger.warning("Failed to record session completion for %s: %s", performer.name, e)
            continue

        results.append({
            "performer_id": performer.id,
            "performer_name": performer.name,
            "role": performer.role_type,
            "success": success,
            "avg_score": avg_score,
            "trust_score": performer.trust_score,
        })

    return {
        "corps_id": corps_id,
        "performers_evaluated": len(results),
        "details": results,
    }


def _get_session_avg_score(db: Session, session: AgentSession) -> Optional[float]:
    """Get the average score for reps associated with a session."""
    scores = (
        db.query(Score)
        .filter(Score.rep_id.isnot(None))
        .join(Rep, Rep.id == Score.rep_id)
        .filter(Rep.assigned_to == session.id)
        .all()
    )
    if not scores:
        return None
    return sum(s.value for s in scores) / len(scores)
