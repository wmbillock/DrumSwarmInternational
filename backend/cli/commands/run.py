"""dci run show — execute a show run with manifest tracking."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from backend.cli.commands.doctor import _find_project_root
from backend.services.runtime_config import get_runtime_config
from backend.services.yaml_util import atomic_write, safe_dump_yaml


def _get_root() -> Path:
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    return Path(_find_project_root())


def cmd_run_show(args) -> None:
    root = _get_root()
    slug = args.show_slug
    corps_id = args.corps_id
    season_id = args.season_id
    plan = getattr(args, "plan", False)
    yes = getattr(args, "yes", False)

    # Resolve effective config: CLI > env > default
    cli_timeout = getattr(args, "timeout_seconds", None)
    cli_iters = getattr(args, "max_iterations", None)
    config = get_runtime_config(cli_timeout=cli_timeout, cli_max_iterations=cli_iters)

    # --- Gates ---

    show_dir = root / "shows" / slug
    if not (show_dir / "status.yaml").exists():
        print(f"Show '{slug}' not found at {show_dir}", file=sys.stderr)
        sys.exit(1)

    from backend.services.show_persistence import check_field_ready
    if not check_field_ready(show_dir):
        print(f"Show '{slug}' must be approved before running.", file=sys.stderr)
        sys.exit(1)

    corps_dir = root / "corps" / corps_id
    if not (corps_dir / "corps.yaml").exists():
        print(f"Corps '{corps_id}' not found at {corps_dir}", file=sys.stderr)
        sys.exit(1)

    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").exists():
        print(f"Season '{season_id}' not found at {season_dir}", file=sys.stderr)
        sys.exit(1)

    # --- Run ID ---

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = f"{slug}-{corps_id}-{ts}"
    perf_dir = season_dir / "performances" / corps_id
    run_dir = perf_dir / run_id

    # --- Plan / hint ---

    if plan or not yes:
        print(f"Plan: run show '{slug}' with corps '{corps_id}' in season '{season_id}'")
        print(f"  run_id: {run_id}")
        print(f"  config: timeout={config['timeout']}s, max_iterations={config['max_iterations']}")
        print(f"  create {run_dir}/manifest.yaml")
        print(f"  create {run_dir}/output.txt")
        if not plan:
            print("\nPass --yes to apply, or --plan to preview.")
        return

    # --- Apply ---

    run_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "run_id": run_id,
        "show_slug": slug,
        "corps_id": corps_id,
        "season_id": season_id,
        "started_at": started_at,
        "status": "running",
        "config": config,
        "inputs": {"show_dir": str(show_dir), "corps_dir": str(corps_dir)},
        "outputs": [],
    }
    atomic_write(run_dir / "manifest.yaml", safe_dump_yaml(manifest))

    # Execution stub — placeholder artifact
    (run_dir / "output.txt").write_text(f"Stub execution for show '{slug}'\n")

    manifest["status"] = "completed"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest["outputs"] = ["output.txt"]
    atomic_write(run_dir / "manifest.yaml", safe_dump_yaml(manifest))

    print(f"Run completed: {run_id}")
    print(f"  manifest: {run_dir / 'manifest.yaml'}")
