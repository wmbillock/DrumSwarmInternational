"""Legacy segment and rep endpoints extracted from app.py."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.app import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Schemas ---

class SegmentCreate(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    caption: Optional[str] = None

class RepCreate(BaseModel):
    segment_id: str

class RepTransition(BaseModel):
    new_status: str
    assigned_to: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None


# --- Segment endpoints ---

@router.post("/api/segments")
def api_create_segment(data: SegmentCreate, db: Session = Depends(get_db)):
    from backend.models.segment import SegmentType
    from backend.services.segment_service import create_segment, InvalidSegmentStructure
    try:
        coord = create_segment(
            db, type=SegmentType(data.type), title=data.title,
            description=data.description, parent_id=data.parent_id, caption=data.caption,
        )
        return {"id": coord.id, "type": coord.type.value, "title": coord.title,
                "status": coord.status.value}
    except (ValueError, InvalidSegmentStructure) as e:
        raise HTTPException(400, str(e))


@router.get("/api/segments/{coord_id}")
def api_get_segment(coord_id: str, db: Session = Depends(get_db)):
    from backend.services.segment_service import get_segment
    coord = get_segment(db, coord_id)
    if not coord:
        raise HTTPException(404, "Segment not found")
    return {"id": coord.id, "type": coord.type.value, "title": coord.title,
            "status": coord.status.value, "parent_id": coord.parent_id,
            "caption": coord.caption, "description": coord.description}


@router.get("/api/segments/{coord_id}/children")
def api_get_segment_children(coord_id: str, db: Session = Depends(get_db)):
    from backend.services.segment_service import get_children
    children = get_children(db, coord_id)
    return [{"id": c.id, "type": c.type.value, "title": c.title,
             "status": c.status.value} for c in children]


@router.get("/api/segments/{coord_id}/tree")
def api_get_segment_tree(coord_id: str, db: Session = Depends(get_db)):
    """Get full segment tree with reps for a given root."""
    from backend.services.segment_service import get_segment, get_children
    from backend.services.rep_service import get_reps_for_segment

    def _build(cid):
        coord = get_segment(db, cid)
        if not coord:
            return None
        reps = get_reps_for_segment(db, cid)
        children = get_children(db, cid)
        return {
            "id": coord.id,
            "type": coord.type.value,
            "title": coord.title,
            "description": coord.description,
            "status": coord.status.value,
            "caption": coord.caption,
            "reps": [{"id": r.id, "status": r.status.value, "result": r.result, "error": r.error, "assigned_to": r.assigned_to} for r in reps],
            "children": [_build(c.id) for c in children],
        }

    tree = _build(coord_id)
    if not tree:
        raise HTTPException(404, "Segment not found")
    return tree


@router.get("/api/segments/{coord_id}/reps")
def api_get_reps_for_segment(coord_id: str, db: Session = Depends(get_db)):
    from backend.services.rep_service import get_reps_for_segment
    reps = get_reps_for_segment(db, coord_id)
    return [{"id": r.id, "status": r.status.value, "assigned_to": r.assigned_to,
             "result": r.result, "error": r.error} for r in reps]


# --- Rep endpoints ---

@router.post("/api/reps")
def api_create_rep(data: RepCreate, db: Session = Depends(get_db)):
    from backend.services.rep_service import create_rep
    rep = create_rep(db, segment_id=data.segment_id)
    return {"id": rep.id, "status": rep.status.value, "segment_id": rep.segment_id}


@router.post("/api/reps/{rep_id}/transition")
def api_transition_rep(rep_id: str, data: RepTransition, db: Session = Depends(get_db)):
    from backend.models.rep import RepStatus
    from backend.services.rep_service import transition_rep, InvalidRepTransition
    try:
        rep = transition_rep(
            db, rep_id=rep_id, new_status=RepStatus(data.new_status),
            assigned_to=data.assigned_to, result=data.result, error=data.error,
        )
        return {"id": rep.id, "status": rep.status.value}
    except (ValueError, InvalidRepTransition) as e:
        raise HTTPException(400, str(e))
