from backend.models.corps import Corps
from backend.models.judging_tape import JudgingTape
from backend.models.rep import Rep
from backend.models.score import Score
from backend.models.segment import Segment, SegmentType
from backend.services.competition_executor import record_competition_result
from backend.services.season_calendar import create_season_calendar


def test_competition_result_links_score_and_tape_to_rep(db):
    corps = Corps(name="Test Corps")
    segment = Segment(type=SegmentType.SEGMENT, title="Feature", caption="general_effect")
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

    record_competition_result(
        db,
        season_event_id=event.id,
        corps_id=corps.id,
        rep_id=rep.id,
        artifact_id=None,
        score_payload={"caption": "general_effect", "value": 82.5},
        tape_text="Strong idea; tighten execution before next show.",
    )

    score = db.query(Score).one()
    tape = db.query(JudgingTape).one()
    assert score.rep_id == rep.id
    assert score.season_event_id == event.id
    assert tape.rep_id == rep.id
    assert tape.season_event_id == event.id
