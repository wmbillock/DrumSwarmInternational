"""Tests for season persistence layer."""

import pytest

from backend.services.season_persistence import (
    create_season,
    list_registered_corps,
    load_season,
    register_corps,
)


def _make_corps(tmp_path, corps_id: str):
    """Create a minimal corps directory with corps.yaml."""
    import yaml

    corps_dir = tmp_path / "corps" / corps_id
    corps_dir.mkdir(parents=True)
    (corps_dir / "corps.yaml").write_text(
        yaml.dump({"corps_id": corps_id, "display_name": corps_id, "philosophy": "test", "state": "active"})
    )
    return tmp_path / "corps"


# --- TestCreateSeason ---


class TestCreateSeason:
    def test_creates_required_files(self, tmp_path):
        season_dir = create_season(tmp_path, "season-2025")
        assert (season_dir / "scorecard.md").exists()
        assert (season_dir / "lifecycle_rules.md").exists()

    def test_duplicate_raises(self, tmp_path):
        create_season(tmp_path, "season-2025")
        with pytest.raises(ValueError, match="already exists"):
            create_season(tmp_path, "season-2025")

    def test_scorecard_has_caption_headings(self, tmp_path):
        season_dir = create_season(tmp_path, "season-2025")
        content = (season_dir / "scorecard.md").read_text()
        for heading in ("Brass", "Percussion", "Guard", "Visual", "General Effect"):
            assert f"## {heading}" in content

    def test_returns_season_path(self, tmp_path):
        path = create_season(tmp_path, "season-2025")
        assert path == tmp_path / "seasons" / "season-2025"

    def test_metadata_stored(self, tmp_path):
        create_season(tmp_path, "season-2025", metadata={"theme": "heroes"})
        info = load_season(tmp_path / "seasons" / "season-2025")
        assert info["metadata"]["theme"] == "heroes"


# --- TestRegisterCorps ---


class TestRegisterCorps:
    def test_requires_valid_season(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="season"):
            register_corps(tmp_path / "seasons" / "nope", "bd", tmp_path / "corps")

    def test_requires_valid_corps(self, tmp_path):
        season_dir = create_season(tmp_path, "s1")
        with pytest.raises(FileNotFoundError, match="corps"):
            register_corps(season_dir, "ghost", tmp_path / "corps")

    def test_creates_performance_dir(self, tmp_path):
        corps_base = _make_corps(tmp_path, "bd")
        season_dir = create_season(tmp_path, "s1")
        perf_dir = register_corps(season_dir, "bd", corps_base)
        assert perf_dir.is_dir()
        assert perf_dir == season_dir / "performances" / "bd"

    def test_idempotent_reregister(self, tmp_path):
        corps_base = _make_corps(tmp_path, "bd")
        season_dir = create_season(tmp_path, "s1")
        p1 = register_corps(season_dir, "bd", corps_base)
        p2 = register_corps(season_dir, "bd", corps_base)
        assert p1 == p2


# --- TestLoadSeason ---


class TestLoadSeason:
    def test_round_trip(self, tmp_path):
        season_dir = create_season(tmp_path, "s1")
        info = load_season(season_dir)
        assert info["season_id"] == "s1"
        assert info["registered_corps"] == []

    def test_missing_files_raise(self, tmp_path):
        fake = tmp_path / "seasons" / "bad"
        fake.mkdir(parents=True)
        with pytest.raises(FileNotFoundError):
            load_season(fake)


# --- TestListRegisteredCorps ---


class TestListRegisteredCorps:
    def test_empty_season(self, tmp_path):
        season_dir = create_season(tmp_path, "s1")
        assert list_registered_corps(season_dir) == []

    def test_after_registrations(self, tmp_path):
        corps_base = _make_corps(tmp_path, "bd")
        _make_corps(tmp_path, "cv")
        season_dir = create_season(tmp_path, "s1")
        register_corps(season_dir, "bd", corps_base)
        register_corps(season_dir, "cv", corps_base)
        result = list_registered_corps(season_dir)
        assert sorted(result) == ["bd", "cv"]
