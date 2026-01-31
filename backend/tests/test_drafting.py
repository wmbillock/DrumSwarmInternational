"""Tests for deterministic corps drafting."""

import pytest
import yaml

from backend.services.drafting import (
    DraftError,
    DraftResult,
    RoleRequirement,
    draft_roster,
    execute_draft,
    rank_candidates,
)


def _make_agent(agent_id, instrument, availability="active", trust=50.0, experience=1, specialties=None):
    return {
        "agent_id": agent_id,
        "display_name": agent_id,
        "primary_instrument": instrument,
        "availability": availability,
        "trust_score": trust,
        "experience_seasons": experience,
        "specialties": specialties or [],
    }


def _write_pool(pool_dir, agents):
    """Write agent YAML files and ledger to pool_dir."""
    agents_dir = pool_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    ledger_entries = []
    for a in agents:
        (agents_dir / f"{a['agent_id']}.yaml").write_text(yaml.dump(a, default_flow_style=False))
        ledger_entries.append({
            "agent_id": a["agent_id"],
            "display_name": a["display_name"],
            "primary_instrument": a["primary_instrument"],
            "availability": a["availability"],
        })
    (pool_dir / "ledger.yaml").write_text(yaml.dump({"agents": ledger_entries}, default_flow_style=False))


def _setup_corps(corps_dir, corps_id="test-corps"):
    """Create minimal corps directory for execute_draft."""
    corps_dir.mkdir(parents=True, exist_ok=True)
    data = {"corps_id": corps_id, "display_name": "Test", "philosophy": "test", "state": "commissioned"}
    (corps_dir / "corps.yaml").write_text(yaml.dump(data, default_flow_style=False))
    (corps_dir / "roster.yaml").write_text(yaml.dump({"corps_id": corps_id, "assignments": []}, default_flow_style=False))


class TestRosterCoversRequiredRoles:
    def test_all_roles_filled(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent("a1", "brass"),
            _make_agent("a2", "percussion"),
        ]
        _write_pool(pool_dir, agents)

        result = draft_roster("c1", [
            RoleRequirement("brass", 1),
            RoleRequirement("percussion", 1),
        ], pool_dir)

        assert result.summary["brass"] == ["a1"]
        assert result.summary["percussion"] == ["a2"]
        assert len(result.assignments) == 2


class TestSelectionRespectsAvailability:
    def test_inactive_agents_skipped(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent("a1", "brass", availability="assigned"),
            _make_agent("a2", "brass", availability="active"),
        ]
        _write_pool(pool_dir, agents)

        result = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert result.summary["brass"] == ["a2"]


class TestDeterministicTiebreaker:
    def test_same_input_same_output(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent("b", "brass", trust=80, experience=2),
            _make_agent("a", "brass", trust=80, experience=2),
        ]
        _write_pool(pool_dir, agents)

        r1 = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        r2 = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert r1.assignments == r2.assignments

    def test_trust_beats_experience(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent("a1", "brass", trust=90, experience=1),
            _make_agent("a2", "brass", trust=80, experience=5),
        ]
        _write_pool(pool_dir, agents)

        result = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert result.summary["brass"] == ["a1"]

    def test_experience_beats_lexicographic(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent("a1", "brass", trust=80, experience=1),
            _make_agent("a2", "brass", trust=80, experience=5),
        ]
        _write_pool(pool_dir, agents)

        result = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert result.summary["brass"] == ["a2"]

    def test_lexicographic_final_tiebreaker(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent("b", "brass", trust=80, experience=2),
            _make_agent("a", "brass", trust=80, experience=2),
        ]
        _write_pool(pool_dir, agents)

        result = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert result.summary["brass"] == ["a"]


class TestSpecialtyPreference:
    def test_matching_specialty_ranked_higher(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent("a1", "brass", trust=90, specialties=[]),
            _make_agent("a2", "brass", trust=80, specialties=["jazz"]),
        ]
        _write_pool(pool_dir, agents)

        result = draft_roster("c1", [
            RoleRequirement("brass", 1, preferred_specialties=["jazz"]),
        ], pool_dir)
        assert result.summary["brass"] == ["a2"]

    def test_no_preference_ignores_specialty(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent("a1", "brass", trust=90, specialties=[]),
            _make_agent("a2", "brass", trust=80, specialties=["jazz"]),
        ]
        _write_pool(pool_dir, agents)

        result = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert result.summary["brass"] == ["a1"]


class TestInsufficientPoolRaisesDraftError:
    def test_raises_with_unfilled(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agents = [_make_agent("a1", "brass")]
        _write_pool(pool_dir, agents)

        with pytest.raises(DraftError) as exc_info:
            draft_roster("c1", [RoleRequirement("brass", 3)], pool_dir)
        assert exc_info.value.unfilled == {"brass": 2}


class TestAgentNotDoubleDrafted:
    def test_agent_used_once(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent("a1", "brass", trust=90),
            _make_agent("a2", "brass", trust=80),
        ]
        _write_pool(pool_dir, agents)

        # Two separate brass roles each needing 1
        result = draft_roster("c1", [
            RoleRequirement("brass", 1),
            RoleRequirement("brass", 1),
        ], pool_dir)
        all_ids = [a["agent_id"] for a in result.assignments]
        assert len(all_ids) == len(set(all_ids))


class TestExecuteDraftMarksAssigned:
    def test_agent_yaml_updated(self, tmp_path):
        pool_dir = tmp_path / "pool"
        corps_dir = tmp_path / "corps" / "c1"
        agents = [_make_agent("a1", "brass")]
        _write_pool(pool_dir, agents)
        _setup_corps(corps_dir, "c1")

        execute_draft("c1", [RoleRequirement("brass", 1)], pool_dir, corps_dir)

        agent_data = yaml.safe_load((pool_dir / "agents" / "a1.yaml").read_text())
        assert agent_data["availability"] == "assigned"

    def test_ledger_updated(self, tmp_path):
        pool_dir = tmp_path / "pool"
        corps_dir = tmp_path / "corps" / "c1"
        agents = [_make_agent("a1", "brass"), _make_agent("a2", "percussion")]
        _write_pool(pool_dir, agents)
        _setup_corps(corps_dir, "c1")

        execute_draft("c1", [RoleRequirement("brass", 1)], pool_dir, corps_dir)

        ledger = yaml.safe_load((pool_dir / "ledger.yaml").read_text())
        for entry in ledger["agents"]:
            if entry["agent_id"] == "a1":
                assert entry["availability"] == "assigned"
            else:
                assert entry["availability"] == "active"


class TestExecuteDraftWritesRoster:
    def test_roster_written(self, tmp_path):
        pool_dir = tmp_path / "pool"
        corps_dir = tmp_path / "corps" / "c1"
        agents = [_make_agent("a1", "brass"), _make_agent("a2", "percussion")]
        _write_pool(pool_dir, agents)
        _setup_corps(corps_dir, "c1")

        execute_draft("c1", [
            RoleRequirement("brass", 1),
            RoleRequirement("percussion", 1),
        ], pool_dir, corps_dir)

        roster = yaml.safe_load((corps_dir / "roster.yaml").read_text())
        assert roster["corps_id"] == "c1"
        ids = {a["agent_id"] for a in roster["assignments"]}
        assert ids == {"a1", "a2"}
