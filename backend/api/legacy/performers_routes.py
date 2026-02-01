"""Legacy performer endpoints extracted from app.py."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.app import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/performers")
def api_list_performers(status: Optional[str] = None, db: Session = Depends(get_db)):
    from backend.models.performer import Performer, PerformerStatus
    from backend.services.performer_service import list_performers

    ps = None
    if status:
        try:
            ps = PerformerStatus(status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    performers = list_performers(db, status=ps)
    return [
        {
            "id": p.id,
            "name": p.name,
            "role_type": p.role_type,
            "trust_score": round(p.trust_score, 1),
            "total_sessions": p.total_sessions,
            "successful_sessions": p.successful_sessions,
            "failed_sessions": p.failed_sessions,
            "status": p.status.value,
            "retirement_reason": p.retirement_reason,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in performers
    ]


@router.get("/api/performers/{performer_id}")
def api_get_performer(performer_id: str, db: Session = Depends(get_db)):
    from backend.services.performer_service import get_performer
    p = get_performer(db, performer_id)
    if not p:
        raise HTTPException(404, "Performer not found")
    return {
        "id": p.id,
        "name": p.name,
        "role_type": p.role_type,
        "trust_score": round(p.trust_score, 1),
        "total_sessions": p.total_sessions,
        "successful_sessions": p.successful_sessions,
        "failed_sessions": p.failed_sessions,
        "status": p.status.value,
        "specialties": p.specialties,
        "retirement_reason": p.retirement_reason,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.post("/api/performers/{performer_id}/retire")
def api_retire_performer(performer_id: str, db: Session = Depends(get_db)):
    from backend.services.performer_service import retire_performer
    try:
        p = retire_performer(db, performer_id, reason="Manual retirement via API")
        return {"id": p.id, "name": p.name, "status": p.status.value}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/api/performers/{performer_id}/ledger")
def api_performer_ledger(performer_id: str, db: Session = Depends(get_db)):
    """Get capability ledger entries for a performer."""
    from backend.services.capability_ledger_service import get_entries_for_performer
    entries = get_entries_for_performer(db, performer_id)
    return [
        {
            "id": e.id,
            "entry_type": e.entry_type.value,
            "role_type": e.role_type,
            "score": e.score,
            "trust_before": e.trust_before,
            "trust_after": e.trust_after,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


@router.get("/api/performers/{performer_id}/stats")
def api_performer_stats(performer_id: str, db: Session = Depends(get_db)):
    """Get aggregate stats from the capability ledger."""
    from backend.services.capability_ledger_service import get_performer_stats
    return get_performer_stats(db, performer_id)
