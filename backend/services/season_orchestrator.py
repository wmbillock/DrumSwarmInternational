from sqlalchemy.orm import Session

from backend.models.season_run import (
    CorpsSeasonPhase,
    SeasonEventStatus,
    SeasonRun,
    SeasonRunStatus,
)
from backend.services.competition_executor import record_competition_result
from backend.services.season_invariants import check_corps_ready_for_tour
from backend.services.season_phases.critique_learning import process_show_critique
from backend.services.season_phases.offseason import run_offseason_training
from backend.services.season_phases.show_day import run_show_day_rehearsal
from backend.services.season_phases.winter_camps import run_winter_camps


def run_next_season_step(db: Session, *, season_run_id: str) -> SeasonRun:
    run = db.get(SeasonRun, season_run_id)
    if run is None:
        raise ValueError("Season run does not exist.")
    return run


def run_full_season_dry_run(db: Session, *, season_run_id: str) -> SeasonRun:
    run = db.get(SeasonRun, season_run_id)
    if run is None:
        raise ValueError("Season run does not exist.")

    run.status = SeasonRunStatus.OFFSEASON
    for state in run.corps_states:
        blockers = check_corps_ready_for_tour(db, corps_id=state.corps_id)
        if blockers:
            state.phase = CorpsSeasonPhase.BLOCKED
            state.blocker_reason = "; ".join(blocker.message for blocker in blockers)
            run.status = SeasonRunStatus.BLOCKED
            run.blocker_reason = state.blocker_reason
            db.commit()
            db.refresh(run)
            return run

        run_offseason_training(db, season_run_id=run.id, corps_id=state.corps_id)
        state.phase = CorpsSeasonPhase.WINTER_CAMPS
        run_winter_camps(
            db,
            season_run_id=run.id,
            corps_id=state.corps_id,
            camp_count=run.winter_camp_count,
        )

    run.status = SeasonRunStatus.ON_TOUR
    for event in sorted(run.events, key=lambda item: item.sequence_index):
        event.status = SeasonEventStatus.REHEARSING
        for state in run.corps_states:
            run_show_day_rehearsal(
                db,
                season_run_id=run.id,
                season_event_id=event.id,
                corps_id=state.corps_id,
            )
            event.status = SeasonEventStatus.COMPETING
            record_competition_result(
                db,
                season_event_id=event.id,
                corps_id=state.corps_id,
                rep_id=None,
                artifact_id=f"{event.id}:{state.corps_id}:run-through",
                score_payload={"caption": "general_effect", "value": 75.0},
                tape_text="Dry-run tape: identify one adjustment before the next show.",
            )
            event.status = SeasonEventStatus.CRITIQUE
            process_show_critique(db, season_event_id=event.id, corps_id=state.corps_id)

        event.status = SeasonEventStatus.CLOSED

    for state in run.corps_states:
        state.phase = CorpsSeasonPhase.SEASON_COMPLETE

    run.status = SeasonRunStatus.COMPLETE
    run.blocker_reason = None
    db.commit()
    db.refresh(run)
    return run
