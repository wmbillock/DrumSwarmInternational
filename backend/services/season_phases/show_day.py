from sqlalchemy.orm import Session

from backend.models.rehearsal_block import (
    RehearsalBlock,
    RehearsalBlockStatus,
    RehearsalBlockType,
)
from backend.models.season_run import CorpsEventPhase, CorpsEventState


SHOW_DAY_BLOCKS = [
    RehearsalBlockType.BASICS,
    RehearsalBlockType.VISUAL_BLOCK,
    RehearsalBlockType.MUSIC_BLOCK,
    RehearsalBlockType.SECTIONAL,
    RehearsalBlockType.FULL_ENSEMBLE,
    RehearsalBlockType.RUN_THROUGH,
]


def run_show_day_rehearsal(
    db: Session,
    *,
    season_run_id: str,
    season_event_id: str,
    corps_id: str,
) -> CorpsEventState:
    state = _get_or_create_event_state(db, season_event_id=season_event_id, corps_id=corps_id)

    for index, block_type in enumerate(SHOW_DAY_BLOCKS, start=1):
        db.add(
            RehearsalBlock(
                season_run_id=season_run_id,
                season_event_id=season_event_id,
                corps_id=corps_id,
                block_type=block_type,
                status=RehearsalBlockStatus.COMPLETED,
                sequence_index=index,
                summary=f"{block_type.value} completed.",
            )
        )

    state.phase = CorpsEventPhase.RUN_THROUGH
    state.blocker_reason = None
    db.commit()
    db.refresh(state)
    return state


def _get_or_create_event_state(
    db: Session,
    *,
    season_event_id: str,
    corps_id: str,
) -> CorpsEventState:
    state = (
        db.query(CorpsEventState)
        .filter(
            CorpsEventState.season_event_id == season_event_id,
            CorpsEventState.corps_id == corps_id,
        )
        .one_or_none()
    )
    if state is not None:
        return state

    state = CorpsEventState(season_event_id=season_event_id, corps_id=corps_id)
    db.add(state)
    db.flush()
    return state
