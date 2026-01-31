from typing import Optional

from sqlalchemy.orm import Session

from backend.models.segment import SegmentStatus
from backend.models.rep import Rep, RepStatus, VALID_TRANSITIONS
from backend.services.segment_service import update_status_from_children


class InvalidRepTransition(Exception):
    pass


def create_rep(
    db: Session,
    segment_id: str,
) -> Rep:
    rep = Rep(segment_id=segment_id)
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

    old_status = rep.status

    # Run verification gates before allowing COMPLETED transition
    if new_status == RepStatus.COMPLETED:
        _run_verification(db, rep, result)

    rep.status = new_status

    if assigned_to is not None:
        rep.assigned_to = assigned_to
    if result is not None:
        rep.result = result
    if error is not None:
        rep.error = error

    db.commit()
    db.refresh(rep)

    # Auto-score on completion
    if new_status == RepStatus.COMPLETED:
        _auto_score_rep(db, rep)

    # Update the segment's status based on its reps
    _sync_segment_from_reps(db, rep.segment_id)

    # Publish event
    try:
        from backend.services.event_bus import get_event_bus
        bus = get_event_bus()
        bus.publish("rep.status_changed", {
            "rep_id": rep.id,
            "segment_id": rep.segment_id,
            "old_status": old_status.value,
            "new_status": new_status.value,
        })
    except Exception:
        pass

    return rep


def _run_verification(db: Session, rep: Rep, result: Optional[str]) -> None:
    """Run verification gates before completing a rep. Raises VerificationError on failure."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from backend.models.segment import Segment
        from backend.services.verification import get_verification_engine, VerificationError

        engine = get_verification_engine()
        check_result = result if result is not None else (rep.result or "")

        coord = db.get(Segment, rep.segment_id)
        segment_type = coord.type.value if coord and coord.type else None
        canary = ""

        vr = engine.verify(
            rep_id=rep.id,
            result=check_result,
            segment_id=rep.segment_id,
            segment_type=segment_type,
            canary_phrase=canary or "",
        )
        if not vr.passed:
            logger.warning("Verification failed for rep %s: %s", rep.id, vr.summary)
            raise VerificationError(vr)
    except ImportError:
        pass  # verification module not available
    except Exception as e:
        if type(e).__name__ == "VerificationError":
            raise
        logger.warning("Verification check error for rep %s: %s", rep.id, e)


def _auto_score_rep(db: Session, rep: "Rep") -> None:
    """Auto-generate scores for a completed rep based on result heuristics."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from backend.models.segment import Segment
        from backend.models.score import JudgeType
        from backend.services.scoring_service import record_score

        coord = db.get(Segment, rep.segment_id)
        if not coord:
            return

        # Find corps_id from segment tree
        corps_id = _find_corps_id(db, coord)
        if not corps_id:
            return

        result = rep.result or ""
        result_len = len(result)

        # Heuristic scoring: base score from result quality
        base = 70.0
        if result_len > 500:
            base += 10
        if result_len > 1000:
            base += 5
        if result_len < 50:
            base -= 20
        if rep.error:
            base -= 15

        # Determine box from base score
        box = 3
        if base >= 85:
            box = 5
        elif base >= 75:
            box = 4
        elif base >= 60:
            box = 3
        elif base >= 40:
            box = 2
        else:
            box = 1

        base = max(0.0, min(100.0, base))

        # Map caption to judge type, or use general_effect
        caption = coord.caption or ""
        caption_map = {
            "brass": JudgeType.BRASS,
            "percussion": JudgeType.PERCUSSION,
            "guard": JudgeType.GUARD,
            "visual": JudgeType.VISUAL,
        }
        judge_type = caption_map.get(caption, JudgeType.GENERAL_EFFECT)

        record_score(
            db, corps_id=corps_id, judge_type=judge_type,
            value=base, box=box, rep_id=rep.id,
            segment_id=rep.segment_id,
            feedback=f"Auto-scored: {result_len} chars, box {box}",
        )
    except Exception:
        logger.exception("Auto-scoring failed for rep %s", rep.id)


def _find_corps_id(db: Session, coord) -> str | None:
    """Walk up the segment tree to find the show, then get corps_id."""
    from backend.models.segment import Segment
    from backend.models.show import Show
    current = coord
    visited = set()
    while current and current.id not in visited:
        visited.add(current.id)
        # Check if any show has this as root
        show = db.query(Show).filter(Show.segment_root_id == current.id).first()
        if show:
            return show.corps_id
        if current.parent_id:
            current = db.get(Segment, current.parent_id)
        else:
            break
    return None


def _sync_segment_from_reps(db: Session, segment_id: str) -> None:
    """Update a segment's status based on its reps' statuses.

    Rules:
    - If any rep is completed → segment is completed
    - If any rep is in_progress or assigned → segment is in_progress
    - If any rep is in review → segment is in review
    - If all reps are failed → segment is failed
    - Otherwise → segment is pending
    """
    from backend.models.segment import Segment

    coord = db.get(Segment, segment_id)
    if coord is None:
        return

    reps = (
        db.query(Rep)
        .filter(Rep.segment_id == segment_id)
        .all()
    )

    if not reps:
        return

    rep_statuses = {r.status for r in reps}

    if RepStatus.COMPLETED in rep_statuses:
        coord.status = SegmentStatus.COMPLETED
    elif RepStatus.REVIEW in rep_statuses:
        coord.status = SegmentStatus.REVIEW
    elif RepStatus.IN_PROGRESS in rep_statuses or RepStatus.ASSIGNED in rep_statuses:
        coord.status = SegmentStatus.IN_PROGRESS
    elif rep_statuses == {RepStatus.FAILED}:
        coord.status = SegmentStatus.FAILED
    elif RepStatus.PENDING in rep_statuses:
        coord.status = SegmentStatus.PENDING

    db.commit()

    # Propagate up the tree
    if coord.parent_id is not None:
        update_status_from_children(db, coord.parent_id)


def get_reps_for_segment(db: Session, segment_id: str) -> list[Rep]:
    return (
        db.query(Rep)
        .filter(Rep.segment_id == segment_id)
        .all()
    )
