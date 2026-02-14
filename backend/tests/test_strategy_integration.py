"""Integration tests for the full strategy evolution feedback loop.

Validates: task → model selection → scoring → performance tracking → strategy evolution.
"""

import json
import random

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import Base
import backend.models  # noqa: F401

from backend.models.corps import Corps
from backend.models.corps_strategy import CorpsStrategy, ModelPolicy
from backend.models.model_spec import ModelSpec
from backend.models.model_spec_performance import ModelSpecPerformance
from backend.models.score import JudgeType
from backend.services.model_spec_selector import select_model_spec
from backend.services.model_spec_service import (
    get_best_spec_for_task,
    get_spec_leaderboard,
    record_model_spec_outcome,
)
from backend.services.offseason_proposals import (
    Proposal,
    apply_proposals,
    create_proposals_file,
    load_proposals,
)
from backend.services.scoring_engine import compute_standings
from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS
from backend.services.season_persistence import create_season
from backend.services.strategy_evolution import generate_strategy_proposals
from backend.services.lifecycle_transitions import SeasonPhase
from backend.services.yaml_util import atomic_write, safe_dump_yaml


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    session = sf()
    try:
        yield session
    finally:
        session.close()


def _make_spec(db: Session, name: str, provider: str, model_id: str) -> ModelSpec:
    spec = ModelSpec(
        name=name,
        provider=provider,
        model_id=model_id,
        task_categories="frontend,backend,testing",
    )
    db.add(spec)
    db.flush()
    return spec


def _make_corps(db: Session, corps_id: str, name: str) -> Corps:
    corps = Corps(id=corps_id, name=name)
    db.add(corps)
    db.flush()
    return corps


def _make_strategy(
    db: Session,
    corps_id: str,
    policy: str = "best_of_breed",
    provider: str | None = None,
    exploration: float = 0.1,
    risk: float = 0.5,
) -> CorpsStrategy:
    strategy = CorpsStrategy(
        corps_id=corps_id,
        model_policy=policy,
        preferred_provider=provider,
        exploration_rate=exploration,
        risk_tolerance=risk,
        adaptation_style="model_swap",
    )
    db.add(strategy)
    db.flush()
    return strategy


def _seed_performance(
    db: Session,
    spec: ModelSpec,
    category: str,
    score: float,
    n: int = 8,
    corps_id: str | None = None,
) -> None:
    """Seed performance data with slight jitter for realism."""
    rng = random.Random(42)
    for _ in range(n):
        jitter = rng.uniform(-1.5, 1.5)
        record_model_spec_outcome(
            db, spec.id, category, score=score + jitter,
            success=True, corps_id=corps_id,
        )
    db.flush()


def _make_standings(corps_scores: dict[str, dict[JudgeType, float]], season_id: str):
    """Build CompositeScore objects and compute standings."""
    composites = {}
    for corps_id, scores in corps_scores.items():
        raw_total = sum(scores[jt] * DEFAULT_WEIGHTS[jt] for jt in scores)
        composites[corps_id] = CompositeScore(
            caption_scores=scores,
            raw_total=raw_total,
            penalties_total=0.0,
            final_score=raw_total,
            needs_rework=False,
            needs_escalation=False,
        )
    standings = compute_standings(season_id, DEFAULT_WEIGHTS, composites)
    return standings, [
        {"corps_id": r.corps_id, "rank": r.rank, "final_score": r.final_score}
        for r in standings.results
    ]


