"""Tests for scoring_persistence — round-trip YAML save/load."""

import pytest

from backend.models.score import JudgeType
from backend.services.scoring_engine import CorpsResult, Standings
from backend.services.scoring_persistence import (
    load_corps_scores,
    load_standings,
    save_corps_scores,
    save_standings,
)


def _make_result(corps_id: str = "corps_a", rank: int = 1, final_score: float = 85.0) -> CorpsResult:
    return CorpsResult(
        corps_id=corps_id,
        caption_scores={JudgeType.BRASS: 90.0, JudgeType.PERCUSSION: 80.0},
        penalties_total=5.0,
        difficulty_coefficient=1.0,
        raw_score=90.0,
        final_score=final_score,
        rank=rank,
    )


def _make_standings(season_id: str = "s1") -> Standings:
    return Standings(
        season_id=season_id,
        results=[_make_result("corps_a", 1, 90.0), _make_result("corps_b", 2, 80.0)],
        generated_at="2025-01-01T00:00:00+00:00",
    )


class TestStandingsRoundTrip:
    def test_save_and_load(self, tmp_path):
        standings = _make_standings()
        save_standings(tmp_path, "s1", standings)
        loaded = load_standings(tmp_path, "s1")
        assert loaded.season_id == standings.season_id
        assert loaded.generated_at == standings.generated_at
        assert len(loaded.results) == 2
        assert loaded.results[0].corps_id == "corps_a"
        assert loaded.results[0].final_score == 90.0
        assert loaded.results[1].corps_id == "corps_b"
        assert loaded.results[1].rank == 2

    def test_caption_scores_preserved(self, tmp_path):
        standings = _make_standings()
        save_standings(tmp_path, "s1", standings)
        loaded = load_standings(tmp_path, "s1")
        assert loaded.results[0].caption_scores[JudgeType.BRASS] == 90.0
        assert loaded.results[0].caption_scores[JudgeType.PERCUSSION] == 80.0

    def test_file_location(self, tmp_path):
        standings = _make_standings()
        path = save_standings(tmp_path, "s1", standings)
        assert path == tmp_path / "seasons" / "s1" / "standings.yaml"
        assert path.exists()

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_standings(tmp_path, "nonexistent")


class TestCorpsScoresRoundTrip:
    def test_save_and_load(self, tmp_path):
        result = _make_result()
        save_corps_scores(tmp_path, "s1", "corps_a", result)
        loaded = load_corps_scores(tmp_path, "s1", "corps_a")
        assert loaded.corps_id == result.corps_id
        assert loaded.final_score == result.final_score
        assert loaded.raw_score == result.raw_score
        assert loaded.penalties_total == result.penalties_total
        assert loaded.difficulty_coefficient == result.difficulty_coefficient
        assert loaded.rank == result.rank

    def test_caption_scores_preserved(self, tmp_path):
        result = _make_result()
        save_corps_scores(tmp_path, "s1", "corps_a", result)
        loaded = load_corps_scores(tmp_path, "s1", "corps_a")
        assert loaded.caption_scores[JudgeType.BRASS] == 90.0

    def test_file_location(self, tmp_path):
        result = _make_result()
        path = save_corps_scores(tmp_path, "s1", "corps_a", result)
        assert path == tmp_path / "seasons" / "s1" / "performances" / "corps_a" / "scores.yaml"
        assert path.exists()

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_corps_scores(tmp_path, "s1", "nonexistent")
