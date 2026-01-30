from typing import Optional

from sqlalchemy.orm import Session

from backend.models.coordinate import CoordinateStatus
from backend.models.rep import Rep, RepStatus, VALID_TRANSITIONS
from backend.services.coordinate_service import update_status_from_children


class InvalidRepTransition(Exception):
    pass


def create_rep(
    db: Session,
    coordinate_id: str,
) -> Rep:
    rep = Rep(coordinate_id=coordinate_id)
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return rep


def transition_rep(
    db: Session,
    rep_id: str,
    new_status: RepStatus,
    assigned_to: Optional[str] = None,
    result: Optional[str] = None,
    error: Optional[str] = None,
) -> Rep:
    rep = db.get(Rep, rep_id)
    if rep is None:
        raise ValueError(f"Rep {rep_id} not found")

    if new_status not in VALID_TRANSITIONS[rep.status]:
        raise InvalidRepTransition(
            f"Cannot transition rep from {rep.status.value} to {new_status.value}"
        )

    rep.status = new_status

    if assigned_to is not None:
        rep.assigned_to = assigned_to
    if result is not None:
        rep.result = result
    if error is not None:
        rep.error = error

    db.commit()
    db.refresh(rep)

    # Update the coordinate's status based on its reps
    _sync_coordinate_from_reps(db, rep.coordinate_id)

    return rep


def _sync_coordinate_from_reps(db: Session, coordinate_id: str) -> None:
    """Update a coordinate's status based on its reps' statuses.

    Rules:
    - If any rep is completed → coordinate is completed
    - If any rep is in_progress or assigned → coordinate is in_progress
    - If any rep is in review → coordinate is in review
    - If all reps are failed → coordinate is failed
    - Otherwise → coordinate is pending
    """
    from backend.models.coordinate import Coordinate

    coord = db.get(Coordinate, coordinate_id)
    if coord is None:
        return

    reps = (
        db.query(Rep)
        .filter(Rep.coordinate_id == coordinate_id)
        .all()
    )

    if not reps:
        return

    rep_statuses = {r.status for r in reps}

    if RepStatus.COMPLETED in rep_statuses:
        coord.status = CoordinateStatus.COMPLETED
    elif RepStatus.REVIEW in rep_statuses:
        coord.status = CoordinateStatus.REVIEW
    elif RepStatus.IN_PROGRESS in rep_statuses or RepStatus.ASSIGNED in rep_statuses:
        coord.status = CoordinateStatus.IN_PROGRESS
    elif rep_statuses == {RepStatus.FAILED}:
        coord.status = CoordinateStatus.FAILED
    elif RepStatus.PENDING in rep_statuses:
        coord.status = CoordinateStatus.PENDING

    db.commit()

    # Propagate up the tree
    if coord.parent_id is not None:
        update_status_from_children(db, coord.parent_id)


def get_reps_for_coordinate(db: Session, coordinate_id: str) -> list[Rep]:
    return (
        db.query(Rep)
        .filter(Rep.coordinate_id == coordinate_id)
        .all()
    )
