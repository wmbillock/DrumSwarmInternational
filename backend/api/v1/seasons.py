"""V1 API — Seasons routes."""

import yaml
from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_root, _validate_id, _get_db_session, _slugify
from backend.api.v1.schemas import CreateSeasonRequest, UpdateSeasonRequest, RegisterCorpsRequest

router = APIRouter(prefix="/api/v1")


@router.get("/seasons")
def v1_list_seasons():
    """List all available seasons."""
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []
    results = []
    for season_dir in sorted(seasons_dir.iterdir()):
        if not season_dir.is_dir():
            continue
        season_yaml = season_dir / "season.yaml"
        if not season_yaml.is_file():
            continue
        data = yaml.safe_load(season_yaml.read_text())
        season_id = data.get("season_id", season_dir.name)
        meta = data.get("metadata", {})
        results.append({
            "season_id": season_id,
            "name": meta.get("name", season_id),
            "dir_name": season_dir.name,
            "metadata": meta,
        })
    return results


@router.post("/seasons")
def v1_create_season(req: CreateSeasonRequest):
    """Create a new season workspace. Provide name (auto-generates ID) or season_id directly."""
    if not req.season_id and not req.name:
        raise HTTPException(400, "Provide either 'name' or 'season_id'")
    season_id = req.season_id or _slugify(req.name)
    _validate_id(season_id, "season_id")
    metadata = dict(req.metadata or {})
    if req.name:
        metadata["name"] = req.name
    root = _get_root()
    from backend.services.season_persistence import create_season
    try:
        season_dir = create_season(root, season_id, metadata)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {
        "season_id": season_id,
        "name": req.name or season_id,
        "dir_name": season_dir.name,
        "metadata": metadata,
    }


@router.get("/seasons/{season_id}")
def v1_get_season(season_id: str):
    """Get season details including registered corps."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.season_persistence import load_season
    data = load_season(season_dir)
    meta = data.get("metadata", {})
    data["name"] = meta.get("name", season_id)
    return data


@router.put("/seasons/{season_id}")
def v1_update_season(season_id: str, req: UpdateSeasonRequest):
    """Update season metadata."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    season_yaml = season_dir / "season.yaml"
    if not season_yaml.is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    data = yaml.safe_load(season_yaml.read_text())
    if req.metadata is not None:
        data["metadata"] = req.metadata
    from backend.services.yaml_util import atomic_write, safe_dump_yaml
    atomic_write(season_yaml, safe_dump_yaml(data))
    return data


@router.post("/seasons/{season_id}/corps")
def v1_register_season_corps(season_id: str, req: RegisterCorpsRequest):
    """Register a corps for this season (creates performance directory)."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    corps_dir = root / "corps" / req.corps_id
    if (corps_dir / "corps.yaml").exists():
        from backend.services.season_persistence import register_corps
        register_corps(season_dir, req.corps_id, root / "corps")
    else:
        try:
            from backend.models.corps import Corps
            db = _get_db_session()
            try:
                corps_obj = db.get(Corps, req.corps_id)
                if not corps_obj:
                    raise HTTPException(404, f"Corps '{req.corps_id}' not found")
                if getattr(corps_obj, 'corps_type', None) == 'system':
                    raise HTTPException(400, f"System corps cannot be registered for seasons")
                perf_dir = season_dir / "performances" / req.corps_id
                perf_dir.mkdir(parents=True, exist_ok=True)
            finally:
                db.close()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(404, f"Corps '{req.corps_id}' not found")

    return {"status": "registered", "season_id": season_id, "corps_id": req.corps_id}
