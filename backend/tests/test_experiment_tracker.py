"""Tests for experiment_tracker service."""

from backend.services.experiment_tracker import (
    record_experiment,
    list_experiments,
    compare_experiments,
    result_to_dict,
)
from backend.models.corps import Corps
from backend.models.show import Show


def _seed_corps(db, corps_id="corps-a"):
    corps = Corps(id=corps_id, name=corps_id.title())
    db.add(corps)
    db.commit()
    return corps_id


def _seed_show(db, show_id="show-1"):
    show = Show(id=show_id, title="Test Show")
    db.add(show)
    db.commit()
    return show_id


def test_record_experiment_minimal(db):
    cid = _seed_corps(db)
    result = record_experiment(db, corps_id=cid)
    assert result.id is not None
    assert result.corps_id == cid
    assert result.total_score is None


def test_record_experiment_full(db):
    cid = _seed_corps(db)
    sid = _seed_show(db)
    result = record_experiment(
        db,
        corps_id=cid,
        show_id=sid,
        competition_id="s1-test-show",
        season_id="s1",
        llm_provider="claude",
        llm_model="claude-sonnet-4-5",
        methodology="tdd",
        total_score=85.5,
        caption_scores={"brass": 18.0, "percussion": 17.5},
        iterations_used=3,
        tool_calls_count=42,
        sessions_spawned=5,
        failures_count=1,
        wall_time_seconds=120.5,
        notes="Good run",
        metrics={"avg_latency": 2.5},
    )
    assert result.total_score == 85.5
    assert result.caption_scores["brass"] == 18.0
    assert result.llm_provider == "claude"
    assert result.methodology == "tdd"
    assert result.wall_time_seconds == 120.5


def test_list_experiments_no_filter(db):
    cid = _seed_corps(db)
    record_experiment(db, corps_id=cid, total_score=70.0)
    record_experiment(db, corps_id=cid, total_score=80.0)
    results = list_experiments(db)
    assert len(results) == 2


def test_list_experiments_filter_by_corps(db):
    ca = _seed_corps(db, "corps-a")
    cb = _seed_corps(db, "corps-b")
    record_experiment(db, corps_id=ca, total_score=70.0)
    record_experiment(db, corps_id=cb, total_score=80.0)
    results = list_experiments(db, corps_id="corps-a")
    assert len(results) == 1
    assert results[0].corps_id == "corps-a"


def test_list_experiments_filter_by_show(db):
    cid = _seed_corps(db)
    _seed_show(db, "show-1")
    _seed_show(db, "show-2")
    record_experiment(db, corps_id=cid, show_id="show-1", total_score=70.0)
    record_experiment(db, corps_id=cid, show_id="show-2", total_score=80.0)
    results = list_experiments(db, show_id="show-1")
    assert len(results) == 1


def test_list_experiments_filter_by_season(db):
    cid = _seed_corps(db)
    record_experiment(db, corps_id=cid, season_id="s1", total_score=70.0)
    record_experiment(db, corps_id=cid, season_id="s2", total_score=80.0)
    results = list_experiments(db, season_id="s1")
    assert len(results) == 1


def test_compare_experiments_sorted_by_score(db):
    ca = _seed_corps(db, "corps-a")
    cb = _seed_corps(db, "corps-b")
    sid = _seed_show(db)
    record_experiment(db, corps_id=ca, show_id=sid, total_score=70.0,
                      llm_provider="openai", methodology="scrum")
    record_experiment(db, corps_id=cb, show_id=sid, total_score=90.0,
                      llm_provider="claude", methodology="tdd")
    comparisons = compare_experiments(db, show_id=sid)
    assert len(comparisons) == 2
    assert comparisons[0]["corps_id"] == "corps-b"
    assert comparisons[0]["total_score"] == 90.0
    assert comparisons[1]["corps_id"] == "corps-a"


def test_compare_experiments_handles_none_scores(db):
    cid = _seed_corps(db)
    sid = _seed_show(db)
    record_experiment(db, corps_id=cid, show_id=sid, total_score=None)
    comparisons = compare_experiments(db, show_id=sid)
    assert len(comparisons) == 1
    assert comparisons[0]["total_score"] is None


def test_result_to_dict(db):
    cid = _seed_corps(db)
    result = record_experiment(
        db, corps_id=cid, total_score=75.0, llm_provider="claude"
    )
    d = result_to_dict(result)
    assert d["corps_id"] == cid
    assert d["total_score"] == 75.0
    assert d["llm_provider"] == "claude"
    assert d["id"] == result.id
    assert "created_at" in d
