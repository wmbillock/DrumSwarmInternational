from sqlalchemy.orm import Session

from backend.models.rehearsal_block import (
    RehearsalBlock,
    RehearsalBlockStatus,
    RehearsalBlockType,
)
from backend.models.season_run import CorpsSeasonPhase, CorpsSeasonState


def run_winter_camps(
    db: Session,
    *,
    season_run_id: str,
    corps_id: str,
    camp_count: int,
) -> list[RehearsalBlock]:
    if camp_count < 1 or camp_count > 7:
        raise ValueError("camp_count must be between 1 and 7")

    blocks: list[RehearsalBlock] = []
    for index in range(1, camp_count + 1):
        block = RehearsalBlock(
            season_run_id=season_run_id,
            corps_id=corps_id,
            block_type=RehearsalBlockType.WINTER_CAMP,
            status=RehearsalBlockStatus.COMPLETED,
            sequence_index=index,
            summary=f"Winter camp {index} completed.",
        )
        db.add(block)
        blocks.append(block)

    state = (
        db.query(CorpsSeasonState)
        .filter(
            CorpsSeasonState.season_run_id == season_run_id,
            CorpsSeasonState.corps_id == corps_id,
        )
        .one()
    )
    state.phase = CorpsSeasonPhase.ON_TOUR
    state.blocker_reason = None
    db.commit()
    return blocks
