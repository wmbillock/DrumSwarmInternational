"""dci pool — talent pool management on disk."""

import json
import os
import sys
from pathlib import Path

import yaml

from backend.cli.commands.doctor import _find_project_root


def _get_root() -> Path:
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    return Path(_find_project_root())


def cmd_pool_init(args) -> None:
    root = _get_root()
    pool_dir = root / "talent_pool"
    ledger = pool_dir / "ledger.yaml"
    agents_dir = pool_dir / "agents"

    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    if plan:
        print("Plan: initialize talent pool")
        print(f"  create {pool_dir}/")
        print(f"  create {ledger}")
        print(f"  create {agents_dir}/")
        return

    if not yes:
        print("Plan: initialize talent pool")
        print(f"  create {pool_dir}/")
        print(f"  create {ledger}")
        print(f"  create {agents_dir}/")
        print("\nPass --yes to apply, or --plan to preview.")
        return

    # Apply (idempotent)
    agents_dir.mkdir(parents=True, exist_ok=True)
    if not ledger.exists():
        ledger.write_text(yaml.safe_dump({"agents": []}))
        print(f"Created {ledger}")
    else:
        print(f"Already exists: {ledger}")
    print(f"Talent pool initialized at {pool_dir}")


def cmd_pool_list(args) -> None:
    root = _get_root()
    pool_dir = root / "talent_pool"
    ledger = pool_dir / "ledger.yaml"

    if not ledger.exists():
        print("Talent pool not initialized. Run: dci pool init --yes", file=sys.stderr)
        sys.exit(1)

    from backend.services.yaml_util import safe_load_yaml_dict
    data = safe_load_yaml_dict(ledger.read_text(), {"agents": []})
    agents = data.get("agents", [])

    instrument = getattr(args, "instrument", None)
    if instrument:
        agents = [a for a in agents if a.get("primary_instrument") == instrument]

    json_output = getattr(args, "json_output", False)
    if json_output:
        print(json.dumps(agents, indent=2))
    else:
        if not agents:
            print("No agents in talent pool.")
            return
        print(f"{'ID':<20} {'Name':<20} {'Instrument':<20} {'Status':<10}")
        print("-" * 70)
        for a in agents:
            print(f"{a.get('agent_id', ''):<20} {a.get('display_name', ''):<20} "
                  f"{a.get('primary_instrument', ''):<20} {a.get('availability', ''):<10}")
