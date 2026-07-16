"""V1 API — Reps routes."""

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_db_session
from backend.api.v1.schemas import RepCreateRequest, RepTransitionRequest, ScoreCreateRequest

router = APIRouter(prefix="/api/v1")


@router.get("/reps/{rep_id}/critique")
def v1_get_critique(rep_id: str):
    """Get critique/feedback for a rep — returns scores and result."""
    from backend.models.rep import Rep
    from backend.models.score import Score
    db = _get_db_session()
    try:
        rep = db.get(Rep, rep_id)
        if not rep:
            raise HTTPException(404, "Rep not found")
        scores = db.query(Score).filter(Score.rep_id == rep_id).all()
        return {
            "id": rep.id,
            "segment_id": rep.segment_id,
            "status": rep.status.value,
            "assigned_to": rep.assigned_to,
            "result": rep.result,
            "scores": [{
                "id": s.id,
                "judge_type": s.judge_type.value if s.judge_type else None,
                "value": s.value,
                "box": s.box,
                "feedback": s.feedback,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            } for s in scores],
            "created_at": rep.created_at.isoformat() if rep.created_at else None,
        }
    finally:
        db.close()


@router.post("/reps")
def v1_create_rep(data: RepCreateRequest):
    from backend.services.rep_service import create_rep
    db = _get_db_session()
    try:
        rep = create_rep(db, segment_id=data.segment_id)
        return {"id": rep.id, "status": rep.status.value, "segment_id": rep.segment_id}
    finally:
        db.close()


@router.post("/reps/{rep_id}/transition")
def v1_transition_rep(rep_id: str, data: RepTransitionRequest):
    from backend.models.rep import RepStatus
    from backend.services.rep_service import transition_rep, InvalidRepTransition
    db = _get_db_session()
    try:
        rep = transition_rep(
            db, rep_id=rep_id, new_status=RepStatus(data.new_status),
            assigned_to=data.assigned_to, result=data.result, error=data.error,
        )
        return {"id": rep.id, "status": rep.status.value}
    except (ValueError, InvalidRepTransition) as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.get("/reps/{rep_id}/scores")
def v1_get_scores_for_rep(rep_id: str):
    from backend.services.scoring_service import get_scores_for_rep
    db = _get_db_session()
    try:
        scores = get_scores_for_rep(db, rep_id)
        return [{"id": s.id, "judge_type": s.judge_type.value, "value": s.value,
                 "box": s.box, "feedback": s.feedback} for s in scores]
    finally:
        db.close()


@router.get("/reps/{rep_id}/composite")
def v1_get_composite(rep_id: str):
    from backend.services.scoring_service import compute_composite
    db = _get_db_session()
    try:
        result = compute_composite(db, corps_id="default", rep_id=rep_id)
        return {
            "raw_total": result.raw_total,
            "penalties_total": result.penalties_total,
            "final_score": result.final_score,
            "needs_rework": result.needs_rework,
            "needs_escalation": result.needs_escalation,
        }
    finally:
        db.close()


@router.post("/scores")
def v1_create_score(data: ScoreCreateRequest):
    from backend.models.score import JudgeType
    from backend.services.scoring_service import record_score, InvalidScore
    db = _get_db_session()
    try:
        score = record_score(
            db, corps_id="default", judge_type=JudgeType(data.judge_type),
            value=data.value, box=data.box, rep_id=data.rep_id,
            segment_id=data.segment_id, feedback=data.feedback,
        )
        return {"id": score.id, "value": score.value, "box": score.box}
    except (ValueError, InvalidScore) as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()
