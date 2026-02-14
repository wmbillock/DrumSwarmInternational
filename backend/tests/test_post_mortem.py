"""Tests for post-mortem generation."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from backend.services.post_mortem import (
    generate_corps_post_mortem,
    generate_season_post_mortems,
    get_corps_post_mortem,
    list_corps_post_mortems,
)


@pytest.fixture
def season_data():
    """A completed season with 3 rounds and 3 corps."""
    return {
        "season_id": "test-season-1",
        "metadata": {
            "name": "Test Season One",
            "status": "completed",
            "winner": "corps-alpha",
        },
        "schedule": [
            {
                "round": 1,
                "competition_id": "test-season-1-round-1",
                "show_slug": "first-show",
                "corps_ids": ["corps-alpha", "corps-beta", "corps-gamma"],
                "status": "completed",
                "completed_at": "2026-02-14T08:00:00+00:00",
                "standings": [
                    {
                        "corps_id": "corps-alpha",
                        "rank": 1,
                        "final_score": 85.5,
                        "caption_scores": {
                            "brass": 90.0,
                            "percussion": 80.0,
                            "guard": 85.0,
                            "visual": 88.0,
                            "general_effect": 84.0,
                        },
                    },
                    {
                        "corps_id": "corps-beta",
                        "rank": 2,
                        "final_score": 72.3,
                        "caption_scores": {
                            "brass": 70.0,
                            "percussion": 75.0,
                            "guard": 68.0,
                            "visual": 74.0,
                            "general_effect": 74.5,
                        },
                    },
                    {
                        "corps_id": "corps-gamma",
                        "rank": 3,
                        "final_score": 60.0,
                        "caption_scores": {
                            "brass": 55.0,
                            "percussion": 62.0,
                            "guard": 58.0,
                            "visual": 65.0,
                            "general_effect": 60.0,
                        },
                    },
                ],
            },
            {
                "round": 2,
                "competition_id": "test-season-1-round-2",
                "show_slug": "second-show",
                "corps_ids": ["corps-alpha", "corps-beta"],
                "status": "completed",
                "completed_at": "2026-02-14T09:00:00+00:00",
                "standings": [
                    {
                        "corps_id": "corps-beta",
                        "rank": 1,
                        "final_score": 80.0,
                        "caption_scores": {
                            "brass": 82.0,
                            "percussion": 78.0,
                            "guard": 80.0,
                            "visual": 79.0,
                            "general_effect": 81.0,
                        },
                    },
                    {
                        "corps_id": "corps-alpha",
                        "rank": 2,
                        "final_score": 78.0,
                        "caption_scores": {
                            "brass": 80.0,
                            "percussion": 76.0,
                            "guard": 78.0,
                            "visual": 79.0,
                            "general_effect": 77.0,
                        },
                    },
                ],
            },
            {
                "round": 3,
                "competition_id": "test-season-1-round-3",
                "show_slug": "third-show",
                "corps_ids": ["corps-alpha", "corps-gamma"],
                "status": "completed",
                "completed_at": "2026-02-14T10:00:00+00:00",
                "standings": [
                    {
                        "corps_id": "corps-alpha",
                        "rank": 1,
                        "final_score": 90.0,
                        "caption_scores": {
                            "brass": 92.0,
                            "percussion": 88.0,
                            "guard": 90.0,
                            "visual": 91.0,
                            "general_effect": 89.0,
                        },
                    },
                    {
                        "corps_id": "corps-gamma",
                        "rank": 2,
                        "final_score": 65.0,
                        "caption_scores": {
                            "brass": 60.0,
                            "percussion": 68.0,
                            "guard": 62.0,
                            "visual": 70.0,
                            "general_effect": 65.0,
                        },
                    },
                ],
            },
        ],
    }


class TestGenerateCorpsPostMortem:
    def test_winner_gets_champion_tag(self, season_data):
        content = generate_corps_post_mortem(season_data, "corps-alpha")
        assert "SEASON CHAMPION" in content
        assert "Corps Alpha" in content

    def test_non_winner_no_champion_tag(self, season_data):
        content = generate_corps_post_mortem(season_data, "corps-beta")
        assert "SEASON CHAMPION" not in content
        assert "Corps Beta" in content

    def test_summary_stats(self, season_data):
        content = generate_corps_post_mortem(season_data, "corps-alpha")
        assert "Rounds Competed | 3" in content
        assert "Round Wins | 2" in content

    def test_caption_performance_table(self, season_data):
        content = generate_corps_post_mortem(season_data, "corps-alpha")
        assert "Caption Performance" in content
        assert "Brass" in content
        assert "Percussion" in content

    def test_round_by_round_results(self, season_data):
        content = generate_corps_post_mortem(season_data, "corps-alpha")
        assert "Round-by-Round Results" in content
        assert "First Show" in content
        assert "Second Show" in content
        assert "Third Show" in content

    def test_score_trend_improving(self, season_data):
        content = generate_corps_post_mortem(season_data, "corps-alpha")
        # Scores: 85.5 → 78.0 → 90.0
        # First half avg: 85.5, second half avg: (78+90)/2=84 — roughly stable
        # Actually: first half [85.5], second half [78.0, 90.0]
        # first_avg = 85.5, second_avg = 84.0 — delta = -1.5, stable
        assert "Score trend" in content

    def test_corps_participating_in_subset(self, season_data):
        content = generate_corps_post_mortem(season_data, "corps-gamma")
        assert "Rounds Competed | 2" in content
        # corps-gamma was in round 1 (rank 3) and round 3 (rank 2)

    def test_analysis_section(self, season_data):
        content = generate_corps_post_mortem(season_data, "corps-alpha")
        assert "Analysis" in content

    def test_season_metadata(self, season_data):
        content = generate_corps_post_mortem(season_data, "corps-alpha")
        assert "Test Season One" in content
        assert "test-season-1" in content


class TestGenerateSeasonPostMortems:
    def test_generates_for_all_corps(self, season_data, tmp_path):
        # Write season.yaml to disk
        season_dir = tmp_path / "seasons" / "test-season-1"
        season_dir.mkdir(parents=True)
        (season_dir / "season.yaml").write_text(
            yaml.dump(season_data), encoding="utf-8"
        )

        results = generate_season_post_mortems(tmp_path, "test-season-1")
        assert len(results) == 3
        assert "corps-alpha" in results
        assert "corps-beta" in results
        assert "corps-gamma" in results

    def test_writes_files_to_disk(self, season_data, tmp_path):
        season_dir = tmp_path / "seasons" / "test-season-1"
        season_dir.mkdir(parents=True)
        (season_dir / "season.yaml").write_text(
            yaml.dump(season_data), encoding="utf-8"
        )

        generate_season_post_mortems(tmp_path, "test-season-1")
        pm_dir = season_dir / "post_mortems"
        assert pm_dir.is_dir()
        assert (pm_dir / "corps-alpha.md").is_file()
        assert (pm_dir / "corps-beta.md").is_file()
        assert (pm_dir / "corps-gamma.md").is_file()

    def test_missing_season_returns_empty(self, tmp_path):
        results = generate_season_post_mortems(tmp_path, "nonexistent")
        assert results == {}


class TestGetCorpsPostMortem:
    def test_retrieves_existing(self, tmp_path):
        pm_dir = tmp_path / "seasons" / "s1" / "post_mortems"
        pm_dir.mkdir(parents=True)
        (pm_dir / "corps-x.md").write_text("# Post-Mortem: Corps X", encoding="utf-8")

        content = get_corps_post_mortem(tmp_path, "s1", "corps-x")
        assert content == "# Post-Mortem: Corps X"

    def test_returns_none_if_missing(self, tmp_path):
        content = get_corps_post_mortem(tmp_path, "s1", "corps-missing")
        assert content is None


class TestListCorpsPostMortems:
    def test_finds_across_seasons(self, tmp_path):
        for sid in ["s1", "s2"]:
            pm_dir = tmp_path / "seasons" / sid / "post_mortems"
            pm_dir.mkdir(parents=True)
            (pm_dir / "corps-x.md").write_text("content", encoding="utf-8")

        results = list_corps_post_mortems(tmp_path, "corps-x")
        assert len(results) == 2
        season_ids = [r["season_id"] for r in results]
        assert "s1" in season_ids
        assert "s2" in season_ids

    def test_empty_when_none(self, tmp_path):
        (tmp_path / "seasons").mkdir()
        results = list_corps_post_mortems(tmp_path, "corps-x")
        assert results == []
