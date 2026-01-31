"""Shared segment tree walking and formatting utilities."""

from typing import Optional

from sqlalchemy.orm import Session

from backend.services.segment_service import get_segment, get_children
from backend.services.rep_service import get_reps_for_segment


def build_tree_summary(db: Session, root_id: str) -> str:
    """Build a text summary of the segment tree with IDs and statuses."""
    lines: list[str] = []

    def _walk(segment_id: str, indent: int = 0) -> None:
        seg = get_segment(db, segment_id)
        if not seg:
            return
        prefix = "  " * indent
        lines.append(f"{prefix}{seg.type.value}: {seg.title} [id={seg.id}, status={seg.status.value}]")
        for rep in get_reps_for_segment(db, segment_id):
            lines.append(f"{prefix}  rep [id={rep.id}, status={rep.status.value}]")
        for child in get_children(db, segment_id):
            _walk(child.id, indent + 1)

    _walk(root_id)
    return "\n".join(lines) if lines else "(empty tree)"


def build_tree_dict(db: Session, root_id: str) -> Optional[dict]:
    """Build a JSON-serializable dict of the segment tree with reps."""
    seg = get_segment(db, root_id)
    if not seg:
        return None
    reps = get_reps_for_segment(db, root_id)
    children = get_children(db, root_id)
    return {
        "id": seg.id,
        "type": seg.type.value,
        "title": seg.title,
        "description": seg.description,
        "status": seg.status.value,
        "caption": seg.caption,
        "reps": [
            {"id": r.id, "status": r.status.value, "result": r.result,
             "error": r.error, "assigned_to": r.assigned_to}
            for r in reps
        ],
        "children": [build_tree_dict(db, c.id) for c in children],
    }


def count_pending_work(db: Session, root_id: str) -> int:
    """Count pending work: non-terminal reps + leaf segments with no reps."""
    from backend.models.rep import RepStatus

    pending = 0
    checked: set[str] = set()
    stack = [root_id]

    while stack:
        sid = stack.pop()
        if sid in checked:
            continue
        checked.add(sid)

        children = get_children(db, sid)
        for child in children:
            stack.append(child.id)

        seg = get_segment(db, sid)
        reps = get_reps_for_segment(db, sid)

        if reps:
            for rep in reps:
                if rep.status not in (RepStatus.COMPLETED, RepStatus.FAILED):
                    pending += 1
        elif seg and seg.status.value == "pending" and not children:
            pending += 1

    return pending
