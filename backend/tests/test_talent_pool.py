"""Tests for the talent pool YAML export/import layer."""

import yaml

from backend.models.performer import Performer, PerformerStatus
from backend.services.talent_pool import (
    export_talent_pool,
    list_by_instrument,
    load_talent_pool,
    performer_to_dict,
    validate_agent_dict,
)


def _make_performer(**overrides) -> Performer:
    defaults = dict(
        id="agent-001",
        name="Alice",
        role_type="bass",
        trust_score=72.5,
        total_sessions=10,
        successful_sessions=8,
        failed_sessions=2,
        status=PerformerStatus.ACTIVE,
        experience_seasons=3,
        specialties="jazz,funk",
    )
    defaults.update(overrides)
    return Performer(**defaults)


# --- unit tests (no DB) ---


def test_export_performer_to_dict():
    p = _make_performer()
    d = performer_to_dict(p)
    assert d["agent_id"] == "agent-001"
    assert d["display_name"] == "Alice"
    assert d["primary_instrument"] == "bass"
    assert d["availability"] == "active"
    assert d["trust_score"] == 72.5
    assert d["total_sessions"] == 10
    assert d["successful_sessions"] == 8
    assert d["failed_sessions"] == 2
    assert d["experience_seasons"] == 3
    assert d["last_active_season"] == 3
    assert d["specialties"] == ["jazz", "funk"]


def test_export_dict_validates_required_fields():
    valid = performer_to_dict(_make_performer())
    # removing a required field should raise
    for key in ("agent_id", "display_name", "primary_instrument", "availability"):
        broken = {k: v for k, v in valid.items() if k != key}
        try:
            validate_agent_dict(broken)
            assert False, f"Expected ValueError for missing {key}"
        except ValueError:
            pass

    # valid dict should not raise
    validate_agent_dict(valid)


def test_round_trip_single_performer():
    p = _make_performer()
    d = performer_to_dict(p)
    yaml_str = yaml.dump(d, default_flow_style=False)
    loaded = yaml.safe_load(yaml_str)
    assert loaded == d


def test_export_ledger():
    performers = [
        _make_performer(id="a1", name="Alice", role_type="bass"),
        _make_performer(id="a2", name="Bob", role_type="drums"),
    ]
    dicts = [performer_to_dict(p) for p in performers]

    # Build ledger the same way the module does
    ledger = [
        {
            "agent_id": d["agent_id"],
            "display_name": d["display_name"],
            "primary_instrument": d["primary_instrument"],
            "availability": d["availability"],
        }
        for d in dicts
    ]
    assert len(ledger) == 2
    assert ledger[0]["agent_id"] == "a1"
    assert ledger[1]["primary_instrument"] == "drums"


def test_list_by_instrument(tmp_path):
    performers = [
        _make_performer(id="a1", name="Alice", role_type="bass"),
        _make_performer(id="a2", name="Bob", role_type="drums"),
        _make_performer(id="a3", name="Carol", role_type="bass"),
    ]
    # Write pool manually
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    ledger_entries = []
    for p in performers:
        d = performer_to_dict(p)
        (agents_dir / f"{d['agent_id']}.yaml").write_text(yaml.dump(d))
        ledger_entries.append(
            {
                "agent_id": d["agent_id"],
                "display_name": d["display_name"],
                "primary_instrument": d["primary_instrument"],
                "availability": d["availability"],
            }
        )
    (tmp_path / "ledger.yaml").write_text(yaml.dump({"agents": ledger_entries}))

    result = list_by_instrument(tmp_path, "bass")
    assert len(result) == 2
    assert all(r["primary_instrument"] == "bass" for r in result)


def test_write_and_read_talent_pool(db, tmp_path):
    # Insert real rows via the db fixture
    for pid, name, role in [("x1", "Xena", "guitar"), ("x2", "Yuri", "keys")]:
        db.add(
            Performer(
                id=pid,
                name=name,
                role_type=role,
                status=PerformerStatus.ACTIVE,
                trust_score=50.0,
                specialties="",
            )
        )
    # Also add a retired performer — should be excluded
    db.add(
        Performer(
            id="x3",
            name="Zara",
            role_type="vocals",
            status=PerformerStatus.RETIRED,
            trust_score=10.0,
        )
    )
    db.commit()

    export_talent_pool(db, tmp_path)
    pool = load_talent_pool(tmp_path)

    assert len(pool["agents"]) == 2
    ids = {a["agent_id"] for a in pool["agents"]}
    assert ids == {"x1", "x2"}
    # Verify individual agent files round-tripped
    for entry in pool["agents"]:
        assert "display_name" in entry
        assert "primary_instrument" in entry
