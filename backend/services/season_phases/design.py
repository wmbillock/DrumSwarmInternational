from sqlalchemy.orm import Session

from backend.models.corps import Corps
from backend.models.season_run import CorpsSeasonPhase, CorpsSeasonState


def complete_show_design_for_season(
    db: Session,
    *,
    season_run_id: str,
    corps_id: str,
    show_id: str,
) -> CorpsSeasonState:
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise ValueError("Corps does not exist.")

    state = (
        db.query(CorpsSeasonState)
        .filter(
            CorpsSeasonState.season_run_id == season_run_id,
            CorpsSeasonState.corps_id == corps_id,
        )
        .one()
    )

    corps.show_id = show_id
    state.phase = CorpsSeasonPhase.RECRUITING
    state.blocker_reason = None
    db.commit()
    db.refresh(state)
    return state
