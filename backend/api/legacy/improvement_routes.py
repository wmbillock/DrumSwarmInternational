"""Legacy improvement/basics/critique/banquet/self-improvement endpoints extracted from app.py."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.app import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Schemas ---

class SelfImprovementProposal(BaseModel):
    definition_id: str
    changes: dict
    reason: str

class ImprovementAction(BaseModel):
    approver_session_id: str


# --- Improvement endpoints ---

@router.post("/api/corps/{corps_id}/basics/{caption}")
def api_run_basics(corps_id: str, caption: str, db: Session = Depends(get_db)):
    from backend.services.improvement import run_basics
    result = run_basics(db, corps_id, caption)
    return {
        "caption": result.caption,
        "definitions_reviewed": result.definitions_reviewed,
        "improvements_suggested": result.improvements_suggested,
        "suggestions": result.suggestions,
    }


@router.get("/api/reps/{rep_id}/critique")
def api_run_critique(rep_id: str, corps_id: str = "default", db: Session = Depends(get_db)):
    from backend.services.improvement import run_critique
    result = run_critique(db, rep_id, corps_id)
    return {
        "rep_id": result.rep_id,
        "overall_assessment": result.overall_assessment,
        "needs_rework": result.needs_rework,
        "feedbacks": [
            {"judge_type": f.judge_type.value, "score": f.score_value,
             "strengths": f.strengths, "weaknesses": f.weaknesses,
             "action_items": f.action_items}
            for f in result.feedbacks
        ],
    }


@router.get("/api/corps/{corps_id}/banquet")
def api_run_banquet(corps_id: str, db: Session = Depends(get_db)):
    from backend.services.improvement import run_banquet
    report = run_banquet(db, corps_id)
    return {
        "corps_id": report.corps_id,
        "total_reps": report.total_reps,
        "completed_reps": report.completed_reps,
        "failed_reps": report.failed_reps,
        "average_score": report.average_score,
        "top_caption": report.top_caption,
        "what_worked": report.what_worked,
        "what_failed": report.what_failed,
        "improvements": report.improvements,
    }


# --- Self-improvement ---

@router.post("/api/self-improvement/propose")
def api_propose_improvement(data: SelfImprovementProposal, db: Session = Depends(get_db)):
    from backend.services.lifecycle_manager import propose_self_improvement
    log = propose_self_improvement(db, data.definition_id, data.changes, data.reason)
    return {"id": log.id, "status": log.status.value}


@router.post("/api/self-improvement/{proposal_id}/approve")
def api_approve_improvement(proposal_id: str, data: ImprovementAction, db: Session = Depends(get_db)):
    from backend.services.lifecycle_manager import approve_self_improvement
    defn = approve_self_improvement(db, proposal_id, data.approver_session_id)
    return {"id": defn.id, "role": defn.role, "version": defn.version}


@router.post("/api/self-improvement/{proposal_id}/reject")
def api_reject_improvement(proposal_id: str, data: ImprovementAction, db: Session = Depends(get_db)):
    from backend.services.lifecycle_manager import reject_self_improvement
    log = reject_self_improvement(db, proposal_id, data.approver_session_id)
    return {"id": log.id, "status": log.status.value}


@router.get("/api/self-improvement/pending")
def api_pending_improvements(db: Session = Depends(get_db)):
    from backend.models.self_improvement_log import SelfImprovementLog, ImprovementStatus
    from backend.models.agent_definition import AgentDefinition
    logs = db.query(SelfImprovementLog).filter(
        SelfImprovementLog.status == ImprovementStatus.PENDING
    ).all()
    result = []
    for log in logs:
        defn = db.get(AgentDefinition, log.agent_definition_id)
        result.append({
            "id": log.id,
            "role": defn.role if defn else "unknown",
            "nickname": defn.nickname if defn else None,
            "old_version": log.old_version,
            "new_version": log.new_version,
            "changes": log.changes,
            "reason": log.reason,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return result
