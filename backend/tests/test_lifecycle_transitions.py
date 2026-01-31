"""Tests for lifecycle_transitions module."""

import pytest
from pathlib import Path

import yaml

from backend.services.corps_persistence import create_corps, load_corps, load_roster
from backend.services.lifecycle_transitions import (
    MutationBlockedError,
    SeasonPhase,
    guarded_assign_roster,
    guarded_update_corps_state,
    require_phase,
    retire_corps_and_release,
    update_corps_from_standings,
)
from backend.services.scoring_engine import CorpsResult, Standings


def _make_corps(corps_dir: Path, corps_id: str, state: str = "active") -> Path:
    d = corps_dir / corps_id
    create_corps(d, {
        "corps_id": corps_id,
        "display_name": corps_id.title(),
        "philosophy": "test",
        "state": "commissioned",
    })
    if state != "commissioned":
        # Walk through valid transitions to reach target state
        transitions = {
            "active": ["active"],
            "contending": ["active", "contending"],
            "stagnant": ["active", "stagnant"],
            "retired": ["active", "retired"],
        }
        for s in transitions.get(state, []):
            from backend.services.corps_persistence import update_corps_state
            update_corps_state(d, s)
    return d


def _make_pool(pool_dir: Path, agent_ids: list[str]) -> None:
    agents_dir = pool_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for aid in agent_ids:
        (agents_dir / f"{aid}.yaml").write_text(
            yaml.dump({"agent_id": aid, "display_name": aid}, default_flow_style=False)
        )


def _make_standings(corps_ranks: list[tuple[str, int]], season_id: str = "s1") -> Standings:
    results = []
    for corps_id, rank in corps_ranks:
        results.append(CorpsResult(
            corps_id=corps_id,
            caption_scores={},
            penalties_total=0.0,
            difficulty_coefficient=1.0,
            raw_score=100.0 - rank,
            final_score=100.0 - rank,
            rank=rank,
        ))
    results.sort(key=lambda r: r.rank)
    return Standings(season_id=season_id, results=results, generated_at="2025-01-01T00:00:00Z")


# --- Phase gating tests ---

class TestRequirePhase:
    def test_show_blocked_for_scoring_and_offseason(self):
        with pytest.raises(MutationBlockedError):
            require_phase(SeasonPhase.SHOW, SeasonPhase.SCORING, SeasonPhase.OFFSEASON)

    def test_scoring_allowed(self):
        require_phase(SeasonPhase.SCORING, SeasonPhase.SCORING, SeasonPhase.OFFSEASON)

    def test_offseason_allowed(self):
        require_phase(SeasonPhase.OFFSEASON, SeasonPhase.SCORING, SeasonPhase.OFFSEASON)


class TestGuardedUpdateCorpsState:
    def test_blocked_during_show(self, tmp_path):
        d = _make_corps(tmp_path, "alpha")
        with pytest.raises(MutationBlockedError):
            guarded_update_corps_state(d, "contending", SeasonPhase.SHOW)

    def test_allowed_during_scoring(self, tmp_path):
        d = _make_corps(tmp_path, "alpha")
        guarded_update_corps_state(d, "contending", SeasonPhase.SCORING)
        assert load_corps(d)["state"] == "contending"

    def test_allowed_during_offseason(self, tmp_path):
        d = _make_corps(tmp_path, "alpha")
        guarded_update_corps_state(d, "contending", SeasonPhase.OFFSEASON)
        assert load_corps(d)["state"] == "contending"


class TestGuardedAssignRoster:
    def test_blocked_during_show(self, tmp_path):
        d = _make_corps(tmp_path, "alpha")
        pool = tmp_path / "pool"
        _make_pool(pool, ["a1"])
        with pytest.raises(MutationBlockedError):
            guarded_assign_roster(d, [{"agent_id": "a1", "role": "brass"}], pool, SeasonPhase.SHOW)

    def test_allowed_during_offseason(self, tmp_path):
        d = _make_corps(tmp_path, "alpha")
        pool = tmp_path / "pool"
        _make_pool(pool, ["a1"])
        guarded_assign_roster(d, [{"agent_id": "a1", "role": "brass"}], pool, SeasonPhase.OFFSEASON)
        roster = load_roster(d)
        assert len(roster["assignments"]) == 1


