"""Workspace API routes — thin filesystem readers for the UI.

All endpoints read YAML/markdown from disk and return JSON.
They use the same persistence modules as the CLI.
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.services.yaml_util import safe_load_yaml_dict

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_root() -> Path:
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    from backend.cli.commands.doctor import _find_project_root
    return Path(_find_project_root())


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

@router.get("/api/runs")
def api_list_runs():
    """Scan seasons/*/performances/*/*/manifest.yaml and return run manifests."""
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []

    runs = []
    for season_dir in seasons_dir.iterdir():
        if not season_dir.is_dir():
            continue
        perf_root = season_dir / "performances"
        if not perf_root.exists():
            continue
        for corps_dir in perf_root.iterdir():
            if not corps_dir.is_dir():
                continue
            for run_dir in corps_dir.iterdir():
                manifest_path = run_dir / "manifest.yaml"
                if not manifest_path.is_file():
                    continue
                try:
                    manifest = safe_load_yaml_dict(manifest_path.read_text(encoding="utf-8"))
                    if isinstance(manifest, dict) and "run_id" in manifest:
                        runs.append(manifest)
                except Exception as e:
                    logger.warning("Failed to read manifest %s: %s", manifest_path, e)
                    continue

    # Sort by started_at descending (most recent first)
    runs.sort(key=lambda r: r.get("started_at", ""), reverse=True)
    return runs


@router.get("/api/runs/{run_id}")
def api_get_run_detail(run_id: str):
    """Find a specific run by run_id across all seasons, return manifest + output."""
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    for season_dir in seasons_dir.iterdir():
        if not season_dir.is_dir():
            continue
        perf_root = season_dir / "performances"
        if not perf_root.exists():
            continue
        for corps_dir in perf_root.iterdir():
            if not corps_dir.is_dir():
                continue
            run_dir = corps_dir / run_id
            manifest_path = run_dir / "manifest.yaml"
            if manifest_path.is_file():
                try:
                    manifest = safe_load_yaml_dict(manifest_path.read_text(encoding="utf-8"))
                except Exception:
                    raise HTTPException(status_code=500, detail="Failed to read manifest")

                # Read output if available
                output = ""
                output_path = run_dir / "output.txt"
                if output_path.is_file():
                    try:
                        output = output_path.read_text(encoding="utf-8")
                    except Exception:
                        output = "(failed to read output)"

                return {**manifest, "output": output}

    raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


# ---------------------------------------------------------------------------
# Corps workspace
# ---------------------------------------------------------------------------

@router.get("/api/corps-workspace")
def api_list_corps_workspaces():
    """List all corps from filesystem (corps/<id>/corps.yaml)."""
    root = _get_root()
    corps_base = root / "corps"
    if not corps_base.exists():
        return []

    result = []
    for corps_dir in sorted(corps_base.iterdir()):
        corps_path = corps_dir / "corps.yaml"
        if not corps_path.is_file():
            continue
        try:
            data = safe_load_yaml_dict(corps_path.read_text(encoding="utf-8"))
            roster_path = corps_dir / "roster.yaml"
            roster_size = 0
            if roster_path.is_file():
                roster = safe_load_yaml_dict(roster_path.read_text(encoding="utf-8"))
                roster_size = len(roster.get("assignments", []))
            result.append({
                "corps_id": data.get("corps_id", corps_dir.name),
                "display_name": data.get("display_name", corps_dir.name),
                "philosophy": data.get("philosophy", ""),
                "state": data.get("state", "unknown"),
                "history": data.get("history", []),
                "roster_size": roster_size,
            })
        except Exception as e:
            logger.warning("Failed to read corps workspace %s: %s", corps_path, e)
            continue
    return result


@router.get("/api/corps-workspace/{corps_id}/history")
def api_get_corps_history(corps_id: str):
    """Get competition history from corps.yaml."""
    root = _get_root()
    corps_path = root / "corps" / corps_id / "corps.yaml"
    if not corps_path.is_file():
        raise HTTPException(status_code=404, detail=f"Corps '{corps_id}' not found")

    try:
        data = safe_load_yaml_dict(corps_path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read corps.yaml")

    return data.get("history", [])