class TestFullSeasonWithStrategyEvolution:
    """Happy path: a full season cycle produces strategy proposals for the
    underperforming corps and those proposals change the strategy when applied."""

    def test_underperformer_gets_strategy_proposal(self, db, tmp_path):
        # --- Setup: 3 specs, 3 corps, different strategies ---
        spec_a = _make_spec(db, "claude-sonnet", "anthropic", "claude-sonnet-4-5")
        spec_b = _make_spec(db, "deepseek-v2", "ollama", "deepseek-coder-v2:16b")
        spec_c = _make_spec(db, "gpt-4o", "openai", "gpt-4o")

        _make_corps(db, "alpha", "Alpha Corps")
        _make_corps(db, "beta", "Beta Corps")
        _make_corps(db, "gamma", "Gamma Corps")

        # Alpha: single_provider (anthropic), low exploration
        _make_strategy(db, "alpha", policy="single_provider",
                       provider="anthropic", exploration=0.05, risk=0.3)
        # Beta: best_of_breed, moderate exploration
        _make_strategy(db, "beta", policy="best_of_breed",
                       exploration=0.15, risk=0.6)
        # Gamma: random_exploration, high exploration
        _make_strategy(db, "gamma", policy="random_exploration",
                       exploration=0.4, risk=0.9)

        # --- Seed global performance: deepseek dominates frontend ---
        _seed_performance(db, spec_a, "frontend", 70.0)
        _seed_performance(db, spec_a, "backend", 91.0)
        _seed_performance(db, spec_b, "frontend", 93.0)
        _seed_performance(db, spec_b, "backend", 64.0)
        _seed_performance(db, spec_c, "frontend", 80.0)
        _seed_performance(db, spec_c, "backend", 79.0)

        # Alpha (single_provider anthropic) — weak at frontend
        _seed_performance(db, spec_a, "frontend", 65.0, corps_id="alpha")
        _seed_performance(db, spec_a, "backend", 90.0, corps_id="alpha")

        # Beta — uses best specs, good scores
        _seed_performance(db, spec_b, "frontend", 94.0, corps_id="beta")
        _seed_performance(db, spec_a, "backend", 89.0, corps_id="beta")

        # Gamma — random exploration, mediocre
        _seed_performance(db, spec_c, "frontend", 72.0, corps_id="gamma")
        _seed_performance(db, spec_c, "backend", 68.0, corps_id="gamma")
        db.commit()

        # --- Compute standings: beta #1, alpha #2, gamma #3 ---
        season_id = "test-season-1"
        scores = {
            "alpha": {
                JudgeType.BRASS: 72.0, JudgeType.PERCUSSION: 70.0,
                JudgeType.GUARD: 68.0, JudgeType.VISUAL: 74.0,
                JudgeType.GENERAL_EFFECT: 71.0, JudgeType.ENSEMBLE_TECHNIQUE: 69.0,
            },
            "beta": {
                JudgeType.BRASS: 90.0, JudgeType.PERCUSSION: 88.0,
                JudgeType.GUARD: 86.0, JudgeType.VISUAL: 85.0,
                JudgeType.GENERAL_EFFECT: 91.0, JudgeType.ENSEMBLE_TECHNIQUE: 87.0,
            },
            "gamma": {
                JudgeType.BRASS: 58.0, JudgeType.PERCUSSION: 55.0,
                JudgeType.GUARD: 56.0, JudgeType.VISUAL: 60.0,
                JudgeType.GENERAL_EFFECT: 62.0, JudgeType.ENSEMBLE_TECHNIQUE: 54.0,
            },
        }
        standings, results_list = _make_standings(scores, season_id)

        # Verify rank order
        rank_map = {r["corps_id"]: r["rank"] for r in results_list}
        assert rank_map["beta"] == 1
        assert rank_map["gamma"] == 3

        # --- Generate proposals ---
        proposals = generate_strategy_proposals(db, season_id, results_list)
        assert len(proposals) > 0, "Expected at least one proposal"

        # At least one proposal should target an underperformer
        corps_with_proposals = {p.corps_id for p in proposals}
        assert "gamma" in corps_with_proposals, "Gamma (rank 3) should get a proposal"

        # --- Write and load proposals from filesystem ---
        create_season(tmp_path, season_id, metadata={"season_id": season_id})
        create_proposals_file(tmp_path, season_id, proposals, phase=SeasonPhase.OFFSEASON)
        loaded = load_proposals(tmp_path, season_id)
        assert len(loaded) == len(proposals)
        for orig, loaded_p in zip(proposals, loaded):
            assert orig.corps_id == loaded_p.corps_id
            assert orig.proposal_type == loaded_p.proposal_type

        # --- Apply proposals ---
        corps_dir = tmp_path / "corps"
        for cid in ["alpha", "beta", "gamma"]:
            (corps_dir / cid).mkdir(parents=True, exist_ok=True)
            atomic_write(corps_dir / cid / "corps.yaml", safe_dump_yaml({
                "corps_id": cid, "state": "active",
            }))

        audit = apply_proposals(
            tmp_path, season_id, corps_dir, tmp_path / "talent_pool",
            apply=True, db=db,
        )
        db.commit()

        # All proposals should apply successfully
        for entry in audit:
            assert entry["result"] == "applied", f"Proposal {entry['proposal_index']} failed: {entry.get('error')}"

    def test_strategy_fields_actually_changed(self, db, tmp_path):
        """After applying proposals, the CorpsStrategy row reflects the changes."""
        spec_a = _make_spec(db, "claude-sonnet", "anthropic", "claude-sonnet-4-5")
        spec_b = _make_spec(db, "deepseek-v2", "ollama", "deepseek-coder-v2:16b")

        _make_corps(db, "weak-corps", "Weak Corps")
        strategy = _make_strategy(
            db, "weak-corps", policy="single_provider",
            provider="anthropic", exploration=0.05, risk=0.3,
        )
        original_policy = strategy.model_policy

        # deepseek beats claude globally at frontend by a wide margin
        _seed_performance(db, spec_a, "frontend", 60.0)
        _seed_performance(db, spec_b, "frontend", 95.0)
        _seed_performance(db, spec_a, "frontend", 58.0, corps_id="weak-corps")
        db.commit()

        season_id = "test-season-2"
        # 2 corps needed for proposals; weak-corps is rank 2
        _make_corps(db, "strong-corps", "Strong Corps")
        _make_strategy(db, "strong-corps", policy="best_of_breed")
        db.commit()

        results_list = [
            {"corps_id": "strong-corps", "rank": 1, "final_score": 90.0},
            {"corps_id": "weak-corps", "rank": 2, "final_score": 55.0},
        ]

        proposals = generate_strategy_proposals(db, season_id, results_list)
        weak_proposals = [p for p in proposals if p.corps_id == "weak-corps"]
        assert len(weak_proposals) > 0

        # Apply via direct proposal application
        create_season(tmp_path, season_id, metadata={"season_id": season_id})
        create_proposals_file(tmp_path, season_id, weak_proposals, phase=SeasonPhase.OFFSEASON)

        corps_dir = tmp_path / "corps"
        for cid in ["weak-corps", "strong-corps"]:
            (corps_dir / cid).mkdir(parents=True, exist_ok=True)
            atomic_write(corps_dir / cid / "corps.yaml", safe_dump_yaml({
                "corps_id": cid, "state": "active",
            }))

        apply_proposals(
            tmp_path, season_id, corps_dir, tmp_path / "talent_pool",
            apply=True, db=db,
        )
        db.commit()

        # Refresh strategy from DB
        db.expire_all()
        updated = db.query(CorpsStrategy).filter(CorpsStrategy.corps_id == "weak-corps").first()
        assert updated is not None

        # The policy should have changed (single_provider → section_specialized or best_of_breed)
        assert updated.model_policy != original_policy, (
            f"Strategy should have changed from {original_policy}"
        )

    def test_leaderboard_reflects_performance_data(self, db):
        """After recording outcomes, the leaderboard correctly ranks specs."""
        spec_a = _make_spec(db, "spec-a", "provider-a", "model-a")
        spec_b = _make_spec(db, "spec-b", "provider-b", "model-b")

        # spec_b has higher scores
        _seed_performance(db, spec_a, "frontend", 70.0)
        _seed_performance(db, spec_b, "frontend", 90.0)
        db.commit()

        leaderboard = get_spec_leaderboard(db, "frontend")
        assert len(leaderboard) == 2
        assert leaderboard[0]["name"] == "spec-b"
        assert leaderboard[0]["avg_score"] > leaderboard[1]["avg_score"]


