"""Model spec service — record outcomes and query best-performing specs."""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.models.model_spec import ModelSpec
from backend.models.model_spec_performance import ModelSpecPerformance

logger = logging.getLogger(__name__)


def record_model_spec_outcome(
    db: Session,
    model_spec_id: str,
    task_category: str,
    score: float,
    success: bool,
    corps_id: Optional[str] = None,
) -> ModelSpecPerformance:
    """Record an outcome for a model spec and recompute avg_score.

    Creates the performance row if it doesn't exist yet.
    """
    perf = (
        db.query(ModelSpecPerformance)
        .filter(
            ModelSpecPerformance.model_spec_id == model_spec_id,
            ModelSpecPerformance.task_category == task_category,
            ModelSpecPerformance.corps_id == corps_id
            if corps_id is not None
            else ModelSpecPerformance.corps_id.is_(None),
        )
        .first()
    )

    if perf is None:
        perf = ModelSpecPerformance(
            model_spec_id=model_spec_id,
            task_category=task_category,
            corps_id=corps_id,
            total_attempts=0,
            successful_attempts=0,
            total_score=0.0,
            avg_score=0.0,
        )
        db.add(perf)

    perf.total_attempts += 1
    if success:
        perf.successful_attempts += 1
    perf.total_score += score
    perf.avg_score = perf.total_score / perf.total_attempts
    perf.last_used_at = datetime.now(timezone.utc)

    db.flush()
    return perf


def get_best_spec_for_task(
    db: Session,
    task_category: str,
    corps_id: Optional[str] = None,
    min_attempts: int = 3,
) -> Optional[ModelSpec]:
    """Return the highest avg_score active ModelSpec for this category.

    Only considers specs with at least `min_attempts` recorded outcomes.
    Searches corps-specific stats first; falls back to global if none found.
    """
    def _query(cid):
        return (
            db.query(ModelSpecPerformance)
            .join(ModelSpec, ModelSpec.id == ModelSpecPerformance.model_spec_id)
            .filter(
                ModelSpecPerformance.task_category == task_category,
                ModelSpecPerformance.total_attempts >= min_attempts,
                ModelSpec.is_active.is_(True),
                ModelSpecPerformance.corps_id == cid
                if cid is not None
                else ModelSpecPerformance.corps_id.is_(None),
            )
            .order_by(ModelSpecPerformance.avg_score.desc())
            .first()
        )

    # Try corps-specific first
    if corps_id is not None:
        perf = _query(corps_id)
        if perf is not None:
            return db.get(ModelSpec, perf.model_spec_id)

    # Fall back to global
    perf = _query(None)
    if perf is not None:
        return db.get(ModelSpec, perf.model_spec_id)

    return None


def get_spec_leaderboard(
    db: Session,
    task_category: str,
    limit: int = 10,
) -> list[dict]:
    """Return ranked list of specs for a category (global stats)."""
    rows = (
        db.query(ModelSpecPerformance, ModelSpec)
        .join(ModelSpec, ModelSpec.id == ModelSpecPerformance.model_spec_id)
        .filter(
            ModelSpecPerformance.task_category == task_category,
            ModelSpecPerformance.corps_id.is_(None),
        )
        .order_by(ModelSpecPerformance.avg_score.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "model_spec_id": spec.id,
            "name": spec.name,
            "provider": spec.provider,
            "avg_score": perf.avg_score,
            "total_attempts": perf.total_attempts,
            "successful_attempts": perf.successful_attempts,
            "success_rate": perf.successful_attempts / perf.total_attempts
            if perf.total_attempts > 0
            else 0.0,
        }
        for perf, spec in rows
    ]


def get_corps_spec_stats(
    db: Session,
    corps_id: str,
) -> list[ModelSpecPerformance]:
    """Return all performance records scoped to a corps."""
    return (
        db.query(ModelSpecPerformance)
        .filter(ModelSpecPerformance.corps_id == corps_id)
        .order_by(
            ModelSpecPerformance.task_category,
            ModelSpecPerformance.avg_score.desc(),
        )
        .all()
    )
