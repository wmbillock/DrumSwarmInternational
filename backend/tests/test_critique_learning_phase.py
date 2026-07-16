from backend.models.corps import Corps
from backend.models.critique_adjustment import CritiqueAdjustment
from backend.models.rep import Rep
from backend.models.season_run import CorpsEventPhase
from backend.models.segment import Segment, SegmentType
from backend.services.competition_executor import record_competition_result
from backend.services.season_calendar import create_season_calendar
from backend.services.season_phases.critique_learning import process_show_critique
from backend.services.season_phases.show_day import run_show_day_rehearsal


def test_critique_creates_adjustments_and_advances_event_state(db):
    corps = Corps(name="Test Corps")
    segment = Segment(type=SegmentType.SEGMENT, title="Feature", caption="visual")
    db.add_all([corps, segment])
    db.flush()
    rep = Rep(segment_id=segment.id)
    db.add(rep)
    db.flush()
    run = create_season_calendar(
        db,
        name="2026 Test Season",
        regular_show_count=1,
        winter_camp_count=2,
        corps_ids=[corps.id],
    )
    event = run.events[0]
    run_show_day_rehearsal(
        db,
        season_run_id=run.id,
        season_event_id=event.id,
        corps_id=corps.id,
    )
    record_competition_result(
        db,
        season_event_id=event.id,
        corps_id=corps.id,
        rep_id=rep.id,
        artifact_id=None,
        score_payload={"caption": "visual", "value": 71.0},
        tape_text="Forms read late; improve interval clarity.",
    )

    adjustments = process_show_critique(db, season_event_id=event.id, corps_id=corps.id)

    assert len(adjustments) == 1
    assert db.query(CritiqueAdjustment).count() == 1
    assert adjustments[0].caption == "visual"
    assert adjustments[0].action_summary
    assert adjustments[0].event_state.phase == CorpsEventPhase.ADJUSTED
