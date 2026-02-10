"""Experiment tracker — record and compare corps performance across shows."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.experiment_result import ExperimentResult

logger = logging.getLogger(__name__)


def record_experiment(
    db: Session,
    corps_id: str,
    show_id: Optional[str] = None,
    competition_id: Optional[str] = None,
    season_id: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    methodology: Optional[str] = None,
    total_score: Optional[float] = None,
    caption_scores: Optional[dict] = None,
    iterations_used: Optional[int] = None,
    tool_calls_count: Optional[int] = None,
    sessions_spawned: Optional[int] = None,
    failures_count: Optional[int] = None,
    wall_time_seconds: Optional[float] = None,
    notes: Optional[str] = None,
    metrics: Optional[dict] = None,
) -> ExperimentResult:
    """Record an experiment result for a corps running a show."""
    result = ExperimentResult(
        corps_id=corps_id,
        show_id=show_id,
        competition_id=competition_id,
        season_id=season_id,
        llm_provider=llm_provider,
        llm_model=llm_model,
        methodology=methodology,
        total_score=total_score,
        caption_scores=caption_scores,
        iterations_used=iterations_used,
        tool_calls_count=tool_calls_count,
        sessions_spawned=sessions_spawned,
        failures_count=failures_count,
        wall_time_seconds=wall_time_seconds,
        notes=notes,
        metrics=metrics,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def list_experiments(
    db: Session,
    show_id: Optional[str] = None,
    corps_id: Optional[str] = None,
    season_id: Optional[str] = None,
) -> list[ExperimentResult]:
    """List experiment results with optional filters."""
    q = db.query(ExperimentResult)
    if show_id:
        q = q.filter(ExperimentResult.show_id == show_id)
    if corps_id:
        q = q.filter(ExperimentResult.corps_id == corps_id)
    if season_id:
        q = q.filter(ExperimentResult.season_id == season_id)
    return q.order_by(ExperimentResult.created_at.desc()).all()


def compare_experiments(
    db: Session,
    show_id: str,
) -> list[dict]:
    """Compare all corps that ran the same show.

    Returns a list sorted by total_score descending.
    """
    results = list_experiments(db, show_id=show_id)

    comparisons = []
    for r in results:
        comparisons.append({
            "corps_id": r.corps_id,
            "llm_provider": r.llm_provider,
            "llm_model": r.llm_model,
            "methodology": r.methodology,
            "total_score": r.total_score,
            "caption_scores": r.caption_scores,
            "iterations_used": r.iterations_used,
            "tool_calls_count": r.tool_calls_count,
            "failures_count": r.failures_count,
            "wall_time_seconds": r.wall_time_seconds,
        })

    comparisons.sort(key=lambda x: x.get("total_score") or 0, reverse=True)
    return comparisons


def result_to_dict(result: ExperimentResult) -> dict:
    """Serialize an ExperimentResult."""
    return {
        "id": result.id,
        "corps_id": result.corps_id,
        "show_id": result.show_id,
        "competition_id": result.competition_id,
        "season_id": result.season_id,
        "llm_provider": result.llm_provider,
        "llm_model": result.llm_model,
        "methodology": result.methodology,
        "total_score": result.total_score,
        "caption_scores": result.caption_scores,
        "iterations_used": result.iterations_used,
        "tool_calls_count": result.tool_calls_count,
        "sessions_spawned": result.sessions_spawned,
        "failures_count": result.failures_count,
        "wall_time_seconds": result.wall_time_seconds,
        "notes": result.notes,
        "metrics": result.metrics,
        "created_at": str(result.created_at) if result.created_at else None,
    }
