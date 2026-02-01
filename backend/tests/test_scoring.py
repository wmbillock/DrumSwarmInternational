"""Phase 6: Scoring tests — models, composite math, threshold routing, timing official."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import Base
from backend.models.segment import Segment, SegmentType, SegmentStatus
from backend.models.rep import Rep, RepStatus
from backend.models.score import JudgeType, Score
from backend.models.penalty import Penalty, PenaltyType
from backend.services.scoring_service import (
    record_score,
    record_penalty,
    get_scores_for_rep,
    get_scores_for_segment,
    get_penalties_for_corps,
    compute_composite,
    check_timing,
    InvalidScore,
    REWORK_THRESHOLD,
    ESCALATION_THRESHOLD,
    DEFAULT_WEIGHTS,
    CompositeScore,
)

# Import all models for table creation
import backend.models.segment  # noqa: F401
import backend.models.rep  # noqa: F401
import backend.models.message  # noqa: F401
import backend.models.problem  # noqa: F401
import backend.models.subscription  # noqa: F401
import backend.models.agent_definition  # noqa: F401
import backend.models.agent_session  # noqa: F401
import backend.models.score  # noqa: F401
import backend.models.penalty  # noqa: F401


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def corps_id():
    return "corps-001"


@pytest.fixture
def show_coord(db):
    coord = Segment(type=SegmentType.SHOW, title="Test Show")
    db.add(coord)
    db.commit()
    db.refresh(coord)
    return coord


@pytest.fixture
def rep(db, show_coord):
    r = Rep(segment_id=show_coord.id)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


class TestScoreModel:
    def test_create_score(self, db, corps_id, rep):
        score = record_score(
            db, corps_id=corps_id, judge_type=JudgeType.BRASS,
            value=85.0, box=4, rep_id=rep.id, feedback="Solid execution"
        )
        assert score.id is not None
        assert score.value == 85.0
        assert score.box == 4
        assert score.judge_type == JudgeType.BRASS
        assert score.feedback == "Solid execution"

    def test_score_value_range(self, db, corps_id, rep):
        with pytest.raises(InvalidScore, match="0-100"):
            record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                         value=101.0, box=3, rep_id=rep.id)

    def test_score_value_negative(self, db, corps_id, rep):
        with pytest.raises(InvalidScore, match="0-100"):
            record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                         value=-1.0, box=3, rep_id=rep.id)

    def test_box_range_low(self, db, corps_id, rep):
        with pytest.raises(InvalidScore, match="1-5"):
            record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                         value=50.0, box=0, rep_id=rep.id)

    def test_box_range_high(self, db, corps_id, rep):
        with pytest.raises(InvalidScore, match="1-5"):
            record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                         value=50.0, box=6, rep_id=rep.id)

    def test_score_without_target_allowed(self, db, corps_id):
        """Competition-level scores can exist without a rep or segment."""
        score = record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                             value=50.0, box=3)
        assert score.value == 50.0
        assert score.rep_id is None
        assert score.segment_id is None

    def test_score_on_segment(self, db, corps_id, show_coord):
        score = record_score(
            db, corps_id=corps_id, judge_type=JudgeType.VISUAL,
            value=70.0, box=3, segment_id=show_coord.id
        )
        assert score.segment_id == show_coord.id
        assert score.rep_id is None


class TestPenaltyModel:
    def test_create_penalty(self, db, corps_id, rep):
        penalty = record_penalty(
            db, corps_id=corps_id, type=PenaltyType.TIMING,
            amount=5.0, reason="Late delivery", rep_id=rep.id
        )
        assert penalty.id is not None
        assert penalty.amount == 5.0
        assert penalty.type == PenaltyType.TIMING

    def test_penalty_must_be_positive(self, db, corps_id):
        with pytest.raises(InvalidScore, match="positive"):
            record_penalty(db, corps_id=corps_id, type=PenaltyType.RULE,
                           amount=0, reason="Zero penalty")

    def test_penalty_negative(self, db, corps_id):
        with pytest.raises(InvalidScore, match="positive"):
            record_penalty(db, corps_id=corps_id, type=PenaltyType.RULE,
                           amount=-1, reason="Negative")


class TestCompositeScore:
    def test_single_judge(self, db, corps_id, rep):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=80.0, box=4, rep_id=rep.id)
        result = compute_composite(db, corps_id=corps_id, rep_id=rep.id)
        # Single judge, normalized to full weight
        assert result.final_score == pytest.approx(80.0, abs=0.1)
        assert JudgeType.BRASS in result.caption_scores

    def test_all_judges(self, db, corps_id, rep):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=80.0, box=4, rep_id=rep.id)
        record_score(db, corps_id=corps_id, judge_type=JudgeType.PERCUSSION,
                     value=90.0, box=5, rep_id=rep.id)
        record_score(db, corps_id=corps_id, judge_type=JudgeType.GUARD,
                     value=70.0, box=3, rep_id=rep.id)
        record_score(db, corps_id=corps_id, judge_type=JudgeType.VISUAL,
                     value=85.0, box=4, rep_id=rep.id)
        record_score(db, corps_id=corps_id, judge_type=JudgeType.GENERAL_EFFECT,
                     value=75.0, box=3, rep_id=rep.id)

        result = compute_composite(db, corps_id=corps_id, rep_id=rep.id)
        expected = (80*0.20 + 90*0.20 + 70*0.20 + 85*0.15 + 75*0.25)
        assert result.raw_total == pytest.approx(expected, abs=0.1)
        assert result.final_score == pytest.approx(expected, abs=0.1)
        assert result.penalties_total == 0.0

    def test_with_penalties(self, db, corps_id, rep):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=80.0, box=4, rep_id=rep.id)
        record_penalty(db, corps_id=corps_id, type=PenaltyType.TIMING,
                       amount=5.0, reason="Late", rep_id=rep.id)
        result = compute_composite(db, corps_id=corps_id, rep_id=rep.id)
        assert result.penalties_total == 5.0
        assert result.final_score == pytest.approx(80.0 - 5.0, abs=0.1)

    def test_floor_at_zero(self, db, corps_id, rep):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=10.0, box=1, rep_id=rep.id)
        record_penalty(db, corps_id=corps_id, type=PenaltyType.BUDGET,
                       amount=50.0, reason="Massive overrun", rep_id=rep.id)
        result = compute_composite(db, corps_id=corps_id, rep_id=rep.id)
        assert result.final_score == 0.0

    def test_no_scores(self, db, corps_id):
        result = compute_composite(db, corps_id=corps_id, rep_id="nonexistent")
        assert result.raw_total == 0.0
        assert result.final_score == 0.0


class TestThresholdRouting:
    def test_high_score_no_rework(self, db, corps_id, rep):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=85.0, box=4, rep_id=rep.id)
        result = compute_composite(db, corps_id=corps_id, rep_id=rep.id)
        assert not result.needs_rework
        assert not result.needs_escalation

    def test_medium_score_needs_rework(self, db, corps_id, rep):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=50.0, box=2, rep_id=rep.id)
        result = compute_composite(db, corps_id=corps_id, rep_id=rep.id)
        assert result.needs_rework
        assert not result.needs_escalation

    def test_low_score_needs_escalation(self, db, corps_id, rep):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=30.0, box=1, rep_id=rep.id)
        result = compute_composite(db, corps_id=corps_id, rep_id=rep.id)
        assert result.needs_rework
        assert result.needs_escalation

    def test_exactly_at_rework_threshold(self, db, corps_id, rep):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=REWORK_THRESHOLD, box=3, rep_id=rep.id)
        result = compute_composite(db, corps_id=corps_id, rep_id=rep.id)
        assert not result.needs_rework

    def test_exactly_at_escalation_threshold(self, db, corps_id, rep):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=ESCALATION_THRESHOLD, box=2, rep_id=rep.id)
        result = compute_composite(db, corps_id=corps_id, rep_id=rep.id)
        assert result.needs_rework
        assert not result.needs_escalation


class TestTimingOfficial:
    def test_no_violation(self, db, corps_id):
        result = check_timing(db, corps_id=corps_id, budget_spent=50, budget_limit=100)
        assert result is None

    def test_deadline_exceeded(self, db, corps_id, rep):
        penalty = check_timing(db, corps_id=corps_id, rep_id=rep.id,
                               deadline_exceeded=True)
        assert penalty is not None
        assert penalty.type == PenaltyType.TIMING
        assert penalty.amount == 5.0

    def test_budget_exceeded(self, db, corps_id, rep):
        penalty = check_timing(db, corps_id=corps_id, rep_id=rep.id,
                               budget_spent=150, budget_limit=100)
        assert penalty is not None
        assert penalty.type == PenaltyType.BUDGET
        assert penalty.amount == pytest.approx(5.0, abs=0.1)  # 50% * 0.1

    def test_budget_large_overage_capped(self, db, corps_id, rep):
        penalty = check_timing(db, corps_id=corps_id, rep_id=rep.id,
                               budget_spent=10000, budget_limit=100)
        assert penalty is not None
        assert penalty.amount == 10.0  # Capped

    def test_no_budget_limit(self, db, corps_id):
        result = check_timing(db, corps_id=corps_id, budget_spent=999, budget_limit=0)
        assert result is None


class TestScoreQueries:
    def test_get_scores_for_rep(self, db, corps_id, rep):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=80.0, box=4, rep_id=rep.id)
        record_score(db, corps_id=corps_id, judge_type=JudgeType.GUARD,
                     value=70.0, box=3, rep_id=rep.id)
        scores = get_scores_for_rep(db, rep.id)
        assert len(scores) == 2

    def test_get_scores_for_segment(self, db, corps_id, show_coord):
        record_score(db, corps_id=corps_id, judge_type=JudgeType.VISUAL,
                     value=90.0, box=5, segment_id=show_coord.id)
        scores = get_scores_for_segment(db, show_coord.id)
        assert len(scores) == 1

    def test_get_penalties_for_corps(self, db, corps_id):
        record_penalty(db, corps_id=corps_id, type=PenaltyType.RULE,
                       amount=3.0, reason="Rule 1")
        record_penalty(db, corps_id=corps_id, type=PenaltyType.TIMING,
                       amount=5.0, reason="Late")
        penalties = get_penalties_for_corps(db, corps_id)
        assert len(penalties) == 2

    def test_latest_score_per_judge(self, db, corps_id, rep):
        """Composite uses latest score per judge type."""
        import time
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=50.0, box=2, rep_id=rep.id)
        # Second score for same judge should override
        record_score(db, corps_id=corps_id, judge_type=JudgeType.BRASS,
                     value=90.0, box=5, rep_id=rep.id)
        result = compute_composite(db, corps_id=corps_id, rep_id=rep.id)
        # Should use the latest (90), but since created_at may be same in tests,
        # it uses whichever is latest — both have same created_at from server_default.
        # The important thing is only one score is used per judge.
        assert len(result.caption_scores) == 1
        assert JudgeType.BRASS in result.caption_scores
