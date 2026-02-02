"""V1 API — Staff marketplace routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _validate_id, _get_db_session
from backend.api.v1.schemas import HireStaffRequest, ReleaseStaffRequest

router = APIRouter(prefix="/api/v1")


@router.get("/staff/marketplace")
def v1_list_staff_marketplace():
    """List all non-retired performers available in the marketplace."""
    from backend.models.performer import Performer, PerformerStatus

    db = _get_db_session()
    try:
        performers = (
            db.query(Performer)
            .filter(Performer.status != PerformerStatus.RETIRED)
            .order_by(Performer.trust_score.desc())
            .all()
        )
        return {
            "performers": [
                {
                    "id": p.id,
                    "name": p.name,
                    "role_type": p.role_type,
                    "trust_score": p.trust_score,
                    "total_sessions": p.total_sessions,
                    "successful_sessions": p.successful_sessions,
                    "failed_sessions": p.failed_sessions,
                    "status": p.status.value if p.status else None,
                    "age": p.age,
                    "experience_seasons": p.experience_seasons,
                    "specialties": p.specialties,
                }
                for p in performers
            ],
            "count": len(performers),
        }
    finally:
        db.close()


@router.get("/staff/{performer_id}/profile")
def v1_get_staff_profile(performer_id: str):
    """Detailed performer profile including capability ledger and experience."""
    from backend.models.performer import Performer
    from backend.models.capability_ledger import CapabilityLedger
    from backend.models.agent_experience import AgentExperience

    _validate_id(performer_id, "performer_id")

    db = _get_db_session()
    try:
        performer = db.query(Performer).filter(Performer.id == performer_id).first()
        if not performer:
            raise HTTPException(404, f"Performer {performer_id} not found")

        ledger_entries = (
            db.query(CapabilityLedger)
            .filter(CapabilityLedger.performer_id == performer_id)
            .order_by(CapabilityLedger.created_at.desc())
            .limit(20)
            .all()
        )

        experiences = (
            db.query(AgentExperience)
            .filter(AgentExperience.performer_id == performer_id)
            .all()
        )

        return {
            "id": performer.id,
            "name": performer.name,
            "role_type": performer.role_type,
            "trust_score": performer.trust_score,
            "total_sessions": performer.total_sessions,
            "successful_sessions": performer.successful_sessions,
            "failed_sessions": performer.failed_sessions,
            "status": performer.status.value if performer.status else None,
            "age": performer.age,
            "experience_seasons": performer.experience_seasons,
            "specialties": performer.specialties,
            "capability_ledger": [
                {
                    "id": entry.id,
                    "capability": entry.capability,
                    "delta": entry.delta,
                    "reason": entry.reason,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                }
                for entry in ledger_entries
            ],
            "experiences": [
                {
                    "id": exp.id,
                    "corps_id": exp.corps_id,
                    "role": exp.role,
                    "season": exp.season,
                    "outcome": exp.outcome,
                    "notes": exp.notes,
                }
                for exp in experiences
            ],
        }
    finally:
        db.close()
