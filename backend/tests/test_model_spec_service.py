"""Tests for model spec service — outcome recording and best-spec queries."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
import backend.models  # noqa: F401 — ensure all models registered

from backend.models.corps import Corps
from backend.models.model_spec import ModelSpec
from backend.models.model_spec_performance import ModelSpecPerformance
from backend.services.model_spec_service import (
    get_best_spec_for_task,
    get_corps_spec_stats,
    get_spec_leaderboard,
    record_model_spec_outcome,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _make_corps(db, name="Test Corps"):
    corps = Corps(id=str(uuid.uuid4()), name=name)
    db.add(corps)
    db.flush()
    return corps.id


def _make_spec(db, name, provider="anthropic", model_id="claude-sonnet-4-5", **kwargs):
    spec = ModelSpec(name=name, provider=provider, model_id=model_id, **kwargs)
    db.add(spec)
    db.flush()
    return spec


class TestRecordOutcome:
    def test_record_outcome_creates_row(self, db):
        spec = _make_spec(db, "test-model")
        perf = record_model_spec_outcome(
            db, spec.id, "frontend", score=85.0, success=True
        )
        assert perf.total_attempts == 1
        assert perf.successful_attempts == 1
        assert perf.total_score == 85.0
        assert perf.avg_score == 85.0
        assert perf.last_used_at is not None
        assert perf.corps_id is None

        # Verify it's in the DB
        fetched = db.get(ModelSpecPerformance, perf.id)
        assert fetched is not None
        assert fetched.task_category == "frontend"

    def test_record_outcome_updates_avg(self, db):
        spec = _make_spec(db, "avg-model")

        record_model_spec_outcome(db, spec.id, "backend", score=80.0, success=True)
        record_model_spec_outcome(db, spec.id, "backend", score=90.0, success=True)
        perf = record_model_spec_outcome(db, spec.id, "backend", score=70.0, success=False)

        assert perf.total_attempts == 3
        assert perf.successful_attempts == 2
        assert perf.total_score == pytest.approx(240.0)
        assert perf.avg_score == pytest.approx(80.0)

    def test_record_outcome_corps_scoped(self, db):
        spec = _make_spec(db, "corps-model")
        corps_id = _make_corps(db)

        perf_global = record_model_spec_outcome(
            db, spec.id, "testing", score=90.0, success=True
        )
        perf_corps = record_model_spec_outcome(
            db, spec.id, "testing", score=70.0, success=True, corps_id=corps_id
        )

        # Two distinct rows
        assert perf_global.id != perf_corps.id
        assert perf_global.corps_id is None
        assert perf_corps.corps_id == corps_id


class TestBestSpecForTask:
    def test_best_spec_respects_min_attempts(self, db):
        """Spec with 2 attempts and high score loses to spec with 5 attempts
        and lower score when min_attempts=3."""
        hot_shot = _make_spec(db, "hot-shot", model_id="hot-shot-v1")
        workhorse = _make_spec(db, "workhorse", model_id="workhorse-v1")

        # hot_shot: 2 attempts, avg 95
        record_model_spec_outcome(db, hot_shot.id, "frontend", score=95.0, success=True)
        record_model_spec_outcome(db, hot_shot.id, "frontend", score=95.0, success=True)

        # workhorse: 5 attempts, avg 80
        for _ in range(5):
            record_model_spec_outcome(db, workhorse.id, "frontend", score=80.0, success=True)

        best = get_best_spec_for_task(db, "frontend", min_attempts=3)
        assert best is not None
        assert best.id == workhorse.id

    def test_best_spec_per_corps(self, db):
        """Corps-specific stats take priority over global."""
        spec_a = _make_spec(db, "spec-a", model_id="a-v1")
        spec_b = _make_spec(db, "spec-b", model_id="b-v1")
        corps_id = _make_corps(db)

        # Global: spec_a is best
        for _ in range(5):
            record_model_spec_outcome(db, spec_a.id, "backend", score=90.0, success=True)
        for _ in range(5):
            record_model_spec_outcome(db, spec_b.id, "backend", score=70.0, success=True)

        # Corps-specific: spec_b is best for this corps
        for _ in range(5):
            record_model_spec_outcome(
                db, spec_b.id, "backend", score=95.0, success=True, corps_id=corps_id
            )
        for _ in range(5):
            record_model_spec_outcome(
                db, spec_a.id, "backend", score=60.0, success=True, corps_id=corps_id
            )

        # Without corps → global winner (spec_a)
        best_global = get_best_spec_for_task(db, "backend")
        assert best_global.id == spec_a.id

        # With corps → corps-specific winner (spec_b)
        best_corps = get_best_spec_for_task(db, "backend", corps_id=corps_id)
        assert best_corps.id == spec_b.id

    def test_best_spec_falls_back_to_global(self, db):
        """When corps has no data, falls back to global stats."""
        spec = _make_spec(db, "global-only")
        corps_id = _make_corps(db)

        for _ in range(5):
            record_model_spec_outcome(db, spec.id, "testing", score=85.0, success=True)

        best = get_best_spec_for_task(db, "testing", corps_id=corps_id)
        assert best is not None
        assert best.id == spec.id

    def test_best_spec_excludes_inactive(self, db):
        spec = _make_spec(db, "inactive-spec")
        for _ in range(5):
            record_model_spec_outcome(db, spec.id, "frontend", score=99.0, success=True)

        spec.is_active = False
        db.flush()

        best = get_best_spec_for_task(db, "frontend")
        assert best is None

    def test_best_spec_returns_none_when_empty(self, db):
        best = get_best_spec_for_task(db, "nonexistent")
        assert best is None


class TestLeaderboard:
    def test_leaderboard_ordering(self, db):
        specs = []
        scores = [70.0, 90.0, 80.0]
        for i, score in enumerate(scores):
            spec = _make_spec(db, f"lb-spec-{i}", model_id=f"model-{i}")
            specs.append(spec)
            for _ in range(3):
                record_model_spec_outcome(db, spec.id, "architecture", score=score, success=True)

        board = get_spec_leaderboard(db, "architecture")
        assert len(board) == 3
        assert board[0]["avg_score"] == pytest.approx(90.0)
        assert board[1]["avg_score"] == pytest.approx(80.0)
        assert board[2]["avg_score"] == pytest.approx(70.0)
        assert board[0]["name"] == "lb-spec-1"
        assert board[0]["total_attempts"] == 3
        assert board[0]["success_rate"] == pytest.approx(1.0)

    def test_leaderboard_limit(self, db):
        for i in range(5):
            spec = _make_spec(db, f"many-{i}", model_id=f"m-{i}")
            record_model_spec_outcome(db, spec.id, "docs", score=float(i * 10), success=True)

        board = get_spec_leaderboard(db, "docs", limit=3)
        assert len(board) == 3


class TestCorpsSpecStats:
    def test_get_corps_spec_stats(self, db):
        corps_id = _make_corps(db)
        spec = _make_spec(db, "corps-stat-spec")

        record_model_spec_outcome(
            db, spec.id, "frontend", score=85.0, success=True, corps_id=corps_id
        )
        record_model_spec_outcome(
            db, spec.id, "backend", score=75.0, success=True, corps_id=corps_id
        )
        # Global stat — should NOT appear in corps results
        record_model_spec_outcome(db, spec.id, "testing", score=90.0, success=True)

        stats = get_corps_spec_stats(db, corps_id)
        assert len(stats) == 2
        categories = {s.task_category for s in stats}
        assert categories == {"frontend", "backend"}
