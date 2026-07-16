from sqlalchemy.orm import Session

from backend.models.performer import Performer
from backend.models.season_run import CorpsSeasonPhase, CorpsSeasonState
from backend.services.performer_service import audition_for_role


def run_season_recruiting(
    db: Session,
    *,
    season_run_id: str,
    corps_id: str,
    open_roles: list[str],
) -> list[Performer]:
    if not open_roles:
        raise ValueError("open_roles must not be empty")

    recruited: list[Performer] = []
    for role in open_roles:
        performer = audition_for_role(db, role)
        performer.corps_id = corps_id
        recruited.append(performer)

    state = (
        db.query(CorpsSeasonState)
        .filter(
            CorpsSeasonState.season_run_id == season_run_id,
            CorpsSeasonState.corps_id == corps_id,
        )
        .one()
    )
    state.phase = CorpsSeasonPhase.WINTER_CAMPS
    state.blocker_reason = None
    db.commit()
    return recruited
