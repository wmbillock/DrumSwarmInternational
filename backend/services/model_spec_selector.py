"""Model spec selector — picks the best ModelSpec for a task given corps strategy.

Implements the exploration/exploitation algorithm that lets each corps
develop its own model preferences over time.
"""

import json
import logging
import random
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_definition import AgentDefinition, ModelTier
from backend.models.corps_strategy import CorpsStrategy, ModelPolicy
from backend.models.model_spec import ModelSpec
from backend.models.model_spec_performance import ModelSpecPerformance
from backend.services.model_spec_service import get_best_spec_for_task

logger = logging.getLogger(__name__)

# Minimum attempts before we consider a spec "well-tested"
_WELL_TESTED_THRESHOLD = 3

# Maps ModelTier enum to model_id substrings for reverse-mapping
_TIER_MODEL_PATTERNS: dict[ModelTier, list[str]] = {
    ModelTier.OPUS: ["opus"],
    ModelTier.SONNET: ["sonnet"],
    ModelTier.HAIKU: ["haiku"],
}

# Maps model_id patterns back to ModelTier for backward compat
_MODEL_ID_TO_TIER: list[tuple[str, ModelTier]] = [
    ("opus", ModelTier.OPUS),
    ("sonnet", ModelTier.SONNET),
    ("haiku", ModelTier.HAIKU),
    # Ollama / other models map to SONNET as the general-purpose tier
    ("deepseek", ModelTier.SONNET),
    ("qwen", ModelTier.SONNET),
    ("gpt-4o-mini", ModelTier.HAIKU),
    ("gpt-4o", ModelTier.SONNET),
    ("gpt-4", ModelTier.OPUS),
]


def model_spec_to_model_tier(spec: ModelSpec) -> ModelTier:
    """Map a ModelSpec back to a ModelTier for backward compat with SmartRouter."""
    model_id_lower = spec.model_id.lower()
    for pattern, tier in _MODEL_ID_TO_TIER:
        if pattern in model_id_lower:
            return tier
    return ModelTier.SONNET  # safe default


def model_spec_to_provider_kwargs(spec: ModelSpec) -> dict:
    """Return kwargs needed to route to the right provider.

    Gives the caller everything needed to construct an LLM request:
    provider, model_id, and optional LoRA configuration.
    """
    result: dict = {
        "provider": spec.provider,
        "model_id": spec.model_id,
    }
    if spec.lora_id:
        result["lora_id"] = spec.lora_id
    if spec.adapter_path:
        result["adapter_path"] = spec.adapter_path
    return result


def _get_active_specs_for_category(
    db: Session,
    task_category: str,
    provider: Optional[str] = None,
) -> list[ModelSpec]:
    """Get active specs that list this task_category (or have no categories = general purpose)."""
    q = db.query(ModelSpec).filter(ModelSpec.is_active.is_(True))
    if provider:
        q = q.filter(ModelSpec.provider == provider)

    all_specs = q.all()
    matched = []
    for spec in all_specs:
        cats = spec.categories_list
        if not cats or task_category in cats:
            matched.append(spec)
    return matched


def _pick_exploration_spec(
    db: Session,
    candidates: list[ModelSpec],
    task_category: str,
    corps_id: Optional[str],
    rng: random.Random,
) -> Optional[ModelSpec]:
    """Pick a spec for exploration, weighted toward less-tested specs."""
    if not candidates:
        return None

    # Build weights: inverse of attempt count (less tested = higher weight)
    weights: list[float] = []
    for spec in candidates:
        perf = (
            db.query(ModelSpecPerformance)
            .filter(
                ModelSpecPerformance.model_spec_id == spec.id,
                ModelSpecPerformance.task_category == task_category,
                ModelSpecPerformance.corps_id == corps_id
                if corps_id is not None
                else ModelSpecPerformance.corps_id.is_(None),
            )
            .first()
        )
        attempts = perf.total_attempts if perf else 0
        # Weight: 1/(1+attempts) so untested specs get weight 1.0, heavily tested get near 0
        weights.append(1.0 / (1.0 + attempts))

    chosen = rng.choices(candidates, weights=weights, k=1)[0]
    return chosen


def _get_section_override(strategy: CorpsStrategy, task_category: str) -> Optional[str]:
    """Check section_overrides JSON for a model_spec_id mapped to this category."""
    if not strategy.section_overrides:
        return None
    try:
        overrides = json.loads(strategy.section_overrides)
    except (json.JSONDecodeError, TypeError):
        return None
    return overrides.get(task_category)


class _DefaultStrategy:
    """Synthetic default strategy for corps without a real one."""
    model_policy = ModelPolicy.BEST_OF_BREED.value
    preferred_provider = None
    risk_tolerance = 0.5
    exploration_rate = 0.1
    adaptation_style = "prompt_only"
    section_overrides = None
    corps_id = None


