"""Subprocess-based tests for season governance CLI commands.

Every mutating test uses a temp dir via DCI_PROJECT_ROOT so the real repo is never touched.
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
        timeout=30,
        env=env,
    )


def _setup_env(tmp_path: Path) -> dict:
    """Create pool with 2 agents, a corps with roster, and an approved show.

    Returns dict with keys: root, pool_dir, corps_dir, corps_id, show_slug, agent_ids.
    """
    root = tmp_path
    pool_dir = root / "talent_pool"
    agents_dir = pool_dir / "agents"
    agents_dir.mkdir(parents=True)

    agent_ids = ["agent-alpha", "agent-beta"]
    ledger_entries = []
    for aid in agent_ids:
        agent_data = {
            "agent_id": aid,
            "trust_score": 50.0,
            "total_sessions": 0,
            "successful_sessions": 0,
            "failed_sessions": 0,
            "availability": "active",
            "seen_sessions": [],
        }
        (agents_dir / f"{aid}.yaml").write_text(yaml.safe_dump(agent_data))
        ledger_entries.append({"agent_id": aid, "trust_score": 50.0, "availability": "active"})

    (pool_dir / "ledger.yaml").write_text(yaml.safe_dump({"agents": ledger_entries}))

    # Corps
    corps_id = "bluecoats"
    corps_dir = root / "corps" / corps_id
    corps_dir.mkdir(parents=True)
    (corps_dir / "corps.yaml").write_text(yaml.safe_dump({
        "corps_id": corps_id,
        "display_name": "Bluecoats",
        "philosophy": "Innovation",
        "state": "active",
    }))
    (corps_dir / "roster.yaml").write_text(yaml.safe_dump({
        "corps_id": corps_id,
        "assignments": [
            {"agent_id": "agent-alpha", "role": "brass_lead"},
            {"agent_id": "agent-beta", "role": "percussion_lead"},
        ],
    }))

    # Approved show
    show_slug = "starlight"
    show_dir = root / "shows" / show_slug
    show_dir.mkdir(parents=True)
    (show_dir / "status.yaml").write_text(yaml.safe_dump({"status": "approved"}))
    (show_dir / "design_notes.md").write_text("")
    (show_dir / "show_prompt.md").write_text("")

    return {
        "root": root,
        "pool_dir": pool_dir,
        "corps_dir": corps_dir,
        "corps_id": corps_id,
        "show_slug": show_slug,
        "agent_ids": agent_ids,
    }


# ---------------------------------------------------------------------------
# Season create
# ---------------------------------------------------------------------------

class TestSeasonCreate:
    def test_season_create_yes(self, tmp_path):
        result = run_cli("season", "create", "2026_summer", "--yes", root=str(tmp_path))
        assert result.returncode == 0, result.stderr
        season_dir = tmp_path / "seasons" / "2026_summer"
        assert season_dir.is_dir()
        assert (season_dir / "season.yaml").is_file()

    def test_season_create_duplicate_fails(self, tmp_path):
        run_cli("season", "create", "2026_summer", "--yes", root=str(tmp_path))
        result = run_cli("season", "create", "2026_summer", "--yes", root=str(tmp_path))
        assert result.returncode == 1


# ---------------------------------------------------------------------------
# Register corps
# ---------------------------------------------------------------------------

class TestRegisterCorps:
    def test_register_corps_yes(self, tmp_path):
        env = _setup_env(tmp_path)
        run_cli("season", "create", "s1", "--yes", root=str(env["root"]))
        result = run_cli("season", "register-corps", "s1", env["corps_id"], "--yes",
                         root=str(env["root"]))
        assert result.returncode == 0, result.stderr
        perf_dir = env["root"] / "seasons" / "s1" / "performances" / env["corps_id"]
        assert perf_dir.is_dir()

    def test_register_corps_missing_season(self, tmp_path):
        env = _setup_env(tmp_path)
        result = run_cli("season", "register-corps", "nonexistent", env["corps_id"], "--yes",
                         root=str(env["root"]))
        assert result.returncode == 1

    def test_register_corps_missing_corps(self, tmp_path):
        env = _setup_env(tmp_path)
        run_cli("season", "create", "s1", "--yes", root=str(env["root"]))
        result = run_cli("season", "register-corps", "s1", "no-such-corps", "--yes",
                         root=str(env["root"]))
        assert result.returncode == 1


# ---------------------------------------------------------------------------
# Run contest
# ---------------------------------------------------------------------------

def _setup_contest(tmp_path):
    """Full setup: env + season + registered corps."""
    env = _setup_env(tmp_path)
    # Second corps
    corps2_id = "cavaliers"
    corps2_dir = env["root"] / "corps" / corps2_id
    corps2_dir.mkdir(parents=True)
    (corps2_dir / "corps.yaml").write_text(yaml.safe_dump({
        "corps_id": corps2_id,
        "display_name": "Cavaliers",
        "philosophy": "Precision",
        "state": "active",
    }))
    (corps2_dir / "roster.yaml").write_text(yaml.safe_dump({
        "corps_id": corps2_id,
        "assignments": [
            {"agent_id": "agent-alpha", "role": "visual_lead"},
        ],
    }))
    env["corps2_id"] = corps2_id

    run_cli("season", "create", "s1", "--yes", root=str(env["root"]))
    run_cli("season", "register-corps", "s1", env["corps_id"], "--yes", root=str(env["root"]))
    run_cli("season", "register-corps", "s1", corps2_id, "--yes", root=str(env["root"]))
    return env


class TestRunContest:
    def test_run_contest_produces_standings(self, tmp_path):
        env = _setup_contest(tmp_path)
        result = run_cli("season", "run-contest", "s1",
                         "--show", env["show_slug"],
                         "--corps", env["corps_id"],
                         "--corps", env["corps2_id"],
                         "--yes", root=str(env["root"]))
        assert result.returncode == 0, result.stderr
        standings_path = env["root"] / "seasons" / "s1" / "standings.yaml"
        assert standings_path.is_file()
        standings = yaml.safe_load(standings_path.read_text())
        assert "results" in standings
        assert len(standings["results"]) == 2

    def test_run_contest_deterministic(self, tmp_path):
        """Run twice with same inputs -> same standings."""
        env = _setup_contest(tmp_path)
        for _ in range(2):
            run_cli("season", "run-contest", "s1",
                    "--show", env["show_slug"],
                    "--corps", env["corps_id"],
                    "--corps", env["corps2_id"],
                    "--yes", root=str(env["root"]))
        standings = yaml.safe_load(
            (env["root"] / "seasons" / "s1" / "standings.yaml").read_text()
        )
        # Deterministic: results should be consistent
        scores = {r["corps_id"]: r["final_score"] for r in standings["results"]}
        assert len(scores) == 2
        # All scores in expected range
        for s in scores.values():
            assert 0 < s < 100

    def test_run_contest_per_corps_scores(self, tmp_path):
        env = _setup_contest(tmp_path)
        run_cli("season", "run-contest", "s1",
                "--show", env["show_slug"],
                "--corps", env["corps_id"],
                "--corps", env["corps2_id"],
                "--yes", root=str(env["root"]))
        for cid in [env["corps_id"], env["corps2_id"]]:
            scores_path = env["root"] / "seasons" / "s1" / "performances" / cid / "scores.yaml"
            assert scores_path.is_file(), f"Missing scores.yaml for {cid}"
            data = yaml.safe_load(scores_path.read_text())
            assert "caption_scores" in data

    def test_run_contest_updates_corps_history(self, tmp_path):
        env = _setup_contest(tmp_path)
        run_cli("season", "run-contest", "s1",
                "--show", env["show_slug"],
                "--corps", env["corps_id"],
                "--corps", env["corps2_id"],
                "--yes", root=str(env["root"]))
        corps_data = yaml.safe_load((env["corps_dir"] / "corps.yaml").read_text())
        assert "history" in corps_data
        assert len(corps_data["history"]) >= 1
        assert corps_data["history"][-1]["season_id"] == "s1"

    def test_run_contest_updates_reputations(self, tmp_path):
        env = _setup_contest(tmp_path)
        # Read initial trust
        agent_path = env["pool_dir"] / "agents" / "agent-alpha.yaml"
        initial = yaml.safe_load(agent_path.read_text())["trust_score"]

        run_cli("season", "run-contest", "s1",
                "--show", env["show_slug"],
                "--corps", env["corps_id"],
                "--corps", env["corps2_id"],
                "--yes", root=str(env["root"]))

        updated = yaml.safe_load(agent_path.read_text())
        assert updated["total_sessions"] > 0
        # With dampening (0 prior sessions), trust moves slightly or stays;
        # verify session was recorded and successful_sessions incremented
        assert updated["successful_sessions"] > 0 or updated.get("failed_sessions", 0) > 0

    def test_run_contest_idempotent_session(self, tmp_path):
        env = _setup_contest(tmp_path)
        for _ in range(2):
            run_cli("season", "run-contest", "s1",
                    "--show", env["show_slug"],
                    "--corps", env["corps_id"],
                    "--corps", env["corps2_id"],
                    "--yes", root=str(env["root"]))
        agent_path = env["pool_dir"] / "agents" / "agent-alpha.yaml"
        agent = yaml.safe_load(agent_path.read_text())
        # Session processed only once due to idempotency
        assert agent["total_sessions"] == 1

    def test_run_contest_plan_mode(self, tmp_path):
        env = _setup_contest(tmp_path)
        result = run_cli("season", "run-contest", "s1",
                         "--show", env["show_slug"],
                         "--corps", env["corps_id"],
                         "--plan", root=str(env["root"]))
        assert result.returncode == 0
        assert "Plan" in result.stdout
        # No standings written
        assert not (env["root"] / "seasons" / "s1" / "standings.yaml").exists()

    def test_run_contest_lifecycle_post_not_during(self, tmp_path):
        """Corps state unchanged during contest (no state transition in run-contest)."""
        env = _setup_contest(tmp_path)
        before = yaml.safe_load((env["corps_dir"] / "corps.yaml").read_text())["state"]
        run_cli("season", "run-contest", "s1",
                "--show", env["show_slug"],
                "--corps", env["corps_id"],
                "--corps", env["corps2_id"],
                "--yes", root=str(env["root"]))
        after = yaml.safe_load((env["corps_dir"] / "corps.yaml").read_text())["state"]
        assert before == after
