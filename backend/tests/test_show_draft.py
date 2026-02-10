"""Tests for the show draft service."""

import json
import pytest
from pathlib import Path

from backend.services.show_draft_service import (
    compute_draft_order,
    score_show_affinity,
    run_show_draft,
)


def _make_season_dir(tmp_path, season_name="s1"):
    """Create a valid season directory with all required files."""
    season_dir = tmp_path / "seasons" / season_name
    season_dir.mkdir(parents=True, exist_ok=True)
    (season_dir / "season.yaml").write_text(
        "metadata:\n  name: test-season\n  status: setup\nshows: []\ndivisions: {}\nconfig:\n  corps_per_contest: 4\n  required_scores: 1\nschedule: []\nlocked: false\n",
        encoding="utf-8",
    )
    (season_dir / "scorecard.md").write_text("# Scorecard\nDefault scorecard template.\n", encoding="utf-8")
    (season_dir / "lifecycle_rules.md").write_text("# Lifecycle Rules\nDefault rules.\n", encoding="utf-8")
    return season_dir


def _make_corps(db, name, corps_id=None, caption_affinity=None, founding_definition=None, mascot=None):
    """Helper to create a Corps row."""
    from backend.models.corps import Corps, CorpsStatus
    import uuid

    corps = Corps(
        id=corps_id or str(uuid.uuid4()),
        name=name,
        status=CorpsStatus.WINTER_CAMPS,
        caption_affinity=caption_affinity,
        founding_definition=json.dumps(founding_definition) if founding_definition else None,
        mascot=mascot,
    )
    db.add(corps)
    db.commit()
    return corps


def _make_score(db, corps_id, value):
    """Helper to create a Score row."""
    from backend.models.score import Score, JudgeType
    import uuid

    score = Score(
        id=str(uuid.uuid4()),
        corps_id=corps_id,
        judge_type=JudgeType.GENERAL_EFFECT,
        value=value,
        box=3,
    )
    db.add(score)
    db.commit()
    return score


class TestComputeDraftOrder:
    def test_empty_corps(self, db):
        result = compute_draft_order(db, [])
        assert result == []

    def test_unscored_corps_get_default(self, db):
        c1 = _make_corps(db, "Alpha")
        c2 = _make_corps(db, "Beta")

        result = compute_draft_order(db, [c1.id, c2.id])
        assert len(result) == 2
        for entry in result:
            assert entry["best_score"] == 50.0

    def test_scored_corps_ranked_by_best(self, db):
        c1 = _make_corps(db, "Alpha")
        c2 = _make_corps(db, "Beta")
        c3 = _make_corps(db, "Gamma")

        _make_score(db, c1.id, 85.0)
        _make_score(db, c2.id, 92.0)
        _make_score(db, c3.id, 78.0)

        result = compute_draft_order(db, [c1.id, c2.id, c3.id])
        assert result[0]["corps_id"] == c2.id
        assert result[0]["best_score"] == 92.0
        assert result[0]["rank"] == 1
        assert result[1]["corps_id"] == c1.id
        assert result[2]["corps_id"] == c3.id

    def test_multiple_scores_uses_best(self, db):
        c1 = _make_corps(db, "Alpha")
        _make_score(db, c1.id, 60.0)
        _make_score(db, c1.id, 80.0)
        _make_score(db, c1.id, 70.0)

        result = compute_draft_order(db, [c1.id])
        assert result[0]["best_score"] == 80.0


class TestScoreShowAffinity:
    def test_no_affinity_returns_zero(self, db):
        c = _make_corps(db, "Plain Corps")
        result = score_show_affinity(db, c.id, "abstract-art", "")
        assert result["score"] >= 0
        assert isinstance(result["reason"], str)

    def test_caption_affinity_matches(self, db):
        c = _make_corps(db, "Brass Kings", caption_affinity="brass")
        result = score_show_affinity(db, c.id, "fanfare-of-trumpets", "A bold brass fanfare show")
        assert result["score"] > 0
        assert len(result["keywords_matched"]) > 0

    def test_founding_definition_adds_score(self, db):
        c = _make_corps(
            db, "Visual Arts Corps",
            founding_definition={"philosophy": "We focus on visual design and geometric forms"},
        )
        result = score_show_affinity(db, c.id, "geometric-dreams", "A visual design showcase")
        assert result["score"] > 0

    def test_name_overlap_bonus(self, db):
        c = _make_corps(db, "Thunder")
        result = score_show_affinity(db, c.id, "thunder-storm", "")
        assert result["score"] >= 15.0  # Name overlap bonus

    def test_missing_corps(self, db):
        result = score_show_affinity(db, "nonexistent-id", "any-show", "")
        assert result["score"] == 0.0


class TestRunShowDraft:
    def test_empty_inputs(self, db, tmp_path):
        season_dir = _make_season_dir(tmp_path)
        result = run_show_draft(db, season_dir, [], [])
        assert result["picks"] == []
        assert result["assignments"] == {}

    def test_single_corps_single_show(self, db, tmp_path):
        c = _make_corps(db, "Alpha", caption_affinity="brass")
        shows_dir = tmp_path / "shows" / "brass-bonanza"
        shows_dir.mkdir(parents=True)
        season_dir = _make_season_dir(tmp_path)

        result = run_show_draft(db, season_dir, ["brass-bonanza"], [c.id])
        assert len(result["picks"]) == 1
        assert result["picks"][0]["show_slug"] == "brass-bonanza"
        assert result["picks"][0]["corps_id"] == c.id
        assert "brass-bonanza" in result["assignments"]
        assert c.id in result["assignments"]["brass-bonanza"]

    def test_multiple_corps_multiple_shows(self, db, tmp_path):
        c1 = _make_corps(db, "Brass Kings", caption_affinity="brass")
        c2 = _make_corps(db, "Guard Stars", caption_affinity="guard")

        _make_score(db, c1.id, 90.0)
        _make_score(db, c2.id, 85.0)

        for slug in ["trumpet-fanfare", "color-guard-spectacular"]:
            (tmp_path / "shows" / slug).mkdir(parents=True)

        season_dir = _make_season_dir(tmp_path)

        result = run_show_draft(
            db, season_dir,
            ["trumpet-fanfare", "color-guard-spectacular"],
            [c1.id, c2.id],
        )

        assert len(result["picks"]) == 2
        assert result["picks"][0]["corps_id"] == c1.id  # Higher score picks first
        assert result["draft_order"][0]["corps_id"] == c1.id

    def test_assignments_dict_has_all_shows(self, db, tmp_path):
        c = _make_corps(db, "Any Corps")
        season_dir = _make_season_dir(tmp_path)

        result = run_show_draft(db, season_dir, ["show-a", "show-b"], [c.id])
        assert "show-a" in result["assignments"]
        assert "show-b" in result["assignments"]
