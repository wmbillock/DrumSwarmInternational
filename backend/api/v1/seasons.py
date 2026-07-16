"""V1 API — Seasons routes."""

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_root, _validate_id, _get_db_session, _slugify
from backend.api.v1.schemas import (
    AutoAdvanceRequest,
    CreateSeasonRequest,
    UpdateSeasonRequest,
    RegisterCorpsRequest,
    SeasonShowRequest,
    SeasonAssignRequest,
    SeasonConfigRequest,
    FinalsDeclareWinnerRequest,
    DraftApplyRequest,
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

    # Build corps_id -> display_name mapping from DB
    corps_names: dict[str, str] = {}
    try:
        from backend.models.corps import Corps
        db = _get_db_session()
        try:
            for cid in corps_ids:
                corps_obj = db.get(Corps, cid)
                if corps_obj:
                    corps_names[cid] = corps_obj.name
        finally:
            db.close()
    except Exception:
        pass

    registered_set = set(corps_ids)

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
                sc = safe_load_yaml_dict(scores_path.read_text(encoding="utf-8"))
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
                "display_name": corps_names.get(cid, cid),
                "score": scores_by_corps.get(cid, 0.0),
                "qualified": qualification.get(cid, False),
                "scores_count": score_counts.get(cid, 0),
            }
            for idx, cid in enumerate(ordered)
        ]

    overall = rank_rows(corps_ids)
    division_rows = []
    for show_slug, corps_list in (divisions or {}).items():
        # Filter to only registered corps — stale division entries get dropped
        valid_corps = [cid for cid in (corps_list or []) if cid in registered_set]
        division_rows.append({
            "show_slug": show_slug,
            "standings": rank_rows(valid_corps),
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
        data = safe_load_yaml_dict(season_yaml.read_text(encoding="utf-8"))
        season_id = data.get("season_id", season_dir.name)
        meta = data.get("metadata", {})
        # Derive status from metadata or schedule progress
        status = meta.get("status", "")
        if not status:
            schedule = data.get("schedule") or []
            completed = sum(1 for e in schedule if e.get("status") == "completed")
            total = len(schedule)
            if total > 0 and completed == total:
                status = "completed"
            elif completed > 0:
                status = "touring"
            elif data.get("shows"):
                status = "active"
            else:
                status = "planning"
        corps_ids = set()
        for div_corps in (data.get("divisions") or {}).values():
            if isinstance(div_corps, list):
                corps_ids.update(div_corps)
        registered = data.get("registered_corps") or []
        corps_count = len(corps_ids) or len(registered)
        results.append({
            "season_id": season_id,
            "name": meta.get("name", season_id),
            "dir_name": season_dir.name,
            "status": status,
            "registered_corps_count": corps_count,
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

    # Build slug -> short_name mapping from show status files
    show_names: dict[str, str] = {}
    for slug in data.get("shows", []):
        status_path = root / "shows" / slug / "status.yaml"
        if status_path.is_file():
            show_data = safe_load_yaml_dict(status_path.read_text(encoding="utf-8"))
            short = show_data.get("short_name", "")
            if short:
                show_names[slug] = short
    data["show_names"] = show_names

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
    data = safe_load_yaml_dict(season_yaml.read_text(encoding="utf-8"))
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
    return safe_load_yaml_dict(standings_yaml.read_text(encoding="utf-8"))


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
            existing = safe_load_yaml_dict(finals_path.read_text(encoding="utf-8"))
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

    # Generate post-mortem documents for all participating corps
    try:
        from backend.services.post_mortem import generate_season_post_mortems
        from backend.api.v1.helpers import _get_db_session
        db = _get_db_session()
        try:
            generate_season_post_mortems(root, season_id, db=db)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Post-mortem generation failed for season {season_id}: {e}")

    return finals


@router.post("/seasons/{season_id}/deploy-winner")
def v1_deploy_winner(season_id: str):
    """Dispatch the winning corps' ED with the season's show prompt."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    finals_path = season_dir / "finals.yaml"
    if not finals_path.is_file():
        raise HTTPException(400, "Finals not declared yet")

    finals = safe_load_yaml_dict(finals_path.read_text(encoding="utf-8"))
    winner = finals.get("winner")
    if not winner or not isinstance(winner, dict) or not winner.get("corps_id"):
        raise HTTPException(400, "No winner declared — declare a winner first")

    winner_corps_id = winner["corps_id"]

    # Find show_prompt from the season's show slugs
    from backend.services.season_persistence import load_season
    data = load_season(season_dir)
    show_slugs = data.get("shows") or []
    show_prompt = ""
    show_slug = ""
    for slug in show_slugs:
        prompt_path = root / "shows" / slug / "show_prompt.md"
        if prompt_path.exists() and prompt_path.stat().st_size > 0:
            show_prompt = prompt_path.read_text(encoding="utf-8")
            show_slug = slug
            break

    if not show_prompt:
        raise HTTPException(400, "No show_prompt.md found for any show in this season")

    from backend.api.app import get_task_manager
    tm = get_task_manager()
    if not tm:
        raise HTTPException(503, "Task manager not initialized")

    dispatched = []
    skipped = []
    db = _get_db_session()
    try:
        ed_session = tm.get_session_for_role(db, winner_corps_id, "executive_director")
        if not ed_session:
            skipped.append({"corps_id": winner_corps_id, "reason": "no ED session found"})
        elif tm.is_active(ed_session):
            skipped.append({"corps_id": winner_corps_id, "reason": "ED already active"})
        else:
            task_desc = (
                f"WINNER DEPLOYMENT — Your corps won season {season_id}!\n\n"
                f"Execute the winning show prompt:\n\n---\n\n{show_prompt}"
            )
            tm.start_agent(session_id=ed_session, task_description=task_desc, corps_id=winner_corps_id)
            dispatched.append({"corps_id": winner_corps_id, "session_id": ed_session})
    finally:
        db.close()

    return {
        "season_id": season_id,
        "winner_corps_id": winner_corps_id,
        "show_slug": show_slug,
        "dispatched": dispatched,
        "skipped": skipped,
        "status": "deployed" if dispatched else "skipped",
    }


@router.post("/seasons/{season_id}/advance")
def v1_advance_tour(season_id: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    # Track as an operation so frontend can poll status
    from backend.services.operation_tracker import (
        create_operation, start_operation, complete_operation, fail_operation,
    )
    import json as _json
    db = _get_db_session()
    try:
        op = create_operation(
            db, "advance_round",
            target_type="season", target_id=season_id,
            label=f"Advancing tour round for {season_id}",
        )
        operation_id = op.id
    finally:
        db.close()

    from backend.services.tour_coordinator import run_competition_round
    db2 = _get_db_session()
    try:
        start_operation(db2, operation_id)
        result = run_competition_round(season_dir)
        complete_operation(db2, operation_id, result=_json.dumps(result, default=str))
        result["operation_id"] = operation_id
        return result
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Tour advance failed for %s", season_id)
        fail_operation(db2, operation_id, error=str(exc))
        raise HTTPException(500, f"Tour advance failed: {exc}")
    finally:
        db2.close()


@router.post("/seasons/{season_id}/auto-advance")
def v1_set_auto_advance(season_id: str, req: AutoAdvanceRequest):
    """Enable or disable metronome-driven auto-advance for a touring season."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.tour_coordinator import set_auto_advance
    return set_auto_advance(season_dir, req.enabled)


@router.get("/seasons/{season_id}/tour-status")
def v1_get_tour_status(season_id: str):
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.tour_coordinator import get_tour_status
    return get_tour_status(season_dir)


@router.post("/seasons/{season_id}/assign-shows")
def v1_assign_corps_shows(season_id: str):
    """Assign each corps ONE show for the season via round-robin.

    Honors existing division assignments first; unassigned corps get
    round-robin. Returns {corps_id: show_slug} mapping.
    """
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    from backend.services.season_persistence import load_season
    from backend.services.tour_coordinator import assign_corps_shows

    data = load_season(season_dir)
    if not data.get("shows"):
        raise HTTPException(400, "No shows assigned to this season")
    if not data.get("registered_corps"):
        raise HTTPException(400, "No corps registered for this season")

    assignments = assign_corps_shows(season_dir)
    return {"status": "assigned", "corps_show_assignments": assignments}


@router.post("/seasons/{season_id}/draft")
def v1_run_show_draft(season_id: str):
    """Preview a show draft — returns picks without saving assignments."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    from backend.services.season_persistence import load_season
    from backend.services.show_draft_service import run_show_draft

    data = load_season(season_dir)
    show_slugs = data.get("shows", [])
    corps_ids = data.get("registered_corps", [])

    if not show_slugs:
        raise HTTPException(400, "No shows assigned to this season")
    if not corps_ids:
        raise HTTPException(400, "No corps registered for this season")

    db = _get_db_session()
    try:
        result = run_show_draft(db, season_dir, show_slugs, corps_ids)
        return result
    finally:
        db.close()


@router.post("/seasons/{season_id}/draft/apply")
def v1_apply_show_draft(season_id: str, req: DraftApplyRequest):
    """Apply draft assignments — saves to corps_show_assignments.

    The request contains {show_slug: [corps_ids]} which we invert to
    {corps_id: show_slug} for the 1-show-per-corps model.
    """
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    from backend.services.season_persistence import load_season, save_season

    # Invert {show: [corps]} to {corps: show}
    corps_show_map: dict[str, str] = {}
    for show_slug, corps_ids in req.assignments.items():
        for cid in corps_ids:
            corps_show_map[cid] = show_slug

    data = load_season(season_dir)
    data["corps_show_assignments"] = corps_show_map
    save_season(season_dir, data)

    return {"status": "applied", "corps_show_assignments": corps_show_map}


# =========================================================================
# POST-MORTEMS
# =========================================================================

@router.get("/seasons/{season_id}/post-mortems")
def v1_list_season_post_mortems(season_id: str):
    """List all post-mortem documents for a season."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    pm_dir = root / "seasons" / season_id / "post_mortems"
    if not pm_dir.is_dir():
        return []
    results = []
    for f in sorted(pm_dir.iterdir()):
        if f.suffix == ".md":
            corps_id = f.stem
            results.append({
                "corps_id": corps_id,
                "season_id": season_id,
                "generated_at": datetime.fromtimestamp(
                    f.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            })
    return results


@router.get("/seasons/{season_id}/post-mortems/{corps_id}")
def v1_get_post_mortem(season_id: str, corps_id: str):
    """Get a post-mortem document for a specific corps in a season."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    from backend.services.post_mortem import get_corps_post_mortem
    content = get_corps_post_mortem(root, season_id, corps_id)
    if content is None:
        raise HTTPException(404, f"No post-mortem found for {corps_id} in season {season_id}")
    return {"corps_id": corps_id, "season_id": season_id, "content": content}


@router.get("/seasons/{season_id}/artifacts/{corps_id}")
def v1_get_corps_artifacts(season_id: str, corps_id: str):
    """Get detailed artifact review for a corps in a season.

    Returns reps, artifacts, segment tree, score history, and spec completion.
    """
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    from backend.models.corps import Corps
    from backend.models.artifact import Artifact
    from backend.models.rep import Rep, RepStatus
    from backend.models.segment import Segment
    from backend.models.show import Show

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, f"Corps '{corps_id}' not found")

        # --- Segment tree ---
        show = db.query(Show).filter(Show.corps_id == corps_id).first()
        segment_tree = []
        segment_ids: list[str] = []
        if show and show.segment_root_id:
            # BFS to build tree
            from collections import deque
            queue = deque([show.segment_root_id])
            while queue:
                sid = queue.popleft()
                seg = db.get(Segment, sid)
                if not seg:
                    continue
                segment_ids.append(sid)
                children = db.query(Segment).filter(Segment.parent_id == sid).all()
                child_ids = [c.id for c in children]
                queue.extend(child_ids)
                segment_tree.append({
                    "id": seg.id,
                    "parent_id": seg.parent_id,
                    "type": seg.type.value,
                    "title": seg.title,
                    "description": seg.description,
                    "status": seg.status.value,
                    "caption": seg.caption,
                    "children": child_ids,
                })

        # --- Reps ---
        reps_data = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0, "total": 0, "items": []}
        if segment_ids:
            reps = db.query(Rep).filter(Rep.segment_id.in_(segment_ids)).all()
            for rep in reps:
                reps_data["total"] += 1
                status_key = rep.status.value
                if status_key in reps_data:
                    reps_data[status_key] += 1
                reps_data["items"].append({
                    "id": rep.id,
                    "segment_id": rep.segment_id,
                    "status": rep.status.value,
                    "result": (rep.result[:500] if rep.result else None),
                    "error": rep.error,
                    "assigned_to": rep.assigned_to,
                    "created_at": rep.created_at.isoformat() if rep.created_at else None,
                    "updated_at": rep.updated_at.isoformat() if rep.updated_at else None,
                })

        # --- Artifacts ---
        artifacts = (
            db.query(Artifact)
            .filter(Artifact.corps_id == corps_id)
            .order_by(Artifact.created_at.desc())
            .all()
        )
        artifacts_data = [a.to_dict() for a in artifacts]

        # --- Score history ---
        perf_dir = season_dir / "performances" / corps_id
        score_history: list[dict] = []
        if perf_dir.exists():
            for f in sorted(perf_dir.glob("scores*.yaml")):
                try:
                    sc = safe_load_yaml_dict(f.read_text(encoding="utf-8"))
                    if isinstance(sc, dict):
                        sc["source_file"] = f.name
                        score_history.append(sc)
                except Exception:
                    pass
            # Also include per-round critique files
            for f in sorted(perf_dir.glob("critique_round_*.md")):
                score_history.append({
                    "source_file": f.name,
                    "type": "critique",
                    "round": f.stem.replace("critique_round_", ""),
                })

        # --- Spec completion ---
        spec_completion = None
        from backend.services.season_persistence import load_season
        season_data = load_season(season_dir)
        show_slugs = season_data.get("shows", [])
        # Check corps_show_assignments for this corps' specific show
        assignments = season_data.get("corps_show_assignments", {})
        corps_show = assignments.get(corps_id)
        if corps_show:
            show_slugs = [corps_show]

        for slug in show_slugs:
            show_dir = root / "shows" / slug
            if show_dir.exists():
                try:
                    from backend.services.spec_checker import check_spec_completion
                    spec_completion = check_spec_completion(
                        show_dir,
                        db=db,
                        corps_ids=[corps_id],
                        segment_root_id=show.segment_root_id if show else None,
                    )
                except Exception:
                    pass
                break

        return {
            "corps_id": corps_id,
            "corps_name": corps.name,
            "season_id": season_id,
            "segment_tree": segment_tree,
            "reps": reps_data,
            "artifacts": artifacts_data,
            "score_history": score_history,
            "spec_completion": spec_completion,
        }
    finally:
        db.close()


@router.post("/seasons/{season_id}/post-mortems/generate")
def v1_generate_post_mortems(season_id: str):
    """Manually trigger post-mortem generation for a season."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    from backend.services.post_mortem import generate_season_post_mortems
    db = _get_db_session()
    try:
        results = generate_season_post_mortems(root, season_id, db=db)
    finally:
        db.close()

    return {
        "season_id": season_id,
        "generated": len(results),
        "corps_ids": list(results.keys()),
    }
