from backend.models.corps import Corps
from backend.models.performer import Performer
from backend.models.rehearsal_block import RehearsalBlock, RehearsalBlockStatus, RehearsalBlockType
from backend.models.season_run import CorpsEventPhase, CorpsSeasonPhase
from backend.services.season_calendar import create_season_calendar
from backend.services.season_phases.offseason import run_offseason_training
from backend.services.season_phases.recruiting import run_season_recruiting
from backend.services.season_phases.show_day import run_show_day_rehearsal
from backend.services.season_phases.winter_camps import run_winter_camps


def test_offseason_training_records_member_learning(db):
    corps = Corps(name="Test Corps")
    db.add(corps)
    db.flush()
    performer = Performer(
        name="Test Player",
        role_type="brass_tech",
        corps_id=corps.id,
        experience_seasons=1,
        trust_score=55.0,
    )
    db.add(performer)
    db.flush()
    run = create_season_calendar(
        db,
        name="2026 Test Season",
        regular_show_count=1,
        winter_camp_count=2,
        corps_ids=[corps.id],
    )

    deltas = run_offseason_training(db, season_run_id=run.id, corps_id=corps.id)

    db.refresh(performer)
    assert deltas
    assert performer.trust_score > 55.0
    assert any(delta.target_id == performer.id for delta in deltas)


def test_recruiting_fills_open_roles_and_advances_to_winter_camps(db):
    corps = Corps(name="Test Corps")
    db.add(corps)
    db.flush()
    run = create_season_calendar(
        db,
        name="2026 Test Season",
        regular_show_count=1,
        winter_camp_count=2,
        corps_ids=[corps.id],
    )

    performers = run_season_recruiting(
        db,
        season_run_id=run.id,
        corps_id=corps.id,
        open_roles=["brass_caption_head", "percussion_caption_head"],
    )

    assert {performer.role_type for performer in performers} == {
        "brass_caption_head",
        "percussion_caption_head",
    }
    state = run.corps_states[0]
    db.refresh(state)
    assert state.phase == CorpsSeasonPhase.WINTER_CAMPS


def test_winter_camps_create_learning_blocks_and_advance_to_tour(db):
    corps = Corps(name="Test Corps")
    db.add(corps)
    db.flush()
    run = create_season_calendar(
        db,
        name="2026 Test Season",
        regular_show_count=1,
        winter_camp_count=2,
        corps_ids=[corps.id],
    )

    blocks = run_winter_camps(db, season_run_id=run.id, corps_id=corps.id, camp_count=2)

    assert len(blocks) == 2
    assert all(block.block_type == RehearsalBlockType.WINTER_CAMP for block in blocks)
    assert all(block.status == RehearsalBlockStatus.COMPLETED for block in blocks)
    state = run.corps_states[0]
    db.refresh(state)
    assert state.phase == CorpsSeasonPhase.ON_TOUR


def test_winter_camps_reject_more_than_seven_camps(db):
    corps = Corps(name="Test Corps")
    db.add(corps)
    db.flush()
    run = create_season_calendar(
        db,
        name="2026 Test Season",
        regular_show_count=1,
        winter_camp_count=7,
        corps_ids=[corps.id],
    )

    try:
        run_winter_camps(db, season_run_id=run.id, corps_id=corps.id, camp_count=8)
    except ValueError as exc:
        assert "camp_count must be between 1 and 7" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_show_day_rehearsal_runs_required_blocks_in_order(db):
    corps = Corps(name="Test Corps")
    db.add(corps)
    db.flush()
    run = create_season_calendar(
        db,
        name="2026 Test Season",
        regular_show_count=1,
        winter_camp_count=2,
        corps_ids=[corps.id],
    )
    event = run.events[0]

    state = run_show_day_rehearsal(
        db,
        season_run_id=run.id,
        season_event_id=event.id,
        corps_id=corps.id,
    )

    blocks = (
        db.query(RehearsalBlock)
        .filter(RehearsalBlock.season_event_id == event.id)
        .order_by(RehearsalBlock.sequence_index)
        .all()
    )
    assert [block.block_type for block in blocks] == [
        RehearsalBlockType.BASICS,
        RehearsalBlockType.VISUAL_BLOCK,
        RehearsalBlockType.MUSIC_BLOCK,
        RehearsalBlockType.SECTIONAL,
        RehearsalBlockType.FULL_ENSEMBLE,
        RehearsalBlockType.RUN_THROUGH,
    ]
    assert all(block.status == RehearsalBlockStatus.COMPLETED for block in blocks)
    assert state.phase == CorpsEventPhase.RUN_THROUGH
