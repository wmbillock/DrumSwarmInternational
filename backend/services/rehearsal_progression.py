"""Auto-progression engine for rehearsal modes.

Checks milestones for the current mode and advances when criteria are met:
  BASICS → SECTIONALS → FULL_ENSEMBLE → RUN_THROUGH

Called by the task manager on each metronome tick for WINTER_CAMPS corps.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.corps import Corps, CorpsStatus, RehearsalMode
from backend.models.segment import Segment, SegmentType, SegmentStatus
from backend.models.rep import Rep, RepStatus
from backend.models.message import Message

logger = logging.getLogger(__name__)

# Ordered progression
_MODE_ORDER = [
    RehearsalMode.BASICS,
    RehearsalMode.SECTIONALS,
    RehearsalMode.FULL_ENSEMBLE,
    RehearsalMode.RUN_THROUGH,
]


def _next_mode(current: RehearsalMode) -> Optional[RehearsalMode]:
    try:
        idx = _MODE_ORDER.index(current)
        if idx + 1 < len(_MODE_ORDER):
            return _MODE_ORDER[idx + 1]
    except ValueError:
        pass
    return None


def _get_show_for_corps(db: Session, corps_id: str):
    from backend.models.show import Show
    return db.query(Show).filter(Show.corps_id == corps_id).first()


def _basics_met(db: Session, corps_id: str) -> bool:
    """BASICS → SECTIONALS: ED has created >=1 movement, work tree exists."""
    show = _get_show_for_corps(db, corps_id)
    if not show or not show.segment_root_id:
        return False
    movements = (
        db.query(Segment)
        .filter(
            Segment.parent_id == show.segment_root_id,
            Segment.type == SegmentType.MOVEMENT,
        )
        .count()
    )
    return movements >= 1


def _sectionals_met(db: Session, corps_id: str) -> bool:
    """SECTIONALS → FULL_ENSEMBLE: >=1 rep created."""
    rep_count = db.query(Rep).count()
    return rep_count >= 1


def _full_ensemble_met(db: Session, corps_id: str) -> bool:
    """FULL_ENSEMBLE → RUN_THROUGH: cross-section messages exist, no blocked segments."""
    from backend.models.message import MessageType
    cross_msgs = (
        db.query(Message)
        .filter(Message.corps_id == corps_id)
        .count()
    )
    blocked = (
        db.query(Segment)
        .filter(Segment.status == SegmentStatus.BLOCKED)
        .count()
    )
    return cross_msgs >= 1 and blocked == 0


_MILESTONE_CHECKS = {
    RehearsalMode.BASICS: _basics_met,
    RehearsalMode.SECTIONALS: _sectionals_met,
    RehearsalMode.FULL_ENSEMBLE: _full_ensemble_met,
}


def check_and_advance(db: Session, corps_id: str) -> Optional[RehearsalMode]:
    """Check milestones for current mode; advance if met. Returns new mode or None."""
    corps = db.get(Corps, corps_id)
    if corps is None or corps.status != CorpsStatus.WINTER_CAMPS:
        return None
    if corps.rehearsal_mode is None:
        return None

    check_fn = _MILESTONE_CHECKS.get(corps.rehearsal_mode)
    if check_fn is None:
        return None  # RUN_THROUGH has no auto-advance (go_on_tour is explicit)

    if check_fn(db, corps_id):
        new_mode = _next_mode(corps.rehearsal_mode)
        if new_mode:
            old_mode = corps.rehearsal_mode
            corps.rehearsal_mode = new_mode
            db.commit()
            logger.info(
                "Corps %s advanced from %s to %s",
                corps_id, old_mode.value, new_mode.value,
            )
            return new_mode

    return None
