"""V1 API routes for model specs, strategy config, and leaderboards."""

import json

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_db_session, _resolve_corps, _validate_id

router = APIRouter(prefix="/api/v1")


# ---------- Model Specs ----------


@router.get("/model-specs")
def v1_list_model_specs():
    """List all model specs with global performance stats."""
    db = _get_db_session()
    try:
        from backend.models.model_spec import ModelSpec
        from backend.models.model_spec_performance import ModelSpecPerformance

        specs = db.query(ModelSpec).order_by(ModelSpec.name).all()
        result = []
        for spec in specs:
            # Aggregate global performance per spec
            perfs = (
                db.query(ModelSpecPerformance)
                .filter(
                    ModelSpecPerformance.model_spec_id == spec.id,
                    ModelSpecPerformance.corps_id.is_(None),
                )
                .all()
            )
            categories = {}
            for p in perfs:
                categories[p.task_category] = {
                    "avg_score": p.avg_score,
                    "total_attempts": p.total_attempts,
                    "successful_attempts": p.successful_attempts,
                }
            result.append({
                "id": spec.id,
                "name": spec.name,
                "provider": spec.provider,
                "model_id": spec.model_id,
                "task_categories": spec.categories_list,
                "is_active": spec.is_active,
                "performance": categories,
            })
        return result
    finally:
        db.close()


@router.get("/model-specs/{spec_id}/performance")
def v1_get_spec_performance(spec_id: str):
    """Performance breakdown by task_category for a single spec."""
    _validate_id(spec_id, "spec_id")
    db = _get_db_session()
    try:
        from backend.models.model_spec import ModelSpec
        from backend.models.model_spec_performance import ModelSpecPerformance

        spec = db.get(ModelSpec, spec_id)
        if spec is None:
            raise HTTPException(404, f"ModelSpec '{spec_id}' not found")

        perfs = (
            db.query(ModelSpecPerformance)
            .filter(ModelSpecPerformance.model_spec_id == spec_id)
            .order_by(ModelSpecPerformance.task_category)
            .all()
        )

        global_stats = []
        corps_stats = []
        for p in perfs:
            entry = {
                "task_category": p.task_category,
                "avg_score": p.avg_score,
                "total_attempts": p.total_attempts,
                "successful_attempts": p.successful_attempts,
                "success_rate": p.successful_attempts / p.total_attempts
                if p.total_attempts > 0
                else 0.0,
                "last_used_at": p.last_used_at.isoformat() if p.last_used_at else None,
            }
            if p.corps_id is None:
                global_stats.append(entry)
            else:
                entry["corps_id"] = p.corps_id
                corps_stats.append(entry)

        return {
            "spec_id": spec.id,
            "name": spec.name,
            "provider": spec.provider,
            "model_id": spec.model_id,
            "global": global_stats,
            "by_corps": corps_stats,
        }
    finally:
        db.close()


# ---------- Corps Strategy ----------


@router.get("/corps/{corps_id}/strategy")
def v1_get_corps_strategy(corps_id: str):
    """Current strategy config + per-category performance for a corps."""
    _validate_id(corps_id, "corps_id")
    db = _get_db_session()
    try:
        from backend.models.corps_strategy import CorpsStrategy
        from backend.services.model_spec_service import get_corps_spec_stats

        corps = _resolve_corps(db, corps_id)
        corps_id = corps.id  # normalize to UUID

        strategy = (
            db.query(CorpsStrategy)
            .filter(CorpsStrategy.corps_id == corps_id)
            .first()
        )
        if strategy is None:
            raise HTTPException(404, f"No strategy configured for corps '{corps_id}'")

        # Parse section overrides
        overrides = {}
        if strategy.section_overrides:
            try:
                overrides = json.loads(strategy.section_overrides)
            except (json.JSONDecodeError, TypeError):
                pass

        # Corps-specific performance stats
        perf_rows = get_corps_spec_stats(db, corps_id)
        performance = {}
        for p in perf_rows:
            performance[p.task_category] = {
                "model_spec_id": p.model_spec_id,
                "avg_score": p.avg_score,
                "total_attempts": p.total_attempts,
                "successful_attempts": p.successful_attempts,
            }

        # Include corps color scheme for frontend theming
        color_scheme = {}
        if corps.color_scheme:
            try:
                color_scheme = json.loads(corps.color_scheme)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "corps_id": corps_id,
            "corps_name": corps.name,
            "color_scheme": color_scheme,
            "strategy": {
                "id": strategy.id,
                "model_policy": strategy.model_policy,
                "preferred_provider": strategy.preferred_provider,
                "risk_tolerance": strategy.risk_tolerance,
                "exploration_rate": strategy.exploration_rate,
                "adaptation_style": strategy.adaptation_style,
                "section_overrides": overrides,
                "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
            },
            "performance": performance,
        }
    finally:
        db.close()


