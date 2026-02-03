"""V1 API — Seasons routes."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_root, _validate_id, _get_db_session, _slugify
from backend.api.v1.schemas import (
    CreateSeasonRequest,
    UpdateSeasonRequest,
    RegisterCorpsRequest,
    SeasonShowRequest,
    SeasonAssignRequest,
    SeasonConfigRequest,
    FinalsDeclareWinnerRequest,
)
from backend.services.yaml_util import safe_load_yaml_dict

router = APIRouter(prefix="/api/v1")


def _build_finals_payload(season_dir: Path) -> dict:
    from backend.services.season_persistence import load_season

    data = load_season(season_dir)
    season_id = data.get("season_id", season_dir.name)
    required_scores = (data.get("config") or {}).get("required_scores", 1)
    corps_ids = data.get("registered_corps", [])
    divisions = data.get("divisions", {})

    qualification: dict[str, bool] = {}
    score_counts: dict[str, int] = {}
    scores_by_corps: dict[str, float] = {}

    for cid in corps_ids:
        perf_dir = season_dir / "performances" / cid
        critique_count = 0
        if perf_dir.exists():
            critique_count = len(list(perf_dir.glob("critique_round_*.md")))
        score_counts[cid] = critique_count
        qualification[cid] = critique_count >= required_scores
        score_value = 0.0
        scores_path = perf_dir / "scores.yaml"
        if scores_path.is_file():
            try:
                sc = safe_load_yaml_dict(scores_path.read_text())
                if isinstance(sc, dict):
                    score_value = float(sc.get("final_score") or sc.get("raw_total") or 0.0)
            except Exception:
                score_value = 0.0
        scores_by_corps[cid] = score_value

    def rank_rows(ids: list[str]) -> list[dict]:
        ordered = sorted(ids, key=lambda cid: scores_by_corps.get(cid, 0.0), reverse=True)
        return [
            {
                "rank": idx + 1,
                "corps_id": cid,
                "score": scores_by_corps.get(cid, 0.0),
                "qualified": qualification.get(cid, False),
                "scores_count": score_counts.get(cid, 0),
            }
            for idx, cid in enumerate(ordered)
        ]

    overall = rank_rows(corps_ids)
    division_rows = []
    for show_slug, corps_list in (divisions or {}).items():
        division_rows.append({
            "show_slug": show_slug,
            "standings": rank_rows(list(corps_list or [])),
        })

    return {
        "season_id": season_id,
        "status": data.get("metadata", {}).get("status", "planning"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "required_scores": required_scores,
        "qualification": qualification,
        "score_counts": score_counts,
        "overall": overall,
        "divisions": division_rows,
    }


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
        data = safe_load_yaml_dict(season_yaml.read_text())
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
    data = safe_load_yaml_dict(season_yaml.read_text())
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


@router.delete("/seasons/{season_id}")
def v1_delete_season(season_id: str):
    """Delete a season workspace."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not season_dir.exists():
        raise HTTPException(404, f"Season '{season_id}' not found")
    import shutil
    shutil.rmtree(season_dir)
    return {"status": "deleted", "season_id": season_id}


@router.post("/seasons/{season_id}/shows")
def v1_add_season_show(season_id: str, req: SeasonShowRequest):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.season_persistence import add_show
    data = add_show(season_dir, req.show_slug)
    return data


@router.delete("/seasons/{season_id}/shows/{show_slug}")
def v1_remove_season_show(season_id: str, show_slug: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.season_persistence import remove_show
    data = remove_show(season_dir, show_slug)
    return data


@router.post("/seasons/{season_id}/assign")
def v1_assign_season(season_id: str, req: SeasonAssignRequest):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.season_persistence import assign_corps
    data = assign_corps(season_dir, req.show_slug, req.corps_ids)
    return data


@router.put("/seasons/{season_id}/config")
def v1_update_season_config(season_id: str, req: SeasonConfigRequest):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.season_persistence import update_config
    data = update_config(season_dir, req.dict(exclude_none=True))
    return data


@router.post("/seasons/{season_id}/lock")
def v1_lock_season(season_id: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.season_persistence import lock_season
    data = lock_season(season_dir)
    return data


@router.post("/seasons/{season_id}/start-tour")
def v1_start_season_tour(season_id: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.season_persistence import start_tour
    data = start_tour(season_dir)
    return data


@router.get("/seasons/{season_id}/schedule")
def v1_get_season_schedule(season_id: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.season_persistence import load_season
    data = load_season(season_dir)
    return data.get("schedule", [])


@router.get("/seasons/{season_id}/standings")
def v1_get_season_standings(season_id: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    standings_yaml = season_dir / "standings.yaml"
    if not standings_yaml.is_file():
        return []
    return safe_load_yaml_dict(standings_yaml.read_text())


@router.post("/seasons/{season_id}/enter-finals")
def v1_enter_finals(season_id: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    from backend.services.season_persistence import load_season, save_season
    data = load_season(season_dir)
    data.setdefault("metadata", {})
    data["metadata"]["status"] = "finals"
    save_season(season_dir, data)

    finals = _build_finals_payload(season_dir)
    from backend.services.yaml_util import atomic_write, safe_dump_yaml
    atomic_write(season_dir / "finals.yaml", safe_dump_yaml(finals))
    return finals


@router.get("/seasons/{season_id}/finals")
def v1_get_finals(season_id: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    finals_path = season_dir / "finals.yaml"
    if finals_path.is_file():
        try:
            existing = safe_load_yaml_dict(finals_path.read_text())
        except Exception:
            existing = {}
    else:
        existing = {}

    finals = _build_finals_payload(season_dir)
    if isinstance(existing, dict) and existing.get("winner"):
        finals["winner"] = existing.get("winner")
    return finals


@router.post("/seasons/{season_id}/finals/declare-winner")
def v1_declare_winner(season_id: str, req: FinalsDeclareWinnerRequest):
    _validate_id(season_id, "season_id")
    _validate_id(req.corps_id, "corps_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    from backend.services.season_persistence import load_season, save_season
    data = load_season(season_dir)
    data.setdefault("metadata", {})
    data["metadata"]["status"] = "completed"
    data["metadata"]["winner"] = req.corps_id
    data["locked"] = True
    save_season(season_dir, data)

    finals = _build_finals_payload(season_dir)
    finals["winner"] = {
        "corps_id": req.corps_id,
        "division": req.division,
        "declared_at": datetime.now(timezone.utc).isoformat(),
    }
    from backend.services.yaml_util import atomic_write, safe_dump_yaml
    atomic_write(season_dir / "finals.yaml", safe_dump_yaml(finals))
    return finals


@router.post("/seasons/{season_id}/advance")
def v1_advance_tour(season_id: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.tour_coordinator import run_competition_round
    return run_competition_round(season_dir)


@router.get("/seasons/{season_id}/tour-status")
def v1_get_tour_status(season_id: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.tour_coordinator import get_tour_status
    return get_tour_status(season_dir)
