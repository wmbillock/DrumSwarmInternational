"""Legacy scoring endpoints extracted from app.py."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.app import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Schemas ---

class ScoreCreate(BaseModel):
    judge_type: str
    value: float
    box: int
    rep_id: Optional[str] = None
    segment_id: Optional[str] = None
    feedback: Optional[str] = None


# --- Score endpoints ---

@router.post("/api/scores")
def api_create_score(data: ScoreCreate, db: Session = Depends(get_db)):
    from backend.models.score import JudgeType
    from backend.services.scoring_service import record_score, InvalidScore
    try:
        score = record_score(
            db, corps_id="default", judge_type=JudgeType(data.judge_type),
            value=data.value, box=data.box, rep_id=data.rep_id,
            segment_id=data.segment_id, feedback=data.feedback,
        )
        return {"id": score.id, "value": score.value, "box": score.box}
    except (ValueError, InvalidScore) as e:
        raise HTTPException(400, str(e))


@router.get("/api/reps/{rep_id}/scores")
def api_get_scores_for_rep(rep_id: str, db: Session = Depends(get_db)):
    from backend.services.scoring_service import get_scores_for_rep
    scores = get_scores_for_rep(db, rep_id)
    return [{"id": s.id, "judge_type": s.judge_type.value, "value": s.value,
             "box": s.box, "feedback": s.feedback} for s in scores]


@router.get("/api/reps/{rep_id}/composite")
def api_get_composite(rep_id: str, db: Session = Depends(get_db)):
    from backend.services.scoring_service import compute_composite
    result = compute_composite(db, corps_id="default", rep_id=rep_id)
    return {
        "raw_total": result.raw_total,
        "penalties_total": result.penalties_total,
        "final_score": result.final_score,
        "needs_rework": result.needs_rework,
        "needs_escalation": result.needs_escalation,
    }
