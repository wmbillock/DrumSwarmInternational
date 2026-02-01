"""Subprocess-based tests for `dci run show` milestone command."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip()


def run_cli(*args: str, root: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["DCI_PROJECT_ROOT"] = root
    # Force API client to connect to a port nothing listens on, so tests
    # always hit the offline/ConnectionError path instead of polling a live server.
    env["DCI_API_URL"] = "http://127.0.0.1:19999"
    return subprocess.run(
        [sys.executable, "-m", "backend.cli.main", *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=30,
        env=env,
    )


def _setup_env(tmp_path: Path) -> None:
    """Create approved show, corps, and season in tmp_path."""
    # Show (approved)
    show_dir = tmp_path / "shows" / "demo"
    show_dir.mkdir(parents=True)
    (show_dir / "status.yaml").write_text(yaml.safe_dump({"status": "approved"}))
    (show_dir / "design_notes.md").write_text("")
    (show_dir / "show_prompt.md").write_text("")

    # Corps
    corps_dir = tmp_path / "corps" / "bd"
    corps_dir.mkdir(parents=True)
    (corps_dir / "corps.yaml").write_text(yaml.safe_dump({
        "corps_id": "bd", "display_name": "Blue Devils",
        "philosophy": "Excellence", "state": "active",
    }))
    (corps_dir / "roster.yaml").write_text(yaml.safe_dump({"corps_id": "bd", "assignments": []}))

    # Season
    season_dir = tmp_path / "seasons" / "s1"
    season_dir.mkdir(parents=True)
    (season_dir / "season.yaml").write_text(yaml.safe_dump({"season_id": "s1", "metadata": {}}))
    (season_dir / "performances").mkdir()


def _setup_unapproved(tmp_path: Path) -> None:
    """Like _setup_env but show is draft."""
    _setup_env(tmp_path)
    show_dir = tmp_path / "shows" / "demo"
    (show_dir / "status.yaml").write_text(yaml.safe_dump({"status": "draft"}))


class TestRunShow:
    def test_run_show_rejects_unapproved(self, tmp_path):
        _setup_unapproved(tmp_path)
        result = run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                         "--yes", root=str(tmp_path))
        assert result.returncode == 1
        assert "approved" in result.stderr.lower()

    def test_run_show_plan(self, tmp_path):
        _setup_env(tmp_path)
        result = run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                         "--plan", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "manifest.yaml" in result.stdout
        # No files created
        perf_dir = tmp_path / "seasons" / "s1" / "performances" / "bd"
        run_dirs = list(perf_dir.iterdir()) if perf_dir.exists() else []
        assert len(run_dirs) == 0

    def test_run_show_yes(self, tmp_path):
        _setup_env(tmp_path)
        result = run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                         "--yes", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        perf_dir = tmp_path / "seasons" / "s1" / "performances" / "bd"
        run_dirs = [d for d in perf_dir.iterdir() if d.is_dir()]
        assert len(run_dirs) == 1
        assert (run_dirs[0] / "manifest.yaml").is_file()

    def test_run_show_manifest_structure(self, tmp_path):
        _setup_env(tmp_path)
        run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                "--yes", root=str(tmp_path))
        perf_dir = tmp_path / "seasons" / "s1" / "performances" / "bd"
        run_dir = next(perf_dir.iterdir())
        manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text())
        for key in ("run_id", "show_slug", "corps_id", "season_id", "started_at", "status", "config"):
            assert key in manifest, f"Missing key: {key}"

    def test_run_show_manifest_completed(self, tmp_path):
        _setup_env(tmp_path)
        run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                "--yes", root=str(tmp_path))
        perf_dir = tmp_path / "seasons" / "s1" / "performances" / "bd"
        run_dir = next(perf_dir.iterdir())
        manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text())
        assert manifest["status"] == "completed"
        assert "completed_at" in manifest

    def test_run_id_format(self, tmp_path):
        _setup_env(tmp_path)
        run_cli("run", "show", "demo", "--corps", "bd", "--season", "s1",
                "--yes", root=str(tmp_path))
        perf_dir = tmp_path / "seasons" / "s1" / "performances" / "bd"
        run_dir = next(perf_dir.iterdir())
        manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text())
        assert re.match(r"demo-bd-\d{8}T\d{6}", manifest["run_id"])

    def test_run_show_missing_corps(self, tmp_path):
        _setup_env(tmp_path)
        result = run_cli("run", "show", "demo", "--corps", "nope", "--season", "s1",
                         "--yes", root=str(tmp_path))
        assert result.returncode == 1

    def test_run_show_missing_season(self, tmp_path):
        _setup_env(tmp_path)
        result = run_cli("run", "show", "demo", "--corps", "bd", "--season", "nope",
                         "--yes", root=str(tmp_path))
        assert result.returncode == 1