class TestStrategyStableWhenCorpsPerformingWell:
    """Top-performing corps should NOT get disruptive proposals."""

    def test_top_corps_no_policy_change(self, db):
        """A top-ranked corps with best_of_breed and low exploration
        should not get a policy change proposal."""
        spec = _make_spec(db, "claude-sonnet", "anthropic", "claude-sonnet-4-5")

        _make_corps(db, "top-corps", "Top Corps")
        _make_corps(db, "mid-corps", "Mid Corps")
        _make_corps(db, "bot-corps", "Bot Corps")

        _make_strategy(db, "top-corps", policy="best_of_breed",
                       exploration=0.05, risk=0.3)
        _make_strategy(db, "mid-corps", policy="best_of_breed",
                       exploration=0.1, risk=0.5)
        _make_strategy(db, "bot-corps", policy="random_exploration",
                       exploration=0.4, risk=0.9)

        # Seed performance data — all decent
        _seed_performance(db, spec, "frontend", 85.0)
        _seed_performance(db, spec, "backend", 88.0)
        _seed_performance(db, spec, "frontend", 87.0, corps_id="top-corps")
        _seed_performance(db, spec, "backend", 90.0, corps_id="top-corps")
        _seed_performance(db, spec, "frontend", 80.0, corps_id="mid-corps")
        _seed_performance(db, spec, "backend", 82.0, corps_id="mid-corps")
        _seed_performance(db, spec, "frontend", 60.0, corps_id="bot-corps")
        _seed_performance(db, spec, "backend", 55.0, corps_id="bot-corps")
        db.commit()

        results_list = [
            {"corps_id": "top-corps", "rank": 1, "final_score": 92.0},
            {"corps_id": "mid-corps", "rank": 2, "final_score": 78.0},
            {"corps_id": "bot-corps", "rank": 3, "final_score": 58.0},
        ]

        proposals = generate_strategy_proposals(db, "stable-test", results_list)

        # The top corps should NOT get a policy change proposal
        top_policy_changes = [
            p for p in proposals
            if p.corps_id == "top-corps" and "model_policy" in p.changes
        ]
        assert len(top_policy_changes) == 0, (
            "Top-performing corps should not get policy change proposals"
        )

    def test_top_corps_may_get_consolidation(self, db):
        """A top-ranked corps with best_of_breed and high exploration
        may get an exploration decrease (consolidation), but not a policy change."""
        spec = _make_spec(db, "claude-sonnet", "anthropic", "claude-sonnet-4-5")

        _make_corps(db, "top-corps", "Top Corps")
        _make_corps(db, "mid-corps", "Mid Corps")
        _make_corps(db, "bot-corps", "Bot Corps")
        _make_corps(db, "last-corps", "Last Corps")

        _make_strategy(db, "top-corps", policy="best_of_breed",
                       exploration=0.3, risk=0.5)
        _make_strategy(db, "mid-corps", policy="best_of_breed",
                       exploration=0.1, risk=0.5)
        _make_strategy(db, "bot-corps", policy="single_provider",
                       provider="anthropic", exploration=0.05, risk=0.3)
        _make_strategy(db, "last-corps", policy="random_exploration",
                       exploration=0.4, risk=0.9)

        _seed_performance(db, spec, "frontend", 85.0)
        _seed_performance(db, spec, "backend", 85.0)
        _seed_performance(db, spec, "frontend", 88.0, corps_id="top-corps")
        db.commit()

        results_list = [
            {"corps_id": "top-corps", "rank": 1, "final_score": 95.0},
            {"corps_id": "mid-corps", "rank": 2, "final_score": 80.0},
            {"corps_id": "bot-corps", "rank": 3, "final_score": 65.0},
            {"corps_id": "last-corps", "rank": 4, "final_score": 50.0},
        ]

        proposals = generate_strategy_proposals(db, "consolidation-test", results_list)

        top_proposals = [p for p in proposals if p.corps_id == "top-corps"]
        if top_proposals:
            # Should only be exploration decrease, not policy change
            for p in top_proposals:
                assert "model_policy" not in p.changes, (
                    "Top corps consolidation should not change policy"
                )
                if "exploration_rate" in p.changes:
                    assert p.changes["exploration_rate"] < 0.3, (
                        "Consolidation should decrease exploration"
                    )

    def test_no_proposals_when_only_two_corps_both_close(self, db):
        """If two corps are close in score with no weak categories,
        minimal proposals should be generated."""
        spec = _make_spec(db, "claude-sonnet", "anthropic", "claude-sonnet-4-5")

        _make_corps(db, "corps-a", "Corps A")
        _make_corps(db, "corps-b", "Corps B")

        _make_strategy(db, "corps-a", policy="best_of_breed", exploration=0.1)
        _make_strategy(db, "corps-b", policy="best_of_breed", exploration=0.1)

        # Both performing near league average
        _seed_performance(db, spec, "frontend", 82.0)
        _seed_performance(db, spec, "frontend", 83.0, corps_id="corps-a")
        _seed_performance(db, spec, "frontend", 81.0, corps_id="corps-b")
        db.commit()

        results_list = [
            {"corps_id": "corps-a", "rank": 1, "final_score": 83.0},
            {"corps_id": "corps-b", "rank": 2, "final_score": 81.0},
        ]

        proposals = generate_strategy_proposals(db, "close-test", results_list)

        # Corps-b is below median but NOT below league avg by threshold
        policy_changes = [p for p in proposals if "model_policy" in p.changes]
        assert len(policy_changes) == 0, (
            "No policy changes when scores are close to league average"
        )


