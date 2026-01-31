"""Tests for corps YAML persistence layer."""

import yaml
import pytest

from backend.services.corps_persistence import (
    assign_roster,
    create_corps,
    load_corps,
    load_roster,
    retire_corps,
    update_corps_state,
    validate_corps_dict,
    validate_roster,
    validate_state_transition,
)


def _sample_corps(**overrides) -> dict:
    defaults = {
        "corps_id": "blue-devils-2025",
        "display_name": "Blue Devils 2025",
        "philosophy": "Innovation through excellence",
        "state": "commissioned",
    }
    defaults.update(overrides)
    return defaults


def _make_pool_dir(tmp_path, agents: list[str]):
    """Create a fake talent pool directory with agent YAML files."""
    pool = tmp_path / "pool"
    agents_dir = pool / "agents"
    agents_dir.mkdir(parents=True)
    for aid in agents:
        (agents_dir / f"{aid}.yaml").write_text(
            yaml.dump({"agent_id": aid, "display_name": aid, "primary_instrument": "any", "availability": "active"})
        )
    return pool


# --- Schema validation ---


def test_valid_corps_dict_passes_validation():
    validate_corps_dict(_sample_corps())


def test_missing_required_field_raises():
    for field in ("corps_id", "display_name", "philosophy", "state"):
        data = _sample_corps()
        del data[field]
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_corps_dict(data)


def test_invalid_state_raises():
    with pytest.raises(ValueError, match="Invalid state"):
        validate_corps_dict(_sample_corps(state="disbanded"))


# --- Lifecycle state transitions ---


def test_valid_transitions_allowed():
    transitions = [
        ("commissioned", "active"),
        ("active", "contending"),
        ("active", "stagnant"),
        ("active", "retired"),
        ("contending", "active"),
        ("contending", "stagnant"),
        ("contending", "retired"),
        ("stagnant", "rebuilt"),
        ("stagnant", "retired"),
        ("rebuilt", "active"),
    ]
    for current, target in transitions:
        validate_state_transition(current, target)  # should not raise


def test_invalid_transition_raises():
    invalid = [
        ("retired", "active"),
        ("commissioned", "contending"),
        ("rebuilt", "retired"),
        ("stagnant", "active"),
    ]
    for current, target in invalid:
        with pytest.raises(ValueError, match="Invalid transition"):
            validate_state_transition(current, target)


# --- Roster validation ---


def test_valid_roster_passes(tmp_path):
    pool = _make_pool_dir(tmp_path, ["abc-123", "def-456"])
    roster = {
        "corps_id": "test",
        "assignments": [
            {"agent_id": "abc-123", "role": "brass_caption_head"},
            {"agent_id": "def-456", "role": "percussion_tech"},
        ],
    }
    validate_roster(roster, pool)


def test_roster_references_nonexistent_agent_raises(tmp_path):
    pool = _make_pool_dir(tmp_path, ["abc-123"])
    roster = {
        "corps_id": "test",
        "assignments": [{"agent_id": "ghost-999", "role": "lead"}],
    }
    with pytest.raises(ValueError, match="not found in talent pool"):
        validate_roster(roster, pool)


def test_roster_missing_required_role_raises(tmp_path):
    pool = _make_pool_dir(tmp_path, ["abc-123"])
    roster = {
        "corps_id": "test",
        "assignments": [{"agent_id": "abc-123"}],
    }
    with pytest.raises(ValueError, match="missing role"):
        validate_roster(roster, pool)


# --- Create & persist ---


def test_create_corps_writes_yaml(tmp_path):
    corps_dir = tmp_path / "blue-devils-2025"
    create_corps(corps_dir, _sample_corps())
    assert (corps_dir / "corps.yaml").exists()
    assert (corps_dir / "roster.yaml").exists()


def test_round_trip_corps(tmp_path):
    corps_dir = tmp_path / "blue-devils-2025"
    data = _sample_corps(history=[{"season_id": "s1", "placement": 1, "notes": "champion"}])
    create_corps(corps_dir, data)
    loaded = load_corps(corps_dir)
    assert loaded == data


def test_update_corps_state_persists(tmp_path):
    corps_dir = tmp_path / "test-corps"
    create_corps(corps_dir, _sample_corps())
    update_corps_state(corps_dir, "active")
    loaded = load_corps(corps_dir)
    assert loaded["state"] == "active"


# --- Roster assignment from talent pool ---


def test_assign_roster_from_pool(tmp_path):
    pool = _make_pool_dir(tmp_path, ["abc-123", "def-456"])
    corps_dir = tmp_path / "test-corps"
    create_corps(corps_dir, _sample_corps())

    assignments = [
        {"agent_id": "abc-123", "role": "brass_caption_head"},
        {"agent_id": "def-456", "role": "percussion_tech"},
    ]
    assign_roster(corps_dir, assignments, pool)

    roster = load_roster(corps_dir)
    assert len(roster["assignments"]) == 2
    assert roster["assignments"][0]["agent_id"] == "abc-123"


def test_retirement_marks_agents_available(tmp_path):
    pool = _make_pool_dir(tmp_path, ["abc-123"])
    corps_dir = tmp_path / "test-corps"
    create_corps(corps_dir, _sample_corps(state="active"))

    assign_roster(corps_dir, [{"agent_id": "abc-123", "role": "lead"}], pool)
    assert len(load_roster(corps_dir)["assignments"]) == 1

    retire_corps(corps_dir)
    assert load_corps(corps_dir)["state"] == "retired"
    assert load_roster(corps_dir)["assignments"] == []
