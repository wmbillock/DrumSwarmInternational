"""V1 API — Evolution routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_db_session

router = APIRouter(prefix="/api/v1")


@router.get("/evolution/selection-events")
def v1_selection_events(performer_id: Optional[str] = None, limit: int = 50):
    """Get selection/drafting events — session assignments linking performers to roles."""
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition
    from backend.models.performer import Performer

    db = _get_db_session()
    try:
        query = (
            db.query(AgentSession, AgentDefinition.role, AgentDefinition.nickname, Performer)
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .join(Performer, AgentSession.performer_id == Performer.id)
        )
        if performer_id:
            query = query.filter(AgentSession.performer_id == performer_id)
        results = query.order_by(AgentSession.started_at.desc()).limit(limit).all()
        return [{
            "session_id": session.id,
            "performer_id": performer.id,
            "performer_name": performer.name,
            "role": role,
            "nickname": nickname,
            "corps_id": session.corps_id,
            "status": session.status.value,
            "trust_score": round(performer.trust_score, 1),
            "started_at": session.started_at.isoformat() if session.started_at else None,
        } for session, role, nickname, performer in results]
    finally:
        db.close()


@router.get("/evolution/mutations")
def v1_mutations(limit: int = 50):
    """Get recent mutation/ledger entries across all performers."""
    from backend.models.capability_ledger import CapabilityLedgerEntry

    db = _get_db_session()
    try:
        entries = (
            db.query(CapabilityLedgerEntry)
            .order_by(CapabilityLedgerEntry.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{
            "id": e.id,
            "performer_id": e.performer_id,
            "entry_type": e.entry_type.value,
            "role_type": e.role_type,
            "score": e.score,
            "trust_before": e.trust_before,
            "trust_after": e.trust_after,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        } for e in entries]
    finally:
        db.close()


@router.post("/evolution/simulate-mutation")
def v1_simulate_mutation(payload: dict):
    """Simulate a mutation on an agent definition."""
    from backend.models.agent_definition import AgentDefinition
    db = _get_db_session()
    try:
        def_id = payload.get("definition_id")
        changes = payload.get("changes", {})
        reason = payload.get("reason", "manual simulation")
        defn = db.query(AgentDefinition).filter(AgentDefinition.id == def_id).first()
        if not defn:
            raise HTTPException(404, "Agent definition not found")
        preview = {
            "definition_id": def_id,
            "current_role": defn.role,
            "current_system_prompt": defn.system_prompt[:200] if defn.system_prompt else None,
            "proposed_changes": changes,
            "reason": reason,
            "status": "simulated",
        }
        return preview
    finally:
        db.close()