@router.get("/corps/{corps_id}/strategy/history")
def v1_get_corps_strategy_history(corps_id: str):
    """List strategy changes from the proposal audit trail.

    Scans offseason proposal files for strategy_change proposals
    that targeted this corps.
    """
    _validate_id(corps_id, "corps_id")
    from backend.api.v1.helpers import _get_root
    from backend.services.offseason_proposals import Proposal

    root = _get_root()
    seasons_dir = root / "seasons"
    history = []

    if not seasons_dir.exists():
        return {"corps_id": corps_id, "history": []}

    for season_dir in sorted(seasons_dir.iterdir()):
        if not season_dir.is_dir():
            continue
        proposals_path = season_dir / "offseason" / "proposals.md"
        if not proposals_path.exists():
            continue
        try:
            from backend.services.offseason_proposals import load_proposals
            proposals = load_proposals(root, season_dir.name)
            for p in proposals:
                if p.corps_id == corps_id and p.proposal_type == "strategy_change":
                    history.append({
                        "season_id": season_dir.name,
                        "description": p.description,
                        "changes": p.changes,
                    })
        except Exception:
            continue

    return {"corps_id": corps_id, "history": history}


@router.put("/corps/{corps_id}/strategy")
def v1_update_corps_strategy(corps_id: str, data: dict):
    """Manual strategy update (user override).

    Accepts any combination of: model_policy, preferred_provider,
    risk_tolerance, exploration_rate, adaptation_style, section_overrides.
    """
    _validate_id(corps_id, "corps_id")
    db = _get_db_session()
    try:
        from backend.models.corps_strategy import CorpsStrategy

        corps = _resolve_corps(db, corps_id)
        corps_id = corps.id  # normalize to UUID

        strategy = (
            db.query(CorpsStrategy)
            .filter(CorpsStrategy.corps_id == corps_id)
            .first()
        )
        if strategy is None:
            raise HTTPException(404, f"No strategy configured for corps '{corps_id}'")

        allowed_fields = {
            "model_policy", "preferred_provider", "risk_tolerance",
            "exploration_rate", "adaptation_style", "section_overrides",
        }
        updated = []
        for field, value in data.items():
            if field not in allowed_fields:
                continue
            if field == "section_overrides" and isinstance(value, dict):
                value = json.dumps(value)
            setattr(strategy, field, value)
            updated.append(field)

        if not updated:
            raise HTTPException(400, "No valid strategy fields provided")

        db.commit()

        return {
            "corps_id": corps_id,
            "updated_fields": updated,
            "strategy": {
                "model_policy": strategy.model_policy,
                "preferred_provider": strategy.preferred_provider,
                "risk_tolerance": strategy.risk_tolerance,
                "exploration_rate": strategy.exploration_rate,
                "adaptation_style": strategy.adaptation_style,
                "section_overrides": json.loads(strategy.section_overrides)
                if strategy.section_overrides else {},
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to update strategy: {e}")
    finally:
        db.close()


# ---------- Leaderboard ----------


@router.get("/leaderboard/{task_category}")
def v1_get_leaderboard(task_category: str, limit: int = 10):
    """Ranked model specs for a task category."""
    db = _get_db_session()
    try:
        from backend.services.model_spec_service import get_spec_leaderboard

        entries = get_spec_leaderboard(db, task_category, limit=limit)
        return {
            "task_category": task_category,
            "entries": entries,
        }
    finally:
        db.close()
