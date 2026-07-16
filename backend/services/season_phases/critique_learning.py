from sqlalchemy.orm import Session

from backend.models.critique_adjustment import CritiqueAdjustment
from backend.models.judging_tape import JudgingTape
from backend.models.season_run import CorpsEventPhase, CorpsEventState


def process_show_critique(
    db: Session,
    *,
    season_event_id: str,
    corps_id: str,
) -> list[CritiqueAdjustment]:
    state = (
        db.query(CorpsEventState)
        .filter(
            CorpsEventState.season_event_id == season_event_id,
            CorpsEventState.corps_id == corps_id,
        )
        .one()
    )

    tapes = (
        db.query(JudgingTape)
        .filter(
            JudgingTape.season_event_id == season_event_id,
            JudgingTape.corps_id == corps_id,
        )
        .all()
    )
    if not tapes:
        raise ValueError("Cannot process critique without judging tapes.")

    adjustments: list[CritiqueAdjustment] = []
    for tape in tapes:
        adjustment = CritiqueAdjustment(
            season_event_id=season_event_id,
            corps_id=corps_id,
            corps_event_state_id=state.id,
            caption=tape.caption,
            source_tape_id=tape.id,
            action_summary=f"Next rehearsal plan for {tape.caption}: {tape.tape_text}",
        )
        db.add(adjustment)
        adjustments.append(adjustment)

    state.phase = CorpsEventPhase.ADJUSTED
    state.blocker_reason = None
    db.commit()
    return adjustments
