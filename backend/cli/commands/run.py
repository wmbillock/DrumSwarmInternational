"""dci run show — execute a show run with manifest tracking."""

import os
import sys
import time
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


def _corps_exists(root: Path, corps_id: str) -> bool:
    """Check if corps exists on filesystem or in DB."""
    corps_dir = root / "corps" / corps_id
    if (corps_dir / "corps.yaml").exists():
        return True
    # Check DB as fallback for DB-only corps
    try:
        from backend.database import SessionLocal
        from backend.models.corps import Corps
        db = SessionLocal()
        try:
            corps = db.get(Corps, corps_id)
            return corps is not None
        finally:
            db.close()
    except Exception:
        return False


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

    if not _corps_exists(root, corps_id):
        print(f"Corps '{corps_id}' not found (filesystem or DB)", file=sys.stderr)
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
        "inputs": {"show_dir": str(show_dir), "corps_dir": str(root / "corps" / corps_id)},
        "outputs": [],
    }
    atomic_write(run_dir / "manifest.yaml", safe_dump_yaml(manifest))

    # --- Execute via API: trigger go_on_tour and poll ---

    poll_interval = 5
    timeout = config["timeout"]
    deadline = time.monotonic() + timeout

    try:
        from backend.cli.client import APIClient
        client = APIClient()

        # Check if API is reachable
        if not client.ping():
            raise ConnectionError("API server not reachable")

        # Trigger go_on_tour
        try:
            result = client.execute_command(corps_id, "go_on_tour")
            print(f"Corps {corps_id[:8]} sent on tour: {result.get('status', 'unknown')}")
        except Exception as e:
            print(f"Warning: go_on_tour failed ({e}), corps may already be on tour")

        # Poll for completion
        print(f"Polling corps status (timeout={timeout}s)...")
        final_status = "timeout"
        while time.monotonic() < deadline:
            time.sleep(poll_interval)
            try:
                status = client.corps_status(corps_id)
                current = status.get("status", "unknown")
                mode = status.get("mode", "")
                print(f"  status={current} mode={mode}")

                if current in ("completed", "disbanded"):
                    final_status = current
                    break
                if current == "ready_for_contest":
                    final_status = "ready_for_contest"
                    break
            except Exception:
                pass

        manifest["status"] = final_status
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()

    except (ConnectionError, ImportError):
        # No API server available — run in offline mode (manifest-only)
        print("API server not available — completing in offline mode")
        manifest["status"] = "completed"
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["outputs"] = ["manifest.yaml"]

    except Exception as e:
        manifest["status"] = "failed"
        manifest["error"] = str(e)
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        print(f"Run failed: {e}", file=sys.stderr)

    # Write final manifest
    atomic_write(run_dir / "manifest.yaml", safe_dump_yaml(manifest))

    print(f"Run {manifest['status']}: {run_id}")
    print(f"  manifest: {run_dir / 'manifest.yaml'}")
