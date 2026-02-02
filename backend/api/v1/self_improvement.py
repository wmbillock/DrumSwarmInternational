"""V1 API — Self-improvement routes."""

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_db_session
from backend.api.v1.schemas import SelfImprovementProposalRequest, ImprovementActionRequest

router = APIRouter(prefix="/api/v1")


@router.post("/self-improvement/propose")
def v1_propose_improvement(data: SelfImprovementProposalRequest):
    from backend.services.lifecycle_manager import propose_self_improvement
    db = _get_db_session()
    try:
        log = propose_self_improvement(db, data.definition_id, data.changes, data.reason)
        return {"id": log.id, "status": log.status.value}
    finally:
        db.close()


@router.post("/self-improvement/{proposal_id}/approve")
def v1_approve_improvement(proposal_id: str, data: ImprovementActionRequest):
    from backend.services.lifecycle_manager import approve_self_improvement
    db = _get_db_session()
    try:
        defn = approve_self_improvement(db, proposal_id, data.approver_session_id)
        return {"id": defn.id, "role": defn.role, "version": defn.version}
    finally:
        db.close()


@router.post("/self-improvement/{proposal_id}/reject")
def v1_reject_improvement(proposal_id: str, data: ImprovementActionRequest):
    from backend.services.lifecycle_manager import reject_self_improvement
    db = _get_db_session()
    try:
        log = reject_self_improvement(db, proposal_id, data.approver_session_id)
        return {"id": log.id, "status": log.status.value}
    finally:
        db.close()


@router.get("/self-improvement/pending")
def v1_pending_improvements():
    from backend.models.self_improvement_log import SelfImprovementLog, ImprovementStatus
    from backend.models.agent_definition import AgentDefinition
    db = _get_db_session()
    try:
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
    finally:
        db.close()
