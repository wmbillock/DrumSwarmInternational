import pytest

from backend.models.season_run import SeasonEventType, SeasonRunStatus
from backend.services.season_calendar import create_season_calendar


def test_create_season_calendar_creates_regular_shows_and_finals(db):
    run = create_season_calendar(
        db,
        name="2026 Test Season",
        regular_show_count=2,
        winter_camp_count=7,
        corps_ids=["corps-a", "corps-b"],
    )

    assert run.status == SeasonRunStatus.PLANNING
    assert run.regular_show_count == 2
    assert run.winter_camp_count == 7
    assert [event.event_type for event in run.events] == [
        SeasonEventType.REGULAR,
        SeasonEventType.REGULAR,
        SeasonEventType.FINALS,
    ]
    assert [event.sequence_index for event in run.events] == [1, 2, 3]
    assert len(run.corps_states) == 2


def test_create_season_calendar_rejects_zero_regular_shows(db):
    with pytest.raises(ValueError, match="regular_show_count must be at least 1"):
        create_season_calendar(
            db,
            name="Broken Season",
            regular_show_count=0,
            winter_camp_count=7,
            corps_ids=["corps-a"],
        )


def test_create_season_calendar_rejects_more_than_seven_winter_camps(db):
    with pytest.raises(ValueError, match="winter_camp_count must be between 1 and 7"):
        create_season_calendar(
            db,
            name="Too Many Camps",
            regular_show_count=3,
            winter_camp_count=8,
            corps_ids=["corps-a"],
        )
