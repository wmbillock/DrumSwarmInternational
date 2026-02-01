"""Corps mode management — switch between design_room, show_mode, rehearsal_mode, judging, offseason_review."""

from sqlalchemy.orm import Session

from backend.models.corps import Corps, CorpsMode, CorpsStatus
from backend.models.work_log import WorkLog


class ModeError(Exception):
    pass


# Valid transitions: from_mode -> set of allowed to_modes
# None means any starting mode is acceptable
VALID_TRANSITIONS: dict[CorpsMode | None, set[CorpsMode]] = {
    None: {CorpsMode.DESIGN_ROOM, CorpsMode.REHEARSAL_MODE},
    CorpsMode.DESIGN_ROOM: {CorpsMode.REHEARSAL_MODE, CorpsMode.SHOW_MODE},
    CorpsMode.REHEARSAL_MODE: {CorpsMode.DESIGN_ROOM, CorpsMode.SHOW_MODE, CorpsMode.JUDGING},
    CorpsMode.SHOW_MODE: {CorpsMode.JUDGING, CorpsMode.DESIGN_ROOM, CorpsMode.REHEARSAL_MODE},
    CorpsMode.JUDGING: {CorpsMode.OFFSEASON_REVIEW, CorpsMode.DESIGN_ROOM, CorpsMode.REHEARSAL_MODE},
    CorpsMode.OFFSEASON_REVIEW: {CorpsMode.DESIGN_ROOM},
}


def switch_mode(db: Session, corps_id: str, new_mode: CorpsMode) -> Corps:
    """Switch a corps to a new mode with validation and work_log entry."""
    corps = db.get(Corps, corps_id)
    if not corps:
        raise ModeError(f"Corps {corps_id} not found")

    if corps.status == CorpsStatus.DISBANDED:
        raise ModeError("Cannot switch mode on a disbanded corps")

    current = corps.mode
    allowed = VALID_TRANSITIONS.get(current, set())
    if new_mode not in allowed:
        current_label = current.value if current else "none"
        raise ModeError(
            f"Cannot transition from {current_label} to {new_mode.value}. "
            f"Allowed: {', '.join(m.value for m in sorted(allowed, key=lambda m: m.value))}"
        )

    old_mode = current.value if current else None
    corps.mode = new_mode
    db.flush()

    # Log the transition
    log = WorkLog(
        session_id="system",
        corps_id=corps_id,
        role="system",
        event_type="mode_switch",
        details=f"Mode changed from {old_mode} to {new_mode.value}",
    )
    db.add(log)
    db.commit()

    return corps
