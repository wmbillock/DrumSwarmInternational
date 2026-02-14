"""V1 Experiments API — corps configuration and experiment comparison."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.v1.helpers import _get_db_session, _validate_id

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class UpdateConfigRequest(BaseModel):
    llm_provider: Optional[str] = None
    llm_model_override: Optional[str] = None
    methodology: Optional[str] = None
    architecture_style: Optional[str] = None
    coding_style: Optional[str] = None
    extra: Optional[dict] = None


class RecordExperimentRequest(BaseModel):
    corps_id: str
    show_id: Optional[str] = None
    competition_id: Optional[str] = None
    season_id: Optional[str] = None
    total_score: Optional[float] = None
    caption_scores: Optional[dict] = None
    iterations_used: Optional[int] = None
    tool_calls_count: Optional[int] = None
    sessions_spawned: Optional[int] = None
    failures_count: Optional[int] = None
    wall_time_seconds: Optional[float] = None
    notes: Optional[str] = None
    metrics: Optional[dict] = None


# ---------------------------------------------------------------------------
# Corps config endpoints
# ---------------------------------------------------------------------------


@router.get("/configs")
def list_configs():
    from backend.services.corps_config_service import list_configs, config_to_dict
    db = _get_db_session()
    try:
        configs = list_configs(db)
        return [config_to_dict(c) for c in configs]
    finally:
        db.close()


@router.get("/configs/{corps_id}")
def get_config(corps_id: str):
    _validate_id(corps_id, "corps_id")
    from backend.services.corps_config_service import get_config, config_to_dict
    db = _get_db_session()
    try:
        config = get_config(db, corps_id)
        if config is None:
            raise HTTPException(404, f"No config for corps {corps_id}")
        return config_to_dict(config)
    finally:
        db.close()


@router.put("/configs/{corps_id}")
def update_config(corps_id: str, req: UpdateConfigRequest):
    _validate_id(corps_id, "corps_id")
    from backend.services.corps_config_service import update_config, config_to_dict
    db = _get_db_session()
    try:
        config = update_config(
            db, corps_id,
            llm_provider=req.llm_provider,
            llm_model_override=req.llm_model_override,
            methodology=req.methodology,
            architecture_style=req.architecture_style,
            coding_style=req.coding_style,
            extra=req.extra,
        )
        return config_to_dict(config)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Experiment result endpoints
# ---------------------------------------------------------------------------


@router.get("/results")
def list_experiments(
    show_id: Optional[str] = None,
    corps_id: Optional[str] = None,
    season_id: Optional[str] = None,
):
    from backend.services.experiment_tracker import list_experiments, result_to_dict
    db = _get_db_session()
    try:
        results = list_experiments(db, show_id=show_id, corps_id=corps_id, season_id=season_id)
        return [result_to_dict(r) for r in results]
    finally:
        db.close()


@router.post("/results")
def record_experiment(req: RecordExperimentRequest):
    from backend.services.experiment_tracker import record_experiment, result_to_dict
    from backend.services.corps_config_service import get_config
    db = _get_db_session()
    try:
        # Auto-populate config snapshot
        config = get_config(db, req.corps_id)
        result = record_experiment(
            db,
            corps_id=req.corps_id,
            show_id=req.show_id,
            competition_id=req.competition_id,
            season_id=req.season_id,
            llm_provider=config.llm_provider if config else None,
            llm_model=config.llm_model_override if config else None,
            methodology=config.methodology if config else None,
            total_score=req.total_score,
            caption_scores=req.caption_scores,
            iterations_used=req.iterations_used,
            tool_calls_count=req.tool_calls_count,
            sessions_spawned=req.sessions_spawned,
            failures_count=req.failures_count,
            wall_time_seconds=req.wall_time_seconds,
            notes=req.notes,
            metrics=req.metrics,
        )
        return result_to_dict(result)
    finally:
        db.close()


@router.get("/compare/{show_id}")
def compare_experiments(show_id: str):
    _validate_id(show_id, "show_id")
    from backend.services.experiment_tracker import compare_experiments
    db = _get_db_session()
    try:
        return compare_experiments(db, show_id)
    finally:
        db.close()
