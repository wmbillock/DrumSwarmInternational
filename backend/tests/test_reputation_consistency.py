"""Tests for reputation/ledger consistency fixes.

Covers: clamp, ledger sync, drafting-after-update, idempotency, input validation.
"""

import math
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from backend.models.score import JudgeType
from backend.services.reputation import (
    _clamp,
    _validate_score,
    apply_season_decay,
    update_reputations,
)
from backend.services.scoring_engine import CorpsResult, Standings


PROJECT_ROOT = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip()


def _make_agent(
    agent_id="agent-001",
    display_name="Alice",
    primary_instrument="brass",
    availability="active",
    trust_score=50.0,
    total_sessions=0,
    successful_sessions=0,
    failed_sessions=0,
    experience_seasons=0,
    **extra,
):
    d = dict(
        agent_id=agent_id,
        display_name=display_name,
        primary_instrument=primary_instrument,
        availability=availability,
        trust_score=trust_score,
        total_sessions=total_sessions,
        successful_sessions=successful_sessions,
        failed_sessions=failed_sessions,
        experience_seasons=experience_seasons,
    )
    d.update(extra)
    return d


def _write_pool(pool_dir, agents):
    pool_dir.mkdir(parents=True, exist_ok=True)
    (pool_dir / "agents").mkdir(exist_ok=True)
    ledger = {
        "agents": [
            {
                "agent_id": a["agent_id"],
                "display_name": a["display_name"],
                "primary_instrument": a["primary_instrument"],
                "availability": a["availability"],
                "trust_score": a["trust_score"],
            }
            for a in agents
        ]
    }
    (pool_dir / "ledger.yaml").write_text(yaml.dump(ledger, default_flow_style=False))
    for a in agents:
        (pool_dir / "agents" / f"{a['agent_id']}.yaml").write_text(
            yaml.dump(a, default_flow_style=False)
        )


def _read_agent(pool_dir, agent_id):
    return yaml.safe_load((pool_dir / "agents" / f"{agent_id}.yaml").read_text())


def _read_ledger(pool_dir):
    return yaml.safe_load((pool_dir / "ledger.yaml").read_text())


def _make_standings(corps_id="corps-A", final_score=80.0):
    return Standings(
        season_id="2025-spring",
        results=[
            CorpsResult(
                corps_id=corps_id,
                caption_scores={JudgeType.BRASS: final_score},
                penalties_total=0.0,
                difficulty_coefficient=1.0,
                raw_score=final_score,
                final_score=final_score,
                rank=1,
            )
        ],
        generated_at="2025-01-01T00:00:00+00:00",
    )


# ========== Clamp ==========


class TestClamp:
    def test_clamp_lower_bound(self):
        assert _clamp(-10.0) == 0.0

    def test_clamp_upper_bound(self):
        assert _clamp(150.0) == 100.0

    def test_clamp_within_range(self):
        assert _clamp(50.0) == 50.0


# ========== Ledger Sync ==========


