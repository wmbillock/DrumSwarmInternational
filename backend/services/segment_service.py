from typing import Optional

from sqlalchemy.orm import Session

from backend.models.segment import Segment, SegmentStatus, SegmentType


# Valid parent-child type relationships
VALID_CHILD_TYPES: dict[SegmentType, set[SegmentType]] = {
    SegmentType.SHOW: {SegmentType.MOVEMENT},
    SegmentType.MOVEMENT: {SegmentType.SET},
    SegmentType.SET: {SegmentType.SEGMENT},
    SegmentType.SEGMENT: set(),  # leaf node
}


class InvalidSegmentStructure(Exception):
    pass


class InvalidStatusTransition(Exception):
    pass


def create_segment(
    db: Session,
    type: SegmentType,
    title: str,
    description: Optional[str] = None,
    parent_id: Optional[str] = None,
    caption: Optional[str] = None,
) -> Segment:
    if parent_id is not None:
        parent = db.get(Segment, parent_id)
        if parent is None:
            raise InvalidSegmentStructure(f"Parent {parent_id} not found")
        if type not in VALID_CHILD_TYPES[parent.type]:
            raise InvalidSegmentStructure(
                f"Cannot add {type.value} as child of {parent.type.value}"
            )

    if parent_id is None and type != SegmentType.SHOW:
        raise InvalidSegmentStructure(
            f"Only shows can be root segments, got {type.value}"
        )

    coord = Segment(
        type=type,
        title=title,
        description=description,
        parent_id=parent_id,
        caption=caption,
    )
    db.add(coord)
    db.commit()
    db.refresh(coord)
    return coord


def get_segment(db: Session, segment_id: str) -> Optional[Segment]:
    return db.get(Segment, segment_id)


def get_children(db: Session, segment_id: str) -> list[Segment]:
    return (
        db.query(Segment)
        .filter(Segment.parent_id == segment_id)
        .all()
    )


def rollup_status(db: Session, segment_id: str) -> SegmentStatus:
    """Compute a parent's status from its children's statuses.

    Rules:
    - If all children are completed → completed
    - If any child is failed and none are in_progress/review → failed
    - If any child is in_progress or review → in_progress
    - If any child is blocked → blocked (unless others are in_progress)
    - Otherwise → pending
    """
    children = get_children(db, segment_id)
    if not children:
        # Leaf node — status is self-determined, not rolled up
        coord = db.get(Segment, segment_id)
        return coord.status if coord else SegmentStatus.PENDING

    child_statuses = {c.status for c in children}

    if child_statuses == {SegmentStatus.COMPLETED}:
        return SegmentStatus.COMPLETED

    if SegmentStatus.IN_PROGRESS in child_statuses or SegmentStatus.REVIEW in child_statuses:
        return SegmentStatus.IN_PROGRESS

    if SegmentStatus.BLOCKED in child_statuses:
        return SegmentStatus.BLOCKED

    if SegmentStatus.FAILED in child_statuses:
        has_pending = SegmentStatus.PENDING in child_statuses
        if has_pending:
            return SegmentStatus.IN_PROGRESS
        return SegmentStatus.FAILED

    return SegmentStatus.PENDING


def update_status_from_children(db: Session, segment_id: str) -> Segment:
    """Recompute and persist a segment's status from its children, then propagate up."""
    coord = db.get(Segment, segment_id)
    if coord is None:
        raise ValueError(f"Segment {segment_id} not found")

    new_status = rollup_status(db, segment_id)
    coord.status = new_status
    db.commit()
    db.refresh(coord)

    # Propagate up the tree
    if coord.parent_id is not None:
        update_status_from_children(db, coord.parent_id)

    return coord