def select_model_spec(
    db: Session,
    corps_id: Optional[str],
    task_category: str,
    agent_definition: AgentDefinition,
    rng: Optional[random.Random] = None,
) -> Optional[ModelSpec]:
    """Select the best model spec for this task given the corps' strategy.

    Algorithm:
    1. Load CorpsStrategy (defaults if none)
    2. Apply model_policy filters
    3. Roll exploration vs exploitation
    4. Apply risk tolerance
    5. Fall back to ModelTier if nothing found

    Args:
        db: Database session.
        corps_id: Corps ID (None for unaffiliated agents).
        task_category: Task category string (e.g. "frontend", "backend").
        agent_definition: The agent's definition (used for ModelTier fallback).
        rng: Optional Random instance for deterministic testing.

    Returns:
        A ModelSpec, or None if nothing is available (caller should use ModelTier).
    """
    if rng is None:
        rng = random.Random()

    # 1. Load strategy
    strategy: CorpsStrategy
    if corps_id:
        found = db.query(CorpsStrategy).filter(CorpsStrategy.corps_id == corps_id).first()
        strategy = found if found else _DefaultStrategy()
    else:
        strategy = _DefaultStrategy()

    policy = strategy.model_policy

    # 2. Section override check (section_specialized policy)
    if policy == ModelPolicy.SECTION_SPECIALIZED.value:
        override_spec_id = _get_section_override(strategy, task_category)
        if override_spec_id:
            spec = db.get(ModelSpec, override_spec_id)
            if spec and spec.is_active:
                return spec
        # Fall through to best_of_breed behavior

    # 3. Determine candidate pool based on policy
    provider_filter: Optional[str] = None
    if policy == ModelPolicy.SINGLE_PROVIDER.value:
        provider_filter = strategy.preferred_provider
    elif policy == ModelPolicy.RANDOM_EXPLORATION.value:
        # Random exploration: pick from all candidates with exploration-style weighting
        candidates = _get_active_specs_for_category(db, task_category)
        if candidates:
            return _pick_exploration_spec(db, candidates, task_category, corps_id, rng)
        return _fallback_to_tier(db, agent_definition)

    # 4. Exploration vs exploitation roll
    candidates = _get_active_specs_for_category(db, task_category, provider=provider_filter)
    if not candidates:
        return _fallback_to_tier(db, agent_definition)

    roll = rng.random()
    if roll < strategy.exploration_rate:
        # Explore: pick a less-tested spec
        spec = _pick_exploration_spec(db, candidates, task_category, corps_id, rng)
        if spec:
            return spec

    # 5. Exploit: use the best-performing spec
    min_attempts = _WELL_TESTED_THRESHOLD if strategy.risk_tolerance < 0.5 else 1
    best = get_best_spec_for_task(db, task_category, corps_id=corps_id, min_attempts=min_attempts)

    if best and best.is_active:
        # Check provider filter
        if provider_filter and best.provider != provider_filter:
            # Best spec doesn't match provider constraint — find best within provider
            best = _best_spec_for_provider(db, task_category, provider_filter, corps_id, min_attempts)

        if best:
            return best

    # 6. Risk tolerance gate: if low risk and nothing well-tested, fall back to tier
    if strategy.risk_tolerance < 0.5:
        return _fallback_to_tier(db, agent_definition)

    # High risk tolerance: pick any matching candidate
    if candidates:
        return rng.choice(candidates)

    return _fallback_to_tier(db, agent_definition)


def _best_spec_for_provider(
    db: Session,
    task_category: str,
    provider: str,
    corps_id: Optional[str],
    min_attempts: int,
) -> Optional[ModelSpec]:
    """Find best spec restricted to a specific provider."""
    q = (
        db.query(ModelSpecPerformance)
        .join(ModelSpec, ModelSpec.id == ModelSpecPerformance.model_spec_id)
        .filter(
            ModelSpecPerformance.task_category == task_category,
            ModelSpecPerformance.total_attempts >= min_attempts,
            ModelSpec.is_active.is_(True),
            ModelSpec.provider == provider,
        )
    )
    if corps_id is not None:
        q = q.filter(ModelSpecPerformance.corps_id == corps_id)
    else:
        q = q.filter(ModelSpecPerformance.corps_id.is_(None))

    perf = q.order_by(ModelSpecPerformance.avg_score.desc()).first()
    if perf:
        return db.get(ModelSpec, perf.model_spec_id)
    return None


def _fallback_to_tier(db: Session, agent_definition: AgentDefinition) -> Optional[ModelSpec]:
    """Try to find a ModelSpec that matches the agent's existing ModelTier.

    Returns None if no matching spec found — the caller can then use
    the raw ModelTier enum directly.
    """
    tier = agent_definition.model_tier
    patterns = _TIER_MODEL_PATTERNS.get(tier, [])

    for pattern in patterns:
        spec = (
            db.query(ModelSpec)
            .filter(
                ModelSpec.is_active.is_(True),
                ModelSpec.model_id.contains(pattern),
                ModelSpec.provider == "anthropic",
            )
            .first()
        )
        if spec:
            return spec

    return None
