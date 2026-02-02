"""V1 API — Segments routes."""

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_db_session
from backend.api.v1.schemas import SegmentCreateRequest

router = APIRouter(prefix="/api/v1")


@router.get("/segments/{segment_id}")
def v1_get_segment(segment_id: str):
    """Get a segment by ID."""
    from backend.services.segment_service import get_segment

    db = _get_db_session()
    try:
        seg = get_segment(db, segment_id)
        if not seg:
            raise HTTPException(404, "Segment not found")
        return {
            "id": seg.id,
            "type": seg.type.value,
            "title": seg.title,
            "status": seg.status.value,
            "parent_id": seg.parent_id,
            "caption": seg.caption,
            "description": seg.description,
        }
    finally:
        db.close()


@router.get("/segments/{segment_id}/children")
def v1_get_segment_children(segment_id: str):
    """Get child segments of a given segment."""
    from backend.services.segment_service import get_children

    db = _get_db_session()
    try:
        children = get_children(db, segment_id)
        return [{
            "id": c.id,
            "type": c.type.value,
            "title": c.title,
            "status": c.status.value,
        } for c in children]
    finally:
        db.close()


@router.get("/segments/{segment_id}/reps")
def v1_get_reps_for_segment(segment_id: str):
    """Get reps for a specific segment."""
    from backend.services.rep_service import get_reps_for_segment

    db = _get_db_session()
    try:
        reps = get_reps_for_segment(db, segment_id)
        return [{"id": r.id, "status": r.status.value, "assigned_to": r.assigned_to,
                 "result": r.result, "error": r.error} for r in reps]
    finally:
        db.close()


@router.get("/segments/{segment_id}/tree")
def v1_get_segment_tree(segment_id: str):
    """Get full segment tree with reps."""
    from backend.services.segment_service import get_segment, get_children
    from backend.services.rep_service import get_reps_for_segment

    db = _get_db_session()
    try:
        def _build(sid):
            seg = get_segment(db, sid)
            if not seg:
                return None
            reps = get_reps_for_segment(db, sid)
            ch = get_children(db, sid)
            return {
                "id": seg.id,
                "type": seg.type.value,
                "title": seg.title,
                "description": seg.description,
                "status": seg.status.value,
                "caption": seg.caption,
                "reps": [{
                    "id": r.id,
                    "status": r.status.value,
                    "result": r.result,
                    "error": r.error,
                    "assigned_to": r.assigned_to,
                } for r in reps],
                "children": [_build(c.id) for c in ch],
            }

        tree = _build(segment_id)
        if not tree:
            raise HTTPException(404, "Segment not found")
        return tree
    finally:
        db.close()


@router.post("/segments")
def v1_create_segment(data: SegmentCreateRequest):
    from backend.models.segment import SegmentType
    from backend.services.segment_service import create_segment, InvalidSegmentStructure
    db = _get_db_session()
    try:
        coord = create_segment(
            db, type=SegmentType(data.type), title=data.title,
            description=data.description, parent_id=data.parent_id, caption=data.caption,
        )
        return {"id": coord.id, "type": coord.type.value, "title": coord.title, "status": coord.status.value}
    except (ValueError, InvalidSegmentStructure) as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()
