"""Tests for scoring_engine — deterministic scoring and ranking."""

import pytest

from backend.models.score import JudgeType
from backend.services.scoring_engine import (
    CorpsResult,
    Standings,
    compute_standings,
    rank_corps,
    score_corps,
)
from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS


def _make_composite(
    caption_scores: dict[JudgeType, float] | None = None,
    raw_total: float = 80.0,
    penalties_total: float = 0.0,
) -> CompositeScore:
    if caption_scores is None:
        caption_scores = {JudgeType.BRASS: 80.0, JudgeType.PERCUSSION: 80.0}
    final = max(0.0, raw_total - penalties_total)
    return CompositeScore(
        caption_scores=caption_scores,
        raw_total=raw_total,
        penalties_total=penalties_total,
        final_score=final,
        needs_rework=final < 60.0,
        needs_escalation=final < 40.0,
    )


class TestScoreCorps:
    def test_default_difficulty(self):
        c = _make_composite(raw_total=85.0, penalties_total=5.0)
        assert score_corps(c) == 80.0

    def test_difficulty_multiplier(self):
        c = _make_composite(raw_total=70.0, penalties_total=0.0)
        assert score_corps(c, difficulty=1.5) == 105.0

    def test_difficulty_with_penalties(self):
        c = _make_composite(raw_total=80.0, penalties_total=10.0)
        # 80 * 1.2 - 10 = 86.0
        assert score_corps(c, difficulty=1.2) == pytest.approx(86.0)


class TestRankCorps:
    def test_basic_ranking(self):
        scores = {"a": 90.0, "b": 80.0, "c": 85.0}
        ranked = rank_corps(scores)
        assert ranked == [("a", 1), ("c", 2), ("b", 3)]

    def test_ties_share_rank(self):
        scores = {"a": 90.0, "b": 90.0, "c": 80.0}
        ranked = rank_corps(scores)
        assert ranked[0][1] == 1
        assert ranked[1][1] == 1
        assert ranked[2][1] == 3  # skip rank 2

    def test_all_tied(self):
        scores = {"a": 50.0, "b": 50.0, "c": 50.0}
        ranked = rank_corps(scores)
        assert all(r == 1 for _, r in ranked)

    def test_single_corps(self):
        scores = {"a": 75.0}
        ranked = rank_corps(scores)
        assert ranked == [("a", 1)]

    def test_zero_scores(self):
        scores = {"a": 0.0, "b": 0.0}
        ranked = rank_corps(scores)
        assert all(r == 1 for _, r in ranked)


class TestComputeStandings:
    def test_deterministic_results(self):
        composites = {
            "corps_a": _make_composite(raw_total=90.0),
            "corps_b": _make_composite(raw_total=80.0),
        }
        s1 = compute_standings("s1", DEFAULT_WEIGHTS, composites)
        s2 = compute_standings("s1", DEFAULT_WEIGHTS, composites)
        assert [r.final_score for r in s1.results] == [r.final_score for r in s2.results]
        assert [r.rank for r in s1.results] == [r.rank for r in s2.results]

    def test_ranking_order(self):
        composites = {
            "corps_a": _make_composite(raw_total=70.0),
            "corps_b": _make_composite(raw_total=90.0),
            "corps_c": _make_composite(raw_total=80.0),
        }
        s = compute_standings("s1", DEFAULT_WEIGHTS, composites)
        assert s.results[0].corps_id == "corps_b"
        assert s.results[0].rank == 1
        assert s.results[1].corps_id == "corps_c"
        assert s.results[1].rank == 2
        assert s.results[2].corps_id == "corps_a"
        assert s.results[2].rank == 3

    def test_difficulty_can_reorder(self):
        composites = {
            "corps_a": _make_composite(raw_total=70.0),
            "corps_b": _make_composite(raw_total=80.0),
        }
        # corps_a with 2.0 difficulty: 70*2.0 = 140
        # corps_b with 1.0 difficulty: 80*1.0 = 80
        s = compute_standings("s1", DEFAULT_WEIGHTS, composites, {"corps_a": 2.0})
        assert s.results[0].corps_id == "corps_a"
        assert s.results[0].rank == 1

    def test_difficulty_defaults_to_one(self):
        composites = {"corps_a": _make_composite(raw_total=80.0)}
        s = compute_standings("s1", DEFAULT_WEIGHTS, composites)
        assert s.results[0].difficulty_coefficient == 1.0
        assert s.results[0].final_score == 80.0

    def test_penalties_applied(self):
        composites = {"corps_a": _make_composite(raw_total=80.0, penalties_total=5.0)}
        s = compute_standings("s1", DEFAULT_WEIGHTS, composites)
        assert s.results[0].final_score == 75.0

    def test_standings_metadata(self):
        composites = {"corps_a": _make_composite(raw_total=80.0)}
        s = compute_standings("s1", DEFAULT_WEIGHTS, composites)
        assert s.season_id == "s1"
        assert isinstance(s.generated_at, str)
        assert len(s.results) == 1

    def test_single_corps(self):
        composites = {"only": _make_composite(raw_total=50.0)}
        s = compute_standings("s1", DEFAULT_WEIGHTS, composites)
        assert s.results[0].rank == 1

    def test_all_tied(self):
        composites = {
            "a": _make_composite(raw_total=80.0),
            "b": _make_composite(raw_total=80.0),
            "c": _make_composite(raw_total=80.0),
        }
        s = compute_standings("s1", DEFAULT_WEIGHTS, composites)
        assert all(r.rank == 1 for r in s.results)

    def test_zero_scores(self):
        composites = {
            "a": _make_composite(raw_total=0.0),
            "b": _make_composite(raw_total=0.0),
        }
        s = compute_standings("s1", DEFAULT_WEIGHTS, composites)
        assert all(r.rank == 1 for r in s.results)
        assert all(r.final_score == 0.0 for r in s.results)
