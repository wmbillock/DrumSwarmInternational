from sqlalchemy.orm import Session

from backend.models.season_run import (
    CorpsSeasonState,
    SeasonEvent,
    SeasonEventType,
    SeasonRun,
)


def create_season_calendar(
    db: Session,
    *,
    name: str,
    regular_show_count: int,
    winter_camp_count: int,
    corps_ids: list[str],
) -> SeasonRun:
    if regular_show_count < 1:
        raise ValueError("regular_show_count must be at least 1")
    if winter_camp_count < 1 or winter_camp_count > 7:
        raise ValueError("winter_camp_count must be between 1 and 7")
    if not corps_ids:
        raise ValueError("at least one corps is required")

    run = SeasonRun(
        name=name,
        regular_show_count=regular_show_count,
        winter_camp_count=winter_camp_count,
    )
    db.add(run)
    db.flush()

    for index in range(1, regular_show_count + 1):
        db.add(
            SeasonEvent(
                season_run_id=run.id,
                name=f"Regular Show {index}",
                event_type=SeasonEventType.REGULAR,
                sequence_index=index,
            )
        )

    db.add(
        SeasonEvent(
            season_run_id=run.id,
            name="Season Finals",
            event_type=SeasonEventType.FINALS,
            sequence_index=regular_show_count + 1,
        )
    )

    for corps_id in corps_ids:
        db.add(CorpsSeasonState(season_run_id=run.id, corps_id=corps_id))

    db.commit()
    db.refresh(run)
    return run
