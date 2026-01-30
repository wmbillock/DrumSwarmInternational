from typing import Optional

from sqlalchemy.orm import Session

from backend.models.coordinate import Coordinate, CoordinateStatus, CoordinateType


# Valid parent-child type relationships
VALID_CHILD_TYPES: dict[CoordinateType, set[CoordinateType]] = {
    CoordinateType.SHOW: {CoordinateType.MOVEMENT},
    CoordinateType.MOVEMENT: {CoordinateType.SET},
    CoordinateType.SET: {CoordinateType.COORDINATE},
    CoordinateType.COORDINATE: set(),  # leaf node
}


class InvalidCoordinateStructure(Exception):
    pass


class InvalidStatusTransition(Exception):
    pass


def create_coordinate(
    db: Session,
    type: CoordinateType,
    title: str,
    description: Optional[str] = None,
    parent_id: Optional[str] = None,
    caption: Optional[str] = None,
) -> Coordinate:
    if parent_id is not None:
        parent = db.get(Coordinate, parent_id)
        if parent is None:
            raise InvalidCoordinateStructure(f"Parent {parent_id} not found")
        if type not in VALID_CHILD_TYPES[parent.type]:
            raise InvalidCoordinateStructure(
                f"Cannot add {type.value} as child of {parent.type.value}"
            )

    if parent_id is None and type != CoordinateType.SHOW:
        raise InvalidCoordinateStructure(
            f"Only shows can be root coordinates, got {type.value}"
        )

    coord = Coordinate(
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


def get_coordinate(db: Session, coordinate_id: str) -> Optional[Coordinate]:
    return db.get(Coordinate, coordinate_id)


def get_children(db: Session, coordinate_id: str) -> list[Coordinate]:
    return (
        db.query(Coordinate)
        .filter(Coordinate.parent_id == coordinate_id)
        .all()
    )


def rollup_status(db: Session, coordinate_id: str) -> CoordinateStatus:
    """Compute a parent's status from its children's statuses.

    Rules:
    - If all children are completed → completed
    - If any child is failed and none are in_progress/review → failed
    - If any child is in_progress or review → in_progress
    - If any child is blocked → blocked (unless others are in_progress)
    - Otherwise → pending
    """
    children = get_children(db, coordinate_id)
    if not children:
        # Leaf node — status is self-determined, not rolled up
        coord = db.get(Coordinate, coordinate_id)
        return coord.status if coord else CoordinateStatus.PENDING

    child_statuses = {c.status for c in children}

    if child_statuses == {CoordinateStatus.COMPLETED}:
        return CoordinateStatus.COMPLETED

    if CoordinateStatus.IN_PROGRESS in child_statuses or CoordinateStatus.REVIEW in child_statuses:
        return CoordinateStatus.IN_PROGRESS

    if CoordinateStatus.BLOCKED in child_statuses:
        return CoordinateStatus.BLOCKED

    if CoordinateStatus.FAILED in child_statuses:
        has_pending = CoordinateStatus.PENDING in child_statuses
        if has_pending:
            return CoordinateStatus.IN_PROGRESS
        return CoordinateStatus.FAILED

    return CoordinateStatus.PENDING


def update_status_from_children(db: Session, coordinate_id: str) -> Coordinate:
    """Recompute and persist a coordinate's status from its children, then propagate up."""
    coord = db.get(Coordinate, coordinate_id)
    if coord is None:
        raise ValueError(f"Coordinate {coordinate_id} not found")

    new_status = rollup_status(db, coordinate_id)
    coord.status = new_status
    db.commit()
    db.refresh(coord)

    # Propagate up the tree
    if coord.parent_id is not None:
        update_status_from_children(db, coord.parent_id)

    return coord
