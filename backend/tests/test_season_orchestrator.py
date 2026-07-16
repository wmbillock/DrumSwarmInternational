from backend.models.corps import Corps
from backend.models.season_run import CorpsSeasonPhase, SeasonRunStatus
from backend.models.segment import Segment, SegmentType
from backend.models.show import Show
from backend.services.season_calendar import create_season_calendar
from backend.services.season_orchestrator import run_full_season_dry_run


def test_full_season_runs_multiple_shows_finals_and_evolution(db):
    root = Segment(type=SegmentType.SHOW, title="Test Show")
    db.add(root)
    db.flush()
    segment = Segment(parent_id=root.id, type=SegmentType.SEGMENT, title="Feature", caption="visual")
    show = Show(title="Test Show", segment_root_id=root.id)
    db.add_all([segment, show])
    db.flush()
    corps_a = Corps(name="Corps A", show_id=show.id)
    corps_b = Corps(name="Corps B", show_id=show.id)
    db.add_all([corps_a, corps_b])
    db.flush()
    run = create_season_calendar(
        db,
        name="2026 Test Season",
        regular_show_count=2,
        winter_camp_count=4,
        corps_ids=[corps_a.id, corps_b.id],
    )

    completed = run_full_season_dry_run(db, season_run_id=run.id)

    assert completed.status == SeasonRunStatus.COMPLETE
    assert completed.regular_show_count == 2
    assert completed.winter_camp_count == 4
    assert all(state.phase == CorpsSeasonPhase.SEASON_COMPLETE for state in completed.corps_states)
    assert len(completed.events) == 3
    assert all(event.status.value == "closed" for event in completed.events)


def test_season_blocks_when_corps_has_unroutable_segments(db):
    root = Segment(type=SegmentType.SHOW, title="Test Show")
    db.add(root)
    db.flush()
    segment = Segment(parent_id=root.id, type=SegmentType.SEGMENT, title="Feature", caption=None)
    show = Show(title="Test Show", segment_root_id=root.id)
    db.add_all([segment, show])
    db.flush()
    corps = Corps(name="Corps A", show_id=show.id)
    db.add(corps)
    db.flush()
    run = create_season_calendar(
        db,
        name="2026 Test Season",
        regular_show_count=1,
        winter_camp_count=2,
        corps_ids=[corps.id],
    )

    result = run_full_season_dry_run(db, season_run_id=run.id)

    assert result.status == SeasonRunStatus.BLOCKED
    state = result.corps_states[0]
    assert state.phase == CorpsSeasonPhase.BLOCKED
    assert "segments without captions" in state.blocker_reason
