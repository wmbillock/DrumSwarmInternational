"""V1 API — Performers routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_db_session

router = APIRouter(prefix="/api/v1")


@router.get("/performers")
def v1_list_performers(
    status: Optional[str] = None,
    category: Optional[str] = None,
    staff_only: bool = False,
    performers_only: bool = False,
):
    """List performers with optional status/category filters.

    Query params:
    - status: active, probation, retired
    - category: performer, instructional_staff, administrative_staff
    - staff_only: true — only verified staff
    - performers_only: true — only unverified performers (excludes staff)
    """
    from backend.models.performer import PerformerStatus
    from backend.services.performer_service import list_performers

    ps = None
    if status:
        try:
            ps = PerformerStatus(status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    db = _get_db_session()
    try:
        performers = list_performers(
            db, status=ps, category=category,
            staff_only=staff_only, performers_only=performers_only,
        )
        return [{
            "id": p.id,
            "name": p.name,
            "role_type": p.role_type,
            "trust_score": round(p.trust_score, 1),
            "total_sessions": p.total_sessions,
            "successful_sessions": p.successful_sessions,
            "failed_sessions": p.failed_sessions,
            "status": p.status.value,
            "agent_category": getattr(p, "agent_category", "performer"),
            "is_verified": getattr(p, "is_verified", False),
            "retirement_reason": p.retirement_reason,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        } for p in performers]
    finally:
        db.close()


@router.get("/performers/{performer_id}")
def v1_get_performer(performer_id: str):
    """Get performer detail."""
    from backend.services.performer_service import get_performer

    db = _get_db_session()
    try:
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
            "agent_category": getattr(p, "agent_category", "performer"),
            "is_verified": getattr(p, "is_verified", False),
            "verified_at": p.verified_at.isoformat() if getattr(p, "verified_at", None) else None,
            "verified_by": getattr(p, "verified_by", None),
            "specialties": p.specialties,
            "retirement_reason": p.retirement_reason,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
    finally:
        db.close()


@router.post("/performers/{performer_id}/retire")
def v1_retire_performer(performer_id: str):
    """Retire a performer."""
    from backend.services.performer_service import retire_performer

    db = _get_db_session()
    try:
        p = retire_performer(db, performer_id, reason="Manual retirement via API")
        return {"id": p.id, "name": p.name, "status": p.status.value}
    except ValueError as e:
        raise HTTPException(404, str(e))
    finally:
        db.close()


@router.get("/performers/{performer_id}/ledger")
def v1_performer_ledger(performer_id: str):
    """Get capability ledger entries for a performer."""
    from backend.services.capability_ledger_service import get_entries_for_performer

    db = _get_db_session()
    try:
        entries = get_entries_for_performer(db, performer_id)
        return [{
            "id": e.id,
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


@router.get("/performers/{performer_id}/stats")
def v1_performer_stats(performer_id: str):
    """Get aggregate stats from the capability ledger."""
    from backend.services.capability_ledger_service import get_performer_stats

    db = _get_db_session()
    try:
        return get_performer_stats(db, performer_id)
    finally:
        db.close()


@router.get("/performers/{performer_id}/genome")
def v1_performer_genome(performer_id: str):
    """Get performer genome (evolution traits)."""
    from backend.models.performer import Performer

    db = _get_db_session()
    try:
        p = db.get(Performer, performer_id)
        if not p:
            raise HTTPException(404, "Performer not found")
        return {
            "id": p.id,
            "name": p.name,
            "role_type": p.role_type,
            "trust_score": round(p.trust_score, 1),
            "specialties": p.specialties,
            "genome": p.genome if hasattr(p, "genome") else {},
        }
    finally:
        db.close()
