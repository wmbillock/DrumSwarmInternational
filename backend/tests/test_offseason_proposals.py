"""Tests for offseason_proposals module."""

import pytest
from pathlib import Path

import yaml

from backend.services.corps_persistence import create_corps, load_corps
from backend.services.lifecycle_transitions import SeasonPhase, MutationBlockedError
from backend.services.offseason_proposals import (
    Proposal,
    apply_proposals,
    create_proposals_file,
    load_proposals,
)


def _make_corps(corps_dir: Path, corps_id: str, state: str = "active") -> Path:
    d = corps_dir / corps_id
    create_corps(d, {
        "corps_id": corps_id,
        "display_name": corps_id.title(),
        "philosophy": "test",
        "state": "commissioned",
    })
    if state != "commissioned":
        transitions = {
            "active": ["active"],
            "contending": ["active", "contending"],
            "stagnant": ["active", "stagnant"],
        }
        for s in transitions.get(state, []):
            from backend.services.corps_persistence import update_corps_state
            update_corps_state(d, s)
    return d


def _make_season(base_dir: Path, season_id: str) -> Path:
    season_dir = base_dir / "seasons" / season_id
    season_dir.mkdir(parents=True, exist_ok=True)
    return season_dir


def _make_pool(pool_dir: Path, agent_ids: list[str]) -> None:
    agents_dir = pool_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for aid in agent_ids:
        (agents_dir / f"{aid}.yaml").write_text(
            yaml.dump({"agent_id": aid, "display_name": aid}, default_flow_style=False)
        )


class TestCreateAndLoadProposals:
    def test_round_trip(self, tmp_path):
        _make_season(tmp_path, "s1")
        proposals = [
            Proposal("state_change", "alpha", "Promote alpha", {"new_state": "contending"}),
            Proposal("retirement", "beta", "Retire beta", {}),
        ]
        path = create_proposals_file(tmp_path, "s1", proposals)
        assert path.exists()
        assert path.name == "proposals.md"

        loaded = load_proposals(tmp_path, "s1")
        assert len(loaded) == 2
        assert loaded[0].proposal_type == "state_change"
        assert loaded[0].corps_id == "alpha"
        assert loaded[0].changes == {"new_state": "contending"}
        assert loaded[1].proposal_type == "retirement"
        assert loaded[1].corps_id == "beta"

    def test_file_is_markdown_with_yaml(self, tmp_path):
        _make_season(tmp_path, "s1")
        proposals = [Proposal("state_change", "alpha", "Test", {"new_state": "contending"})]
        path = create_proposals_file(tmp_path, "s1", proposals)
        text = path.read_text()
        assert "# Offseason Proposals" in text
        assert "```yaml" in text

    def test_blocked_during_show(self, tmp_path):
        _make_season(tmp_path, "s1")
        proposals = [Proposal("state_change", "alpha", "Test", {})]
        with pytest.raises(MutationBlockedError):
            create_proposals_file(tmp_path, "s1", proposals, phase=SeasonPhase.SHOW)


class TestApplyProposals:
    def test_requires_apply_flag(self, tmp_path):
        _make_season(tmp_path, "s1")
        proposals = [Proposal("state_change", "alpha", "Test", {"new_state": "contending"})]
        create_proposals_file(tmp_path, "s1", proposals)
        corps_dir = tmp_path / "corps"
        corps_dir.mkdir()
        with pytest.raises(ValueError, match="apply=True"):
            apply_proposals(tmp_path, "s1", corps_dir, tmp_path / "pool", apply=False)

    def test_applies_valid_state_change(self, tmp_path):
        corps_dir = tmp_path / "corps"
        _make_corps(corps_dir, "alpha", "active")
        _make_season(tmp_path, "s1")
        proposals = [Proposal("state_change", "alpha", "Promote", {"new_state": "contending"})]
        create_proposals_file(tmp_path, "s1", proposals)

        audit = apply_proposals(tmp_path, "s1", corps_dir, tmp_path / "pool", apply=True)
        assert len(audit) == 1
        assert audit[0]["result"] == "applied"
        assert load_corps(corps_dir / "alpha")["state"] == "contending"

    def test_invalid_transition_returns_error(self, tmp_path):
        corps_dir = tmp_path / "corps"
        _make_corps(corps_dir, "alpha", "commissioned")
        _make_season(tmp_path, "s1")
        # commissioned -> contending is not valid
        proposals = [Proposal("state_change", "alpha", "Bad", {"new_state": "contending"})]
        create_proposals_file(tmp_path, "s1", proposals)

        audit = apply_proposals(tmp_path, "s1", corps_dir, tmp_path / "pool", apply=True)
        assert audit[0]["result"] == "error"
        assert "Invalid transition" in audit[0]["error"]

    def test_nonexistent_corps_returns_error(self, tmp_path):
        corps_dir = tmp_path / "corps"
        corps_dir.mkdir()
        _make_season(tmp_path, "s1")
        proposals = [Proposal("state_change", "ghost", "Missing", {"new_state": "active"})]
        create_proposals_file(tmp_path, "s1", proposals)

        audit = apply_proposals(tmp_path, "s1", corps_dir, tmp_path / "pool", apply=True)
        assert audit[0]["result"] == "error"
        assert "not found" in audit[0]["error"]

    def test_partial_failure_others_still_applied(self, tmp_path):
        corps_dir = tmp_path / "corps"
        _make_corps(corps_dir, "alpha", "commissioned")  # bad transition target
        _make_corps(corps_dir, "beta", "active")  # valid
        _make_season(tmp_path, "s1")
        proposals = [
            Proposal("state_change", "alpha", "Bad", {"new_state": "contending"}),
            Proposal("state_change", "beta", "Good", {"new_state": "contending"}),
        ]
        create_proposals_file(tmp_path, "s1", proposals)

        audit = apply_proposals(tmp_path, "s1", corps_dir, tmp_path / "pool", apply=True)
        assert audit[0]["result"] == "error"
        assert audit[1]["result"] == "applied"
        assert load_corps(corps_dir / "beta")["state"] == "contending"