class TestLedgerSync:
    def test_ledger_has_trust_score_after_reputation_update(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent(trust_score=50.0, total_sessions=10)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(final_score=90.0)
        update_reputations(standings, pool_dir, {"corps-A": ["agent-001"]}, session_id="s1")

        ledger = _read_ledger(pool_dir)
        entry = ledger["agents"][0]
        assert "trust_score" in entry
        agent_yaml = _read_agent(pool_dir, "agent-001")
        assert entry["trust_score"] == agent_yaml["trust_score"]

    def test_ledger_has_trust_score_after_decay(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent(trust_score=80.0, total_sessions=10)
        _write_pool(pool_dir, [agent])

        apply_season_decay(pool_dir, decay_rate=0.1, baseline=50.0)

        ledger = _read_ledger(pool_dir)
        entry = ledger["agents"][0]
        assert "trust_score" in entry
        agent_yaml = _read_agent(pool_dir, "agent-001")
        assert entry["trust_score"] == agent_yaml["trust_score"]

    def test_ledger_trust_matches_agent_yaml_after_multiple_updates(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent(trust_score=50.0, total_sessions=5)
        _write_pool(pool_dir, [agent])

        # Two reputation updates
        for i, score in enumerate([80.0, 90.0]):
            standings = _make_standings(final_score=score)
            update_reputations(
                standings, pool_dir, {"corps-A": ["agent-001"]}, session_id=f"s{i}"
            )

        # Then decay
        apply_season_decay(pool_dir, decay_rate=0.05, baseline=50.0)

        ledger = _read_ledger(pool_dir)
        entry = ledger["agents"][0]
        agent_yaml = _read_agent(pool_dir, "agent-001")
        assert entry["trust_score"] == agent_yaml["trust_score"]


# ========== Drafting after reputation ==========


class TestDraftingAfterReputation:
    def test_draft_ranking_changes_after_reputation_update(self, tmp_path):
        from backend.services.drafting import draft_roster, RoleRequirement

        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent(agent_id="a1", display_name="A1", trust_score=50.0, total_sessions=10),
            _make_agent(agent_id="a2", display_name="A2", trust_score=50.0, total_sessions=10),
        ]
        _write_pool(pool_dir, agents)

        # Before: tiebreaker is lexicographic → a1 wins
        result_before = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert result_before.summary["brass"] == ["a1"]

        # Boost a2 with high score
        standings = _make_standings(final_score=95.0)
        update_reputations(standings, pool_dir, {"corps-A": ["a2"]}, session_id="s1")

        # After: a2 has higher trust → a2 wins
        result_after = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert result_after.summary["brass"] == ["a2"]

    def test_draft_ranking_after_season_decay(self, tmp_path):
        from backend.services.drafting import draft_roster, RoleRequirement

        pool_dir = tmp_path / "pool"
        # a1 slightly ahead of a2
        agents = [
            _make_agent(agent_id="a1", display_name="A1", trust_score=90.0, total_sessions=10),
            _make_agent(agent_id="a2", display_name="A2", trust_score=80.0, total_sessions=10),
        ]
        _write_pool(pool_dir, agents)

        # Before decay: a1 wins
        result_before = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert result_before.summary["brass"] == ["a1"]

        # Heavy decay toward 50 — both move toward 50, gap narrows
        apply_season_decay(pool_dir, decay_rate=0.5, baseline=50.0)

        a1 = _read_agent(pool_dir, "a1")
        a2 = _read_agent(pool_dir, "a2")
        # a1: 90 + 0.5*(50-90) = 70, a2: 80 + 0.5*(50-80) = 65
        assert a1["trust_score"] < 90.0
        assert a2["trust_score"] < 80.0
        # a1 still ahead but gap narrowed
        assert a1["trust_score"] > a2["trust_score"]


# ========== Idempotency ==========


class TestIdempotency:
    def test_idempotent_repeated_session_id(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent(trust_score=50.0, total_sessions=5)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(final_score=80.0)
        roster = {"corps-A": ["agent-001"]}

        update_reputations(standings, pool_dir, roster, session_id="session-X")
        after_first = _read_agent(pool_dir, "agent-001")

        update_reputations(standings, pool_dir, roster, session_id="session-X")
        after_second = _read_agent(pool_dir, "agent-001")

        assert after_first["trust_score"] == after_second["trust_score"]
        assert after_first["total_sessions"] == after_second["total_sessions"]

    def test_empty_session_id_not_idempotent(self, tmp_path):
        """Empty string session_id means no idempotency — both calls apply."""
        pool_dir = tmp_path / "pool"
        agent = _make_agent(trust_score=50.0, total_sessions=5)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(final_score=80.0)
        roster = {"corps-A": ["agent-001"]}

        update_reputations(standings, pool_dir, roster, session_id="")
        after_first = _read_agent(pool_dir, "agent-001")

        update_reputations(standings, pool_dir, roster, session_id="")
        after_second = _read_agent(pool_dir, "agent-001")

        assert after_second["total_sessions"] == after_first["total_sessions"] + 1


# ========== Input Validation ==========


class TestInputValidation:
    def test_validate_score_none_raises(self):
        with pytest.raises(ValueError, match="Invalid"):
            _validate_score(None)

    def test_validate_score_nan_raises(self):
        with pytest.raises(ValueError, match="Invalid"):
            _validate_score(float("nan"))

    def test_validate_score_string_nan_raises(self):
        """String 'nan' converts to float nan — should still raise."""
        with pytest.raises(ValueError, match="Invalid"):
            _validate_score("nan")

    def test_validate_score_inf_raises(self):
        with pytest.raises(ValueError):
            _validate_score(float("inf"))

    def test_validate_score_negative_raises(self):
        with pytest.raises(ValueError, match="must be"):
            _validate_score(-1.0)


# ========== CLI Demo Tour ==========


def _run_cli(*args, env_extra=None):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "backend.cli.main", *args],
        capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30, env=env,
    )


class TestDemoTourCLI:
    def test_demo_tour_yes(self):
        result = _run_cli("demo", "tour", "--yes")
        assert result.returncode == 0, result.stderr
        assert "trust" in result.stdout.lower()
        assert "drafted" in result.stdout.lower()

    def test_demo_tour_plan(self):
        result = _run_cli("demo", "tour", "--plan")
        assert result.returncode == 0, result.stderr
        assert "plan" in result.stdout.lower() or "preview" in result.stdout.lower()
