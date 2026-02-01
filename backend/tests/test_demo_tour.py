"""Tests for dci demo tour — deterministic end-to-end lifecycle demo.

Subprocess-based, uses DCI_PROJECT_ROOT to isolate writes.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip()


def run_cli(*args: str, root: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if root:
        env["DCI_PROJECT_ROOT"] = root
    return subprocess.run(
        [sys.executable, "-m", "backend.cli.main", *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=60,
        env=env,
    )


class TestDemoTourPlan:
    def test_plan_mode_no_writes(self, tmp_path):
        """--plan shows preview, no files written."""
        result = run_cli("demo", "tour", "--plan", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "Plan:" in result.stdout
        assert "Init talent pool" in result.stdout
        # Nothing written
        assert not (tmp_path / "talent_pool").exists()
        assert not (tmp_path / "corps").exists()
        assert not (tmp_path / "seasons").exists()
        assert not (tmp_path / "docs").exists()

    def test_plan_mode_multi_season(self, tmp_path):
        """--plan with --seasons 3 shows all season steps and decay."""
        result = run_cli("demo", "tour", "--plan", "--seasons", "3", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        assert "tour-s1" in result.stdout
        assert "tour-s2" in result.stdout
        assert "tour-s3" in result.stdout
        assert "decay" in result.stdout


class TestDemoTourYes:
    def test_required_artifacts_exist(self, tmp_path):
        """--yes creates all required artifacts."""
        result = run_cli("demo", "tour", "--yes", root=str(tmp_path))
        assert result.returncode == 0, result.stderr

        # Pool
        assert (tmp_path / "talent_pool" / "ledger.yaml").is_file()
        agents_dir = tmp_path / "talent_pool" / "agents"
        assert agents_dir.is_dir()
        agent_files = list(agents_dir.glob("*.yaml"))
        assert len(agent_files) >= 10  # 2 corps * 5 instruments

        # Corps (at least 2)
        corps_dirs = [d for d in (tmp_path / "corps").iterdir() if d.is_dir()]
        assert len(corps_dirs) >= 2
        for cd in corps_dirs:
            assert (cd / "corps.yaml").is_file()
            assert (cd / "roster.yaml").is_file()
            # Corps history from contest
            corps_data = yaml.safe_load((cd / "corps.yaml").read_text())
            assert "history" in corps_data
            assert len(corps_data["history"]) >= 1

        # Show
        shows = list((tmp_path / "shows").iterdir())
        assert len(shows) >= 1
        show_dir = shows[0]
        status = yaml.safe_load((show_dir / "status.yaml").read_text())
        assert status["status"] == "approved"

        # Season
        season_dir = tmp_path / "seasons" / "tour-s1"
        assert season_dir.is_dir()
        assert (season_dir / "standings.yaml").is_file()
        standings = yaml.safe_load((season_dir / "standings.yaml").read_text())
        assert len(standings["results"]) >= 2

        # Per-corps scores
        for r in standings["results"]:
            scores_path = season_dir / "performances" / r["corps_id"] / "scores.yaml"
            assert scores_path.is_file()

        # Recap
        recap_path = tmp_path / "docs" / "outputs" / "tour_seed1.md"
        assert recap_path.is_file()
        recap = recap_path.read_text()
        assert "Tour Recap" in recap
        assert "Final Agent Trust Scores" in recap

    def test_multi_season_with_decay(self, tmp_path):
        """--seasons 2 runs two seasons with offseason decay between them."""
        result = run_cli("demo", "tour", "--yes", "--seasons", "2", root=str(tmp_path))
        assert result.returncode == 0, result.stderr

        # Both seasons exist
        assert (tmp_path / "seasons" / "tour-s1" / "standings.yaml").is_file()
        assert (tmp_path / "seasons" / "tour-s2" / "standings.yaml").is_file()

        # Recap mentions decay
        recap = (tmp_path / "docs" / "outputs" / "tour_seed1.md").read_text()
        assert "decay" in recap.lower()

    def test_three_corps(self, tmp_path):
        """--corps-count 3 creates 3 corps with standings for all 3."""
        result = run_cli("demo", "tour", "--yes", "--corps-count", "3", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        standings = yaml.safe_load(
            (tmp_path / "seasons" / "tour-s1" / "standings.yaml").read_text()
        )
        assert len(standings["results"]) == 3


class TestDemoTourDeterministic:
    def test_deterministic_same_seed(self, tmp_path):
        """Two runs with same seed produce identical standings scores."""
        dir_a = tmp_path / "run_a"
        dir_b = tmp_path / "run_b"
        dir_a.mkdir()
        dir_b.mkdir()

        for d in [dir_a, dir_b]:
            result = run_cli("demo", "tour", "--yes", "--seed", "42", root=str(d))
            assert result.returncode == 0, result.stderr

        standings_a = yaml.safe_load(
            (dir_a / "seasons" / "tour-s1" / "standings.yaml").read_text()
        )
        standings_b = yaml.safe_load(
            (dir_b / "seasons" / "tour-s1" / "standings.yaml").read_text()
        )

        # Same corps, same order, same scores
        for ra, rb in zip(standings_a["results"], standings_b["results"]):
            assert ra["corps_id"] == rb["corps_id"]
            assert ra["final_score"] == rb["final_score"]
            assert ra["rank"] == rb["rank"]
            assert ra["caption_scores"] == rb["caption_scores"]

    def test_different_seed_different_output(self, tmp_path):
        """Different seeds produce different standings."""
        dir_a = tmp_path / "seed1"
        dir_b = tmp_path / "seed2"
        dir_a.mkdir()
        dir_b.mkdir()

        run_cli("demo", "tour", "--yes", "--seed", "1", root=str(dir_a))
        run_cli("demo", "tour", "--yes", "--seed", "99", root=str(dir_b))

        standings_a = yaml.safe_load(
            (dir_a / "seasons" / "tour-s1" / "standings.yaml").read_text()
        )
        standings_b = yaml.safe_load(
            (dir_b / "seasons" / "tour-s1" / "standings.yaml").read_text()
        )

        # At least one score or corps name should differ
        scores_a = {r["corps_id"]: r["final_score"] for r in standings_a["results"]}
        scores_b = {r["corps_id"]: r["final_score"] for r in standings_b["results"]}
        assert scores_a != scores_b or set(scores_a.keys()) != set(scores_b.keys())

    def test_deterministic_multi_season(self, tmp_path):
        """Two runs with same seed and 2 seasons produce identical final trust scores."""
        dir_a = tmp_path / "run_a"
        dir_b = tmp_path / "run_b"
        dir_a.mkdir()
        dir_b.mkdir()

        for d in [dir_a, dir_b]:
            result = run_cli("demo", "tour", "--yes", "--seed", "7", "--seasons", "2", root=str(d))
            assert result.returncode == 0, result.stderr

        # Compare final agent trust scores
        for agent_file in (dir_a / "talent_pool" / "agents").glob("*.yaml"):
            a = yaml.safe_load(agent_file.read_text())
            b = yaml.safe_load((dir_b / "talent_pool" / "agents" / agent_file.name).read_text())
            assert a["trust_score"] == b["trust_score"], f"Mismatch for {agent_file.name}"
            assert a["total_sessions"] == b["total_sessions"]