# --- Scoring phase corps updates ---

class TestUpdateCorpsFromStandings:
    def test_top_ranked_active_becomes_contending(self, tmp_path):
        _make_corps(tmp_path, "alpha", "active")
        _make_corps(tmp_path, "beta", "active")
        _make_corps(tmp_path, "gamma", "active")
        _make_corps(tmp_path, "delta", "active")
        _make_corps(tmp_path, "epsilon", "active")

        standings = _make_standings([
            ("alpha", 1), ("beta", 2), ("gamma", 3),
            ("delta", 4), ("epsilon", 5),
        ])

        audit = update_corps_from_standings(tmp_path, standings, contending_threshold=3)
        changed_ids = {e["corps_id"] for e in audit}
        assert changed_ids == {"alpha", "beta", "gamma"}
        for e in audit:
            assert e["old_state"] == "active"
            assert e["new_state"] == "contending"

    def test_bottom_ranked_active_becomes_stagnant(self, tmp_path):
        _make_corps(tmp_path, "alpha", "active")
        _make_corps(tmp_path, "beta", "active")
        _make_corps(tmp_path, "gamma", "active")
        _make_corps(tmp_path, "delta", "active")
        _make_corps(tmp_path, "epsilon", "active")

        standings = _make_standings([
            ("alpha", 1), ("beta", 2), ("gamma", 3),
            ("delta", 4), ("epsilon", 5),
        ])

        audit = update_corps_from_standings(
            tmp_path, standings, contending_threshold=0, stagnant_threshold=2,
        )
        changed_ids = {e["corps_id"] for e in audit}
        assert changed_ids == {"delta", "epsilon"}
        for e in audit:
            assert e["new_state"] == "stagnant"

    def test_already_contending_not_changed(self, tmp_path):
        _make_corps(tmp_path, "alpha", "contending")
        _make_corps(tmp_path, "beta", "active")

        standings = _make_standings([("alpha", 1), ("beta", 2)])
        audit = update_corps_from_standings(tmp_path, standings, contending_threshold=3)
        # alpha is already contending so skipped; beta is active rank 2 -> contending
        assert len(audit) == 1
        assert audit[0]["corps_id"] == "beta"

    def test_commissioned_not_affected(self, tmp_path):
        _make_corps(tmp_path, "alpha", "commissioned")
        _make_corps(tmp_path, "beta", "active")

        standings = _make_standings([("alpha", 1), ("beta", 2)])
        audit = update_corps_from_standings(tmp_path, standings, contending_threshold=3)
        assert len(audit) == 1
        assert audit[0]["corps_id"] == "beta"

    def test_returns_audit_trail(self, tmp_path):
        _make_corps(tmp_path, "alpha", "active")
        standings = _make_standings([("alpha", 1)])
        audit = update_corps_from_standings(tmp_path, standings, contending_threshold=3)
        assert len(audit) == 1
        assert set(audit[0].keys()) == {"corps_id", "old_state", "new_state"}


# --- Retirement ---

class TestRetireCorpsAndRelease:
    def test_retires_and_releases_agents(self, tmp_path):
        d = _make_corps(tmp_path, "alpha", "active")
        pool = tmp_path / "pool"
        roster = {"assignments": [
            {"agent_id": "a1", "role": "brass"},
            {"agent_id": "a2", "role": "percussion"},
        ]}

        released = retire_corps_and_release(d, "alpha", roster, pool)
        assert set(released) == {"a1", "a2"}
        assert load_corps(d)["state"] == "retired"
        assert load_roster(d)["assignments"] == []

    def test_release_marker_written(self, tmp_path):
        d = _make_corps(tmp_path, "alpha", "active")
        pool = tmp_path / "pool"
        roster = {"assignments": [{"agent_id": "a1", "role": "brass"}]}

        retire_corps_and_release(d, "alpha", roster, pool)
        marker = yaml.safe_load((pool / "released_agents.yaml").read_text())
        assert marker["corps_id"] == "alpha"
        assert marker["released_agent_ids"] == ["a1"]
