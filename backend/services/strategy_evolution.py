"""Strategy evolution — analyze season results and propose strategy changes.

After a season ends, compares each corps' ModelSpecPerformance data against
league-wide averages to propose concrete CorpsStrategy mutations:
provider switches, exploration rate tweaks, and section override swaps.
"""

import json
import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.corps_strategy import CorpsStrategy, ModelPolicy
from backend.models.model_spec import ModelSpec
from backend.models.model_spec_performance import ModelSpecPerformance
from backend.services.offseason_proposals import Proposal

logger = logging.getLogger(__name__)

# How far below the league average a corps category must be to trigger proposals
_WEAK_CATEGORY_THRESHOLD = 5.0  # points below league avg

# Minimum attempts to consider a performance record meaningful
_MIN_ATTEMPTS = 3

# Exploration rate adjustment step
_EXPLORATION_STEP = 0.1

# Max exploration rate we'll propose
_MAX_EXPLORATION_RATE = 0.5

# Min exploration rate we'll propose for top corps consolidation
_MIN_EXPLORATION_RATE = 0.02


def generate_strategy_proposals(
    db: Session,
    season_id: str,
    standings_results: list[dict],
) -> list[Proposal]:
    """Analyze season results and propose strategy changes.

    Args:
        db: Database session.
        season_id: The season that just completed.
        standings_results: List of dicts with at least ``corps_id`` and ``rank``.

    Returns:
        List of Proposal objects with proposal_type="strategy_change".
    """
    if not standings_results or len(standings_results) < 2:
        return []

    total = len(standings_results)
    sorted_standings = sorted(standings_results, key=lambda r: r.get("rank", 0))

    # Compute median rank
    median_rank = total / 2.0

    # Top-25% cutoff
    top_cutoff = max(1, total // 4)

    # Build league-wide category averages (global performance data)
    league_avgs = _compute_league_averages(db)
    if not league_avgs:
        return []

    proposals: list[Proposal] = []

    for entry in sorted_standings:
        corps_id = entry["corps_id"]
        rank = entry.get("rank", 0)

        strategy = (
            db.query(CorpsStrategy)
            .filter(CorpsStrategy.corps_id == corps_id)
            .first()
        )
        if strategy is None:
            continue

        if rank > median_rank:
            # Underperforming corps — propose improvements
            underperformer_proposals = _propose_for_underperformer(
                db, corps_id, strategy, league_avgs,
            )
            proposals.extend(underperformer_proposals)
        elif rank <= top_cutoff:
            # Top-25% corps — propose consolidation
            consolidation_proposals = _propose_for_top_performer(
                db, corps_id, strategy, league_avgs,
            )
            proposals.extend(consolidation_proposals)

    return proposals


def _compute_league_averages(db: Session) -> dict[str, float]:
    """Compute average score per task_category across all corps."""
    rows = (
        db.query(
            ModelSpecPerformance.task_category,
            func.avg(ModelSpecPerformance.avg_score),
        )
        .filter(ModelSpecPerformance.total_attempts >= _MIN_ATTEMPTS)
        .group_by(ModelSpecPerformance.task_category)
        .all()
    )
    return {cat: avg for cat, avg in rows if avg is not None}


def _get_corps_category_scores(
    db: Session, corps_id: str,
) -> dict[str, float]:
    """Get this corps' average score per task category."""
    rows = (
        db.query(ModelSpecPerformance)
        .filter(
            ModelSpecPerformance.corps_id == corps_id,
            ModelSpecPerformance.total_attempts >= _MIN_ATTEMPTS,
        )
        .all()
    )
    return {r.task_category: r.avg_score for r in rows}


def _find_best_global_spec(
    db: Session, task_category: str,
) -> Optional[ModelSpec]:
    """Find the globally best-performing active spec for a category."""
    perf = (
        db.query(ModelSpecPerformance)
        .join(ModelSpec, ModelSpec.id == ModelSpecPerformance.model_spec_id)
        .filter(
            ModelSpecPerformance.task_category == task_category,
            ModelSpecPerformance.corps_id.is_(None),
            ModelSpecPerformance.total_attempts >= _MIN_ATTEMPTS,
            ModelSpec.is_active.is_(True),
        )
        .order_by(ModelSpecPerformance.avg_score.desc())
        .first()
    )
    if perf is None:
        return None
    return db.get(ModelSpec, perf.model_spec_id)


def _propose_for_underperformer(
    db: Session,
    corps_id: str,
    strategy: CorpsStrategy,
    league_avgs: dict[str, float],
) -> list[Proposal]:
    """Generate proposals for a below-median corps."""
    proposals: list[Proposal] = []
    corps_scores = _get_corps_category_scores(db, corps_id)

    # Identify weak categories
    weak_categories: list[str] = []
    for cat, league_avg in league_avgs.items():
        corps_avg = corps_scores.get(cat)
        if corps_avg is not None and corps_avg < league_avg - _WEAK_CATEGORY_THRESHOLD:
            weak_categories.append(cat)

    # 1. Provider policy change: if single_provider and another provider scores better
    if (
        strategy.model_policy == ModelPolicy.SINGLE_PROVIDER.value
        and weak_categories
    ):
        for cat in weak_categories:
            best_spec = _find_best_global_spec(db, cat)
            if best_spec and best_spec.provider != strategy.preferred_provider:
                # Another provider does better — suggest switching policy
                if len(weak_categories) == 1:
                    # One weak category: section_specialized with override
                    proposals.append(Proposal(
                        proposal_type="strategy_change",
                        corps_id=corps_id,
                        description=(
                            f"Switch to section_specialized: use {best_spec.name} "
                            f"for {cat} (outperforms current provider)"
                        ),
                        changes={
                            "model_policy": ModelPolicy.SECTION_SPECIALIZED.value,
                            "section_overrides": json.dumps({cat: best_spec.id}),
                        },
                    ))
                else:
                    # Multiple weak categories: best_of_breed
                    proposals.append(Proposal(
                        proposal_type="strategy_change",
                        corps_id=corps_id,
                        description=(
                            f"Switch to best_of_breed: single_provider "
                            f"underperforming in {len(weak_categories)} categories"
                        ),
                        changes={
                            "model_policy": ModelPolicy.BEST_OF_BREED.value,
                        },
                    ))
                break  # one policy change proposal per corps

    # 2. Exploration rate increase: if corps is stagnating (low exploration, weak scores)
    if (
        strategy.exploration_rate < _MAX_EXPLORATION_RATE
        and weak_categories
        and strategy.model_policy != ModelPolicy.SINGLE_PROVIDER.value
    ):
        new_rate = min(
            strategy.exploration_rate + _EXPLORATION_STEP,
            _MAX_EXPLORATION_RATE,
        )
        proposals.append(Proposal(
            proposal_type="strategy_change",
            corps_id=corps_id,
            description=(
                f"Increase exploration_rate from "
                f"{strategy.exploration_rate:.2f} to {new_rate:.2f} "
                f"(underperforming in {len(weak_categories)} categories)"
            ),
            changes={"exploration_rate": new_rate},
        ))

    # 3. Section override swap: if a specific override spec underperforms
    if strategy.section_overrides:
        try:
            overrides = json.loads(strategy.section_overrides)
        except (json.JSONDecodeError, TypeError):
            overrides = {}

        for cat, spec_id in overrides.items():
            if cat not in weak_categories:
                continue
            best_spec = _find_best_global_spec(db, cat)
            if best_spec and best_spec.id != spec_id:
                proposals.append(Proposal(
                    proposal_type="strategy_change",
                    corps_id=corps_id,
                    description=(
                        f"Swap {cat} section override to {best_spec.name} "
                        f"(current override underperforming)"
                    ),
                    changes={
                        "section_overrides": json.dumps(
                            {**overrides, cat: best_spec.id}
                        ),
                    },
                ))

    return proposals


def _propose_for_top_performer(
    db: Session,
    corps_id: str,
    strategy: CorpsStrategy,
    league_avgs: dict[str, float],
) -> list[Proposal]:
    """Generate consolidation proposals for a top-25% corps."""
    proposals: list[Proposal] = []

    # Only propose consolidation for best_of_breed with high exploration
    if (
        strategy.model_policy == ModelPolicy.BEST_OF_BREED.value
        and strategy.exploration_rate > _MIN_EXPLORATION_RATE
    ):
        new_rate = max(
            strategy.exploration_rate - _EXPLORATION_STEP,
            _MIN_EXPLORATION_RATE,
        )
        proposals.append(Proposal(
            proposal_type="strategy_change",
            corps_id=corps_id,
            description=(
                f"Decrease exploration_rate from "
                f"{strategy.exploration_rate:.2f} to {new_rate:.2f} "
                f"(top performer — lock in winning configuration)"
            ),
            changes={"exploration_rate": new_rate},
        ))

    return proposals
