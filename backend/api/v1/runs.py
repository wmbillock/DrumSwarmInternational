"""V1 API — Runs routes."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_root, _validate_id, _get_db_session
from backend.api.v1.schemas import StartRunRequest
from backend.services.yaml_util import safe_load_yaml_dict

router = APIRouter(prefix="/api/v1")


@router.get("/runs")
def v1_list_runs(corps_id: Optional[str] = None):
    """List all run manifests across seasons. Optionally filter by corps_id."""
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []
    if corps_id:
        _validate_id(corps_id, "corps_id")
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
            if corps_id and corps_dir.name != corps_id:
                continue
            for run_dir in corps_dir.iterdir():
                manifest_path = run_dir / "manifest.yaml"
                if not manifest_path.is_file():
                    continue
                try:
                    manifest = safe_load_yaml_dict(manifest_path.read_text())
                    if isinstance(manifest, dict) and "run_id" in manifest:
                        runs.append(manifest)
                except Exception:
                    continue
    runs.sort(key=lambda r: r.get("started_at", ""), reverse=True)
    return runs


@router.get("/runs/{run_id}")
def v1_get_run(run_id: str):
    """Get run manifest + output."""
    _validate_id(run_id, "run_id")
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        raise HTTPException(404, f"Run '{run_id}' not found")
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
                manifest = safe_load_yaml_dict(manifest_path.read_text())
                output = ""
                output_path = run_dir / "output.txt"
                if output_path.is_file():
                    output = output_path.read_text()[:10000]
                return {**manifest, "output": output}
    raise HTTPException(404, f"Run '{run_id}' not found")


@router.get("/runs/{run_id}/logs")
def v1_get_run_logs(run_id: str):
    """Get run output log."""
    _validate_id(run_id, "run_id")
    root = _get_root()
    seasons_dir = root / "seasons"
    if seasons_dir.exists():
        for season_dir in seasons_dir.iterdir():
            if not season_dir.is_dir():
                continue
            perf_root = season_dir / "performances"
            if not perf_root.exists():
                continue
            for corps_dir in perf_root.iterdir():
                if not corps_dir.is_dir():
                    continue
                output_path = corps_dir / run_id / "output.txt"
                if output_path.is_file():
                    return {"run_id": run_id, "log": output_path.read_text()[:50000]}
    raise HTTPException(404, f"Run '{run_id}' not found")


@router.post("/runs")
def v1_start_run(req: StartRunRequest):
    """Start a show run — creates manifest, executes stub, returns run_id."""
    root = _get_root()

    show_dir = root / "shows" / req.show_slug
    if not (show_dir / "status.yaml").exists():
        raise HTTPException(404, f"Show '{req.show_slug}' not found")
    from backend.services.show_persistence import check_field_ready
    if not check_field_ready(show_dir):
        raise HTTPException(400, f"Show '{req.show_slug}' is not approved")

    corps_dir = root / "corps" / req.corps_id
    if not (corps_dir / "corps.yaml").exists():
        try:
            from backend.models.corps import Corps
            db = _get_db_session()
            try:
                if not db.get(Corps, req.corps_id):
                    raise HTTPException(404, f"Corps '{req.corps_id}' not found")
            finally:
                db.close()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(404, f"Corps '{req.corps_id}' not found")

    season_dir = root / "seasons" / req.season_id
    if not (season_dir / "season.yaml").exists():
        raise HTTPException(404, f"Season '{req.season_id}' not found")

    from backend.services.yaml_util import atomic_write, safe_dump_yaml
    from backend.services.runtime_config import get_runtime_config

    config = get_runtime_config()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = f"{req.show_slug}-{req.corps_id}-{ts}"
    run_dir = season_dir / "performances" / req.corps_id / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "run_id": run_id,
        "show_slug": req.show_slug,
        "corps_id": req.corps_id,
        "season_id": req.season_id,
        "started_at": started_at,
        "status": "running",
        "config": config,
        "inputs": {"show_dir": str(show_dir), "corps_dir": str(corps_dir)},
        "outputs": [],
    }
    atomic_write(run_dir / "manifest.yaml", safe_dump_yaml(manifest))

    # Try to wire to task_manager for real agent execution
    try:
        from backend.api.app import get_task_manager
        tm = get_task_manager()
        if tm:
            task_desc = (
                f"Execute show run '{req.show_slug}' for corps '{req.corps_id}' "
                f"in season '{req.season_id}'. Run ID: {run_id}."
            )
            tm.start_agent(
                session_id=run_id,
                task_description=task_desc,
                corps_id=req.corps_id,
                context_snapshot={"manifest": manifest, "run_dir": str(run_dir)},
            )
            manifest["status"] = "running"
            atomic_write(run_dir / "manifest.yaml", safe_dump_yaml(manifest))
            return {"run_id": run_id, "status": "running"}
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to start agent for run %s: %s", run_id, e)

    # Stub execution fallback (no task manager available)
    (run_dir / "output.txt").write_text(f"Stub execution for show '{req.show_slug}'\n")

    manifest["status"] = "completed"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest["outputs"] = ["output.txt"]
    atomic_write(run_dir / "manifest.yaml", safe_dump_yaml(manifest))

    return {"run_id": run_id, "status": "completed"}
