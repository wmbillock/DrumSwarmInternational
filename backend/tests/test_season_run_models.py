from backend.models.season_run import (
    CorpsEventPhase,
    CorpsEventState,
    CorpsSeasonPhase,
    CorpsSeasonState,
    SeasonEvent,
    SeasonEventStatus,
    SeasonEventType,
    SeasonRun,
    SeasonRunStatus,
)


def test_season_run_defaults(db):
    run = SeasonRun(name="2026 Test Season", regular_show_count=3, winter_camp_count=7)
    db.add(run)
    db.flush()

    assert run.status == SeasonRunStatus.PLANNING
    assert run.regular_show_count == 3
    assert run.winter_camp_count == 7


def test_season_event_defaults(db):
    run = SeasonRun(name="2026 Test Season", regular_show_count=3, winter_camp_count=7)
    db.add(run)
    db.flush()
    event = SeasonEvent(
        season_run_id=run.id,
        name="Midwest Regional",
        event_type=SeasonEventType.REGULAR,
        sequence_index=1,
    )
    db.add(event)
    db.flush()

    assert event.status == SeasonEventStatus.SCHEDULED
    assert event.sequence_index == 1


def test_corps_season_state_defaults(db):
    run = SeasonRun(name="2026 Test Season", regular_show_count=3, winter_camp_count=7)
    db.add(run)
    db.flush()
    state = CorpsSeasonState(
        season_run_id=run.id,
        corps_id="corps-1",
    )
    db.add(state)
    db.flush()

    assert state.phase == CorpsSeasonPhase.STAFFING
    assert state.prestige_snapshot == 0.0
    assert state.cachet_snapshot == 0.0


def test_corps_event_state_defaults(db):
    run = SeasonRun(name="2026 Test Season", regular_show_count=3, winter_camp_count=7)
    db.add(run)
    db.flush()
    event = SeasonEvent(
        season_run_id=run.id,
        name="Midwest Regional",
        event_type=SeasonEventType.REGULAR,
        sequence_index=1,
    )
    db.add(event)
    db.flush()
    state = CorpsEventState(
        season_event_id=event.id,
        corps_id="corps-1",
    )
    db.add(state)
    db.flush()

    assert state.phase == CorpsEventPhase.NOT_STARTED
    assert state.blocker_reason is None
