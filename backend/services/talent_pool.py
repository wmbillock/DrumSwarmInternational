"""Talent pool YAML export/import layer.

Converts Performer DB rows into human-readable YAML snapshots.
The database remains the system of record; YAML files are generated views.
"""

from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from backend.models.performer import Performer, PerformerStatus
from backend.services.yaml_util import atomic_write, safe_dump_yaml

REQUIRED_FIELDS = ("agent_id", "display_name", "primary_instrument", "availability")


def _parse_specialties(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def performer_to_dict(performer: Performer) -> dict:
    """Convert a DB Performer to a talent-pool schema dict."""
    return {
        "agent_id": performer.id,
        "display_name": performer.name,
        "primary_instrument": performer.role_type,
        "availability": performer.status.value if isinstance(performer.status, PerformerStatus) else performer.status,
        "trust_score": performer.trust_score,
        "total_sessions": performer.total_sessions,
        "successful_sessions": performer.successful_sessions,
        "failed_sessions": performer.failed_sessions,
        "experience_seasons": performer.experience_seasons,
        "last_active_season": performer.experience_seasons,
        "specialties": _parse_specialties(performer.specialties),
    }


def validate_agent_dict(data: dict) -> None:
    """Raise ValueError if required schema fields are missing."""
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")


def export_talent_pool(db: Session, output_dir: Path) -> None:
    """Write ledger.yaml + agents/<id>.yaml for all non-retired performers."""
    output_dir = Path(output_dir)
    agents_dir = output_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    performers = db.query(Performer).filter(Performer.status != PerformerStatus.RETIRED).all()
    ledger_entries = []

    for p in performers:
        d = performer_to_dict(p)
        validate_agent_dict(d)
        atomic_write(agents_dir / f"{d['agent_id']}.yaml", safe_dump_yaml(d))
        ledger_entries.append({
            "agent_id": d["agent_id"],
            "display_name": d["display_name"],
            "primary_instrument": d["primary_instrument"],
            "availability": d["availability"],
        })

    atomic_write(output_dir / "ledger.yaml", safe_dump_yaml({"agents": ledger_entries}))


def load_talent_pool(pool_dir: Path) -> dict:
    """Read ledger.yaml, load each agent file, return structured dict."""
    pool_dir = Path(pool_dir)
    ledger = yaml.safe_load((pool_dir / "ledger.yaml").read_text())
    agents = []
    for entry in ledger.get("agents", []):
        agent_path = pool_dir / "agents" / f"{entry['agent_id']}.yaml"
        agents.append(yaml.safe_load(agent_path.read_text()))
    return {"agents": agents}


def list_by_instrument(pool_dir: Path, instrument: str) -> list[dict]:
    """Filter loaded pool by primary_instrument."""
    pool = load_talent_pool(pool_dir)
    return [a for a in pool["agents"] if a.get("primary_instrument") == instrument]
