"""TDD tests for corps history index building."""

import yaml
from pathlib import Path

import pytest

from backend.services.corps_history import (
    build_history_index,
    load_history_index,
    get_history_entry,
)


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _make_corps(tmp_path: Path, corps_id: str, history: list) -> None:
    _write_yaml(tmp_path / "corps" / corps_id / "corps.yaml", {
        "corps_id": corps_id,
        "display_name": corps_id.title(),
        "philosophy": "",
        "state": "active",
        "history": history,
    })


# ---------------------------------------------------------------------------
# History Index Building
# ---------------------------------------------------------------------------

class TestBuildIndex:
    def test_build_index_from_single_season(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [
            {"season_id": "s1", "placement": 1, "final_score": 85.0, "notes": "show:my-show"},
        ])
        _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {"season_id": "s1", "results": []})
        _write_yaml(tmp_path / "seasons" / "s1" / "performances" / "cavaliers" / "scores.yaml", {"corps_id": "cavaliers"})
        _write_yaml(tmp_path / "shows" / "my-show" / "status.yaml", {"status": "approved"})
        _write_text(tmp_path / "shows" / "my-show" / "design_notes.md", "notes")
        _write_text(tmp_path / "shows" / "my-show" / "show_prompt.md", "prompt")

        index = build_history_index(tmp_path, "cavaliers")

        assert index["corps_id"] == "cavaliers"
        assert len(index["entries"]) == 1
        entry = index["entries"][0]
        assert entry["entry_id"] == "cavaliers-s1"
        assert entry["season_id"] == "s1"
        assert entry["show_slug"] == "my-show"
        assert entry["placement"] == 1
        assert entry["final_score"] == 85.0
        assert entry["artifacts"]["standings"] == "seasons/s1/standings.yaml"
        assert entry["artifacts"]["corps_scores"] == "seasons/s1/performances/cavaliers/scores.yaml"
        assert entry["artifacts"]["show_status"] == "shows/my-show/status.yaml"
        assert entry["artifacts"]["design_notes"] == "shows/my-show/design_notes.md"
        assert entry["artifacts"]["show_prompt"] == "shows/my-show/show_prompt.md"

    def test_build_index_deduplicates_seasons(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [
            {"season_id": "s1", "placement": 2, "final_score": 70.0, "notes": ""},
            {"season_id": "s1", "placement": 1, "final_score": 85.0, "notes": "show:my-show"},
        ])
        _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {"season_id": "s1", "results": []})

        index = build_history_index(tmp_path, "cavaliers")

        assert len(index["entries"]) == 1
        assert index["entries"][0]["placement"] == 1
        assert index["entries"][0]["show_slug"] == "my-show"

    def test_build_index_missing_show_artifacts(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [
            {"season_id": "s1", "placement": 1, "final_score": 80.0, "notes": "show:ghost-show"},
        ])
        _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {"season_id": "s1", "results": []})
        _write_yaml(tmp_path / "seasons" / "s1" / "performances" / "cavaliers" / "scores.yaml", {"corps_id": "cavaliers"})

        index = build_history_index(tmp_path, "cavaliers")

        entry = index["entries"][0]
        assert "standings" in entry["artifacts"]
        assert "corps_scores" in entry["artifacts"]
        assert "design_notes" not in entry["artifacts"]
        assert "show_prompt" not in entry["artifacts"]
        assert "show_status" not in entry["artifacts"]

    def test_build_index_discovers_runs(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [
            {"season_id": "s1", "placement": 1, "final_score": 80.0, "notes": "show:my-show"},
        ])
        _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {"season_id": "s1", "results": []})
        _write_yaml(
            tmp_path / "seasons" / "s1" / "performances" / "cavaliers" / "run-001" / "manifest.yaml",
            {"run_id": "run-001"},
        )
        _write_yaml(
            tmp_path / "seasons" / "s1" / "performances" / "cavaliers" / "run-002" / "manifest.yaml",
            {"run_id": "run-002"},
        )

        index = build_history_index(tmp_path, "cavaliers")

        assert sorted(index["entries"][0]["runs"]) == ["run-001", "run-002"]

    def test_build_index_empty_history(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [])

        index = build_history_index(tmp_path, "cavaliers")

        assert index["entries"] == []

    def test_build_index_no_notes_field(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [
            {"season_id": "s1", "placement": 3, "final_score": 65.0, "notes": ""},
        ])
        _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {"season_id": "s1", "results": []})

        index = build_history_index(tmp_path, "cavaliers")

        entry = index["entries"][0]
        assert entry["show_slug"] is None
        assert "show_status" not in entry["artifacts"]
        assert "design_notes" not in entry["artifacts"]
        assert "show_prompt" not in entry["artifacts"]

    def test_build_index_writes_yaml_file(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [
            {"season_id": "s1", "placement": 1, "final_score": 80.0, "notes": ""},
        ])
        _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {"season_id": "s1", "results": []})

        build_history_index(tmp_path, "cavaliers")

        index_path = tmp_path / "corps" / "cavaliers" / "history" / "index.yaml"
        assert index_path.exists()
        data = yaml.safe_load(index_path.read_text())
        assert data["corps_id"] == "cavaliers"
        assert len(data["entries"]) == 1

    def test_build_index_stable_ordering(self, tmp_path):
        """Multiple seasons are ordered by season_id."""
        _make_corps(tmp_path, "cavaliers", [
            {"season_id": "s2", "placement": 2, "final_score": 70.0, "notes": ""},
            {"season_id": "s1", "placement": 1, "final_score": 80.0, "notes": ""},
            {"season_id": "s3", "placement": 3, "final_score": 60.0, "notes": ""},
        ])
        for sid in ("s1", "s2", "s3"):
            _write_yaml(tmp_path / "seasons" / sid / "standings.yaml", {"season_id": sid, "results": []})

        index = build_history_index(tmp_path, "cavaliers")

        ids = [e["entry_id"] for e in index["entries"]]
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# Index Loading / Entry Lookup
# ---------------------------------------------------------------------------

class TestLoadAndGet:
    def test_load_index_returns_cached(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [
            {"season_id": "s1", "placement": 1, "final_score": 80.0, "notes": ""},
        ])
        _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {"season_id": "s1", "results": []})
        build_history_index(tmp_path, "cavaliers")

        # Mutate corps.yaml to prove we read from cache
        _make_corps(tmp_path, "cavaliers", [])

        index = load_history_index(tmp_path, "cavaliers")
        assert len(index["entries"]) == 1

    def test_load_index_builds_if_missing(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [
            {"season_id": "s1", "placement": 1, "final_score": 80.0, "notes": ""},
        ])
        _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {"season_id": "s1", "results": []})

        index = load_history_index(tmp_path, "cavaliers")
        assert len(index["entries"]) == 1

    def test_get_history_entry_found(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [
            {"season_id": "s1", "placement": 1, "final_score": 80.0, "notes": ""},
        ])
        _write_yaml(tmp_path / "seasons" / "s1" / "standings.yaml", {"season_id": "s1", "results": []})
        build_history_index(tmp_path, "cavaliers")

        entry = get_history_entry(tmp_path, "cavaliers", "cavaliers-s1")
        assert entry["season_id"] == "s1"

    def test_get_history_entry_not_found(self, tmp_path):
        _make_corps(tmp_path, "cavaliers", [])
        build_history_index(tmp_path, "cavaliers")

        with pytest.raises(ValueError, match="not found"):
            get_history_entry(tmp_path, "cavaliers", "cavaliers-nope")
