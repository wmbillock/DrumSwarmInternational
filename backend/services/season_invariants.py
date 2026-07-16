from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.models.corps import Corps
from backend.models.segment import Segment, SegmentType
from backend.models.show import Show
from backend.services.segment_service import get_children


@dataclass(frozen=True)
class SeasonBlocker:
    code: str
    message: str
    corps_id: str | None = None


def check_corps_ready_for_winter_camps(db: Session, *, corps_id: str) -> list[SeasonBlocker]:
    corps = db.get(Corps, corps_id)
    if corps is None:
        return [SeasonBlocker("missing_corps", "Corps does not exist.", corps_id)]

    blockers: list[SeasonBlocker] = []
    if not corps.show_id:
        blockers.append(SeasonBlocker("missing_show", "Corps has no assigned show.", corps_id))
        return blockers

    show = db.get(Show, corps.show_id)
    if show is None:
        blockers.append(SeasonBlocker("missing_show", "Corps assigned show does not exist.", corps_id))
    elif not show.segment_root_id:
        blockers.append(
            SeasonBlocker("missing_segment_tree", "Corps show has no segment tree.", corps_id)
        )

    return blockers


def check_corps_ready_for_tour(db: Session, *, corps_id: str) -> list[SeasonBlocker]:
    corps = db.get(Corps, corps_id)
    if corps is None:
        return [SeasonBlocker("missing_corps", "Corps does not exist.", corps_id)]

    blockers = check_corps_ready_for_winter_camps(db, corps_id=corps_id)
    if blockers:
        return blockers

    show = db.get(Show, corps.show_id)
    assert show is not None
    unroutable = _find_unroutable_segments(db, show.segment_root_id)
    if unroutable:
        blockers.append(
            SeasonBlocker(
                "unroutable_segments",
                "Corps show has segments without captions or fallback owners.",
                corps_id,
            )
        )

    return blockers


def check_corps_ready_to_compete(
    db: Session,
    *,
    corps_id: str,
    season_event_id: str,
) -> list[SeasonBlocker]:
    return check_corps_ready_for_tour(db, corps_id=corps_id)


def _find_unroutable_segments(db: Session, root_id: str | None) -> list[Segment]:
    if root_id is None:
        return []

    root = db.get(Segment, root_id)
    if root is None:
        return []

    unroutable: list[Segment] = []
    stack = list(get_children(db, root.id))

    while stack:
        segment = stack.pop()
        stack.extend(get_children(db, segment.id))
        if segment.type != SegmentType.SHOW and not segment.caption:
            unroutable.append(segment)

    return unroutable