class TestNewModelSpecDiscoveredThroughExploration:
    """When a new model spec is added, exploration should pick it up
    and performance data should accumulate."""

    def test_exploration_selects_new_spec(self, db):
        """Random exploration policy weights untested specs higher."""
        from backend.models.agent_definition import AgentDefinition, ModelTier

        spec_old = _make_spec(db, "old-model", "anthropic", "old-model-v1")
        spec_new = _make_spec(db, "new-model", "ollama", "new-model-v1")

        _make_corps(db, "explorer", "Explorer Corps")
        _make_strategy(db, "explorer", policy="random_exploration",
                       exploration=0.9, risk=0.9)

        # Old model has lots of attempts
        _seed_performance(db, spec_old, "frontend", 80.0, n=50)
        db.commit()

        # Create a minimal agent definition for the selector
        agent_def = AgentDefinition(
            role="performer",
            model_tier=ModelTier.SONNET,
            system_prompt="test",
        )
        db.add(agent_def)
        db.flush()

        # With exploration, the selector should sometimes pick the new untested spec
        rng = random.Random(42)
        selections = set()
        for _ in range(20):
            spec = select_model_spec(
                db, "explorer", "frontend", agent_def, rng=rng,
            )
            if spec:
                selections.add(spec.name)

        assert "new-model" in selections, (
            "Exploration should discover and select untested specs"
        )

    def test_new_spec_accumulates_performance(self, db):
        """Recording outcomes for a new spec builds its performance profile."""
        spec = _make_spec(db, "brand-new", "ollama", "brand-new-v1")

        # Initially no performance data
        leaderboard = get_spec_leaderboard(db, "backend")
        assert len(leaderboard) == 0

        # Record several outcomes
        for score in [85.0, 88.0, 92.0, 80.0, 87.0]:
            record_model_spec_outcome(
                db, spec.id, "backend", score=score, success=True,
            )
        db.commit()

        leaderboard = get_spec_leaderboard(db, "backend")
        assert len(leaderboard) == 1
        assert leaderboard[0]["name"] == "brand-new"
        assert leaderboard[0]["total_attempts"] == 5
        # avg should be close to mean of [85, 88, 92, 80, 87] = 86.4
        assert 85.0 < leaderboard[0]["avg_score"] < 88.0

    def test_new_spec_overtakes_old_on_leaderboard(self, db):
        """A new spec that outperforms the old one eventually tops the leaderboard."""
        spec_old = _make_spec(db, "old-model", "anthropic", "old-model-v1")
        spec_new = _make_spec(db, "new-model", "ollama", "new-model-v1")

        # Old model: decent but not great
        _seed_performance(db, spec_old, "frontend", 75.0, n=10)

        # New model: much better scores
        _seed_performance(db, spec_new, "frontend", 95.0, n=10)
        db.commit()

        leaderboard = get_spec_leaderboard(db, "frontend")
        assert len(leaderboard) == 2
        assert leaderboard[0]["name"] == "new-model", (
            "New higher-scoring model should top the leaderboard"
        )
        assert leaderboard[0]["avg_score"] > leaderboard[1]["avg_score"]

    def test_best_spec_for_task_picks_new_winner(self, db):
        """get_best_spec_for_task returns the new spec once it has enough data."""
        spec_old = _make_spec(db, "old-model", "anthropic", "old-model-v1")
        spec_new = _make_spec(db, "new-model", "ollama", "new-model-v1")

        _seed_performance(db, spec_old, "testing", 70.0, n=10)
        _seed_performance(db, spec_new, "testing", 92.0, n=5)
        db.commit()

        best = get_best_spec_for_task(db, "testing", min_attempts=3)
        assert best is not None
        assert best.name == "new-model"
