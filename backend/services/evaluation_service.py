"""Evaluation service — post-competition score-based trust adjustments.

After a competition completes, check if any performers earned score-based
trust bonuses (high rep scores). The base trust update for session
success/failure is handled in agent_lifecycle._terminate_session; this
service adds score-aware bonuses on top.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.performer import Performer
from backend.models.rep import Rep
from backend.models.score import Score

logger = logging.getLogger(__name__)

# Bonus trust for high-scoring reps (on top of the base session trust)
_SCORE_BONUS_THRESHOLD = 80.0
_SCORE_BONUS_DELTA = 2.0


def evaluate_corps(db: Session, corps_id: str) -> dict:
    """Apply score-based trust bonuses for completed sessions in a corps.

    Only awards bonuses for sessions with high-scoring reps. The base
    trust adjustment for session success/failure is already handled by
    _terminate_session via record_session_completion.
    """
    from backend.services.performer_service import update_trust

    sessions = (
        db.query(AgentSession)
        .filter(
            AgentSession.corps_id == corps_id,
            AgentSession.performer_id.isnot(None),
            AgentSession.status == SessionStatus.COMPLETED,
        )
        .all()
    )

    results = []
    for session in sessions:
        performer = db.get(Performer, session.performer_id)
        if not performer:
            continue

        avg_score = _get_session_avg_score(db, session)
        if avg_score is not None and avg_score >= _SCORE_BONUS_THRESHOLD:
            try:
                update_trust(
                    db, performer.id, _SCORE_BONUS_DELTA,
                    reason=f"high_score_bonus (avg={avg_score:.1f})",
                )
                results.append({
                    "performer_id": performer.id,
                    "performer_name": performer.name,
                    "role": performer.role_type,
                    "avg_score": avg_score,
                    "bonus": _SCORE_BONUS_DELTA,
                    "trust_score": performer.trust_score,
                })
            except Exception as e:
                logger.warning("Score bonus failed for %s: %s", performer.name, e)

    return {
        "corps_id": corps_id,
        "bonuses_awarded": len(results),
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
