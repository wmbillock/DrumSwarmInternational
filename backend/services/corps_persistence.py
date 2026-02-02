"""Corps YAML persistence layer.

Manages corps identity and roster as YAML files on disk.
Directory structure: corps/<corps_id>/corps.yaml + roster.yaml
"""

from pathlib import Path

from backend.services.yaml_util import atomic_write, safe_dump_yaml, safe_load_yaml_dict

REQUIRED_CORPS_FIELDS = ("corps_id", "display_name", "philosophy", "state")

VALID_STATES = {"commissioned", "active", "contending", "stagnant", "rebuilt", "retired"}

VALID_TRANSITIONS: dict[str, set[str]] = {
    "commissioned": {"active"},
    "active": {"contending", "stagnant", "retired"},
    "contending": {"active", "stagnant", "retired"},
    "stagnant": {"rebuilt", "retired"},
    "rebuilt": {"active"},
    "retired": set(),
}


def validate_corps_dict(data: dict) -> None:
    """Raise ValueError if required fields are missing or state is invalid."""
    missing = [f for f in REQUIRED_CORPS_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if data["state"] not in VALID_STATES:
        raise ValueError(f"Invalid state '{data['state']}'. Must be one of: {', '.join(sorted(VALID_STATES))}")


def validate_state_transition(current: str, target: str) -> None:
    """Raise ValueError if the state transition is not allowed."""
    if current not in VALID_TRANSITIONS:
        raise ValueError(f"Unknown current state '{current}'")
    if target not in VALID_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid transition: {current} → {target}")


def validate_roster(roster: dict, pool_dir: Path) -> None:
    """Validate roster assignments against the talent pool directory."""
    pool_dir = Path(pool_dir)
    assignments = roster.get("assignments", [])
    for entry in assignments:
        if "agent_id" not in entry:
            raise ValueError("Roster assignment missing agent_id")
        if "role" not in entry:
            raise ValueError(f"Roster assignment for {entry['agent_id']} missing role")
        agent_path = pool_dir / "agents" / f"{entry['agent_id']}.yaml"
        if not agent_path.exists():
            raise ValueError(f"Agent '{entry['agent_id']}' not found in talent pool")


def create_corps(corps_dir: Path, data: dict) -> None:
    """Create a new corps directory with corps.yaml and empty roster.yaml."""
    corps_dir = Path(corps_dir)
    validate_corps_dict(data)
    corps_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(corps_dir / "corps.yaml", safe_dump_yaml(data))
    empty_roster = {"corps_id": data["corps_id"], "assignments": []}
    atomic_write(corps_dir / "roster.yaml", safe_dump_yaml(empty_roster))


def load_corps(corps_dir: Path) -> dict:
    """Read and return the corps dict from corps.yaml."""
    corps_dir = Path(corps_dir)
    return safe_load_yaml_dict((corps_dir / "corps.yaml").read_text())


def load_roster(corps_dir: Path) -> dict:
    """Read and return the roster dict from roster.yaml."""
    corps_dir = Path(corps_dir)
    return safe_load_yaml_dict((corps_dir / "roster.yaml").read_text())


def update_corps_state(corps_dir: Path, new_state: str) -> None:
    """Validate transition and persist new state."""
    corps_dir = Path(corps_dir)
    data = load_corps(corps_dir)
    validate_state_transition(data["state"], new_state)
    data["state"] = new_state
    atomic_write(corps_dir / "corps.yaml", safe_dump_yaml(data))


def assign_roster(corps_dir: Path, assignments: list[dict], pool_dir: Path) -> None:
    """Validate and write roster assignments."""
    corps_dir = Path(corps_dir)
    data = load_corps(corps_dir)
    roster = {"corps_id": data["corps_id"], "assignments": assignments}
    validate_roster(roster, pool_dir)
    atomic_write(corps_dir / "roster.yaml", safe_dump_yaml(roster))


def retire_corps(corps_dir: Path) -> None:
    """Set state to retired and clear the roster."""
    corps_dir = Path(corps_dir)
    data = load_corps(corps_dir)
    validate_state_transition(data["state"], "retired")
    data["state"] = "retired"
    atomic_write(corps_dir / "corps.yaml", safe_dump_yaml(data))
    empty_roster = {"corps_id": data["corps_id"], "assignments": []}
    atomic_write(corps_dir / "roster.yaml", safe_dump_yaml(empty_roster))
