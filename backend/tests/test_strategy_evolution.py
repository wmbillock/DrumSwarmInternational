"""Tests for strategy evolution — season-based strategy proposals."""

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
import backend.models  # noqa: F401

from backend.models.corps import Corps
from backend.models.corps_strategy import CorpsStrategy, ModelPolicy
from backend.models.model_spec import ModelSpec
from backend.models.model_spec_performance import ModelSpecPerformance
from backend.services.model_spec_service import record_model_spec_outcome
from backend.services.offseason_proposals import (
    Proposal,
    apply_proposals,
    create_proposals_file,
    load_proposals,
)
from backend.services.strategy_evolution import generate_strategy_proposals


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _make_corps(db, corps_id=None, name="Test Corps"):
    cid = corps_id or str(uuid.uuid4())
    corps = Corps(id=cid, name=name)
    db.add(corps)
    db.flush()
    return cid


def _make_strategy(db, corps_id, policy="best_of_breed", provider=None,
                   risk=0.5, exploration=0.1, section_overrides=None):
    strategy = CorpsStrategy(
        corps_id=corps_id,
        model_policy=policy,
        preferred_provider=provider,
        risk_tolerance=risk,
        exploration_rate=exploration,
        adaptation_style="model_swap",
        section_overrides=section_overrides,
    )
    db.add(strategy)
    db.flush()
    return strategy


def _make_spec(db, name, provider="anthropic", model_id="claude-sonnet-4-5",
               categories="general"):
    spec = ModelSpec(
        name=name, provider=provider, model_id=model_id,
        task_categories=categories,
    )
    db.add(spec)
    db.flush()
    return spec


def _seed_performance(db, spec_id, category, score, count=5, corps_id=None):
    """Record multiple outcomes to build up performance stats."""
    for _ in range(count):
        record_model_spec_outcome(
            db, spec_id, category, score=score, success=True,
            corps_id=corps_id,
        )


def _make_standings(corps_ids_ranked):
    """Create standings_results from an ordered list of corps_ids (best first)."""
    return [
        {"corps_id": cid, "rank": i + 1}
        for i, cid in enumerate(corps_ids_ranked)
    ]


class TestStrategyProposalForUnderperformer:
    def test_underperformer_gets_policy_change_proposal(self, db):
        """A corps below median with single_provider and weak categories
        gets a proposal to switch policy."""
        # 4 corps: top_a, top_b at ranks 1-2; weak_c, weak_d at ranks 3-4
        top_a = _make_corps(db, "top-a", "Top A")
        top_b = _make_corps(db, "top-b", "Top B")
        weak_c = _make_corps(db, "weak-c", "Weak C")
        weak_d = _make_corps(db, "weak-d", "Weak D")

        # weak_c uses single_provider anthropic
        _make_strategy(db, weak_c, policy="single_provider",
                       provider="anthropic", exploration=0.05)
        _make_strategy(db, weak_d, policy="best_of_breed", exploration=0.05)
        _make_strategy(db, top_a, policy="best_of_breed", exploration=0.3)
        _make_strategy(db, top_b, policy="best_of_breed", exploration=0.3)

        # Create specs from different providers
        anthropic_spec = _make_spec(db, "anthropic-model", provider="anthropic",
                                    categories="frontend")
        ollama_spec = _make_spec(db, "ollama-model", provider="ollama",
                                 model_id="deepseek-coder-v2:16b",
                                 categories="frontend")

        # Global performance: ollama is much better at frontend
        _seed_performance(db, ollama_spec.id, "frontend", score=90.0, corps_id=None)
        _seed_performance(db, anthropic_spec.id, "frontend", score=65.0, corps_id=None)

        # weak_c's corps-specific performance: bad at frontend
        _seed_performance(db, anthropic_spec.id, "frontend", score=55.0, corps_id=weak_c)

        standings = _make_standings([top_a, top_b, weak_c, weak_d])

        proposals = generate_strategy_proposals(db, "season-1", standings)

        # weak_c should get a policy change proposal
        weak_c_proposals = [p for p in proposals if p.corps_id == weak_c]
        policy_changes = [
            p for p in weak_c_proposals
            if "model_policy" in p.changes
        ]
        assert len(policy_changes) >= 1
        change = policy_changes[0]
        assert change.proposal_type == "strategy_change"
        # Should propose section_specialized or best_of_breed
        assert change.changes["model_policy"] in (
            ModelPolicy.SECTION_SPECIALIZED.value,
            ModelPolicy.BEST_OF_BREED.value,
        )


class TestNoProposalForTopCorps:
    def test_top_corps_no_improvement_proposal(self, db):
        """Top-25% corps don't get policy-change or exploration-increase proposals.
        They only get consolidation proposals (exploration decrease)."""
        top = _make_corps(db, "top-1", "Top One")
        mid = _make_corps(db, "mid-1", "Mid One")
        bot_a = _make_corps(db, "bot-a", "Bot A")
        bot_b = _make_corps(db, "bot-b", "Bot B")

        # top uses single_provider — should NOT get a policy change proposal
        _make_strategy(db, top, policy="single_provider", provider="anthropic",
                       exploration=0.02)
        _make_strategy(db, mid, policy="best_of_breed", exploration=0.1)
        _make_strategy(db, bot_a, policy="best_of_breed", exploration=0.1)
        _make_strategy(db, bot_b, policy="best_of_breed", exploration=0.1)

        spec = _make_spec(db, "some-spec", categories="backend")
        _seed_performance(db, spec.id, "backend", score=80.0, corps_id=None)
        _seed_performance(db, spec.id, "backend", score=90.0, corps_id=top)

        standings = _make_standings([top, mid, bot_a, bot_b])
        proposals = generate_strategy_proposals(db, "season-1", standings)

        top_proposals = [p for p in proposals if p.corps_id == top]
        # No policy change or exploration increase for top corps
        policy_changes = [p for p in top_proposals if "model_policy" in p.changes]
        exploration_increases = [
            p for p in top_proposals
            if "exploration_rate" in p.changes
            and p.changes["exploration_rate"] > 0.02
        ]
        assert len(policy_changes) == 0
        assert len(exploration_increases) == 0

    def test_top_corps_gets_consolidation_if_best_of_breed(self, db):
        """Top-25% corps using best_of_breed with high exploration gets
        a consolidation proposal (decrease exploration)."""
        top = _make_corps(db, "top-consolidate", "Top Consolidate")
        bot = _make_corps(db, "bot-1", "Bot One")

        _make_strategy(db, top, policy="best_of_breed", exploration=0.3)
        _make_strategy(db, bot, policy="best_of_breed", exploration=0.1)

        spec = _make_spec(db, "spec-1", categories="backend")
        _seed_performance(db, spec.id, "backend", score=80.0, corps_id=None)

        standings = _make_standings([top, bot])
        proposals = generate_strategy_proposals(db, "season-1", standings)

        top_proposals = [p for p in proposals if p.corps_id == top]
        consolidation = [
            p for p in top_proposals
            if "exploration_rate" in p.changes
            and p.changes["exploration_rate"] < 0.3
        ]
        assert len(consolidation) == 1
        assert consolidation[0].changes["exploration_rate"] == pytest.approx(0.2)


class TestApplyStrategyProposalUpdatesDb:
    def test_apply_strategy_proposal_updates_db(self, db, tmp_path):
        """apply_proposals with strategy_change updates the CorpsStrategy row."""
        corps_id = _make_corps(db, "apply-test", "Apply Test")
        _make_strategy(db, corps_id, policy="single_provider",
                       provider="anthropic", exploration=0.05)

        # Create and write a strategy_change proposal
        season_dir = tmp_path / "seasons" / "s1" / "offseason"
        season_dir.mkdir(parents=True, exist_ok=True)
        proposals = [
            Proposal(
                proposal_type="strategy_change",
                corps_id=corps_id,
                description="Switch to best_of_breed",
                changes={
                    "model_policy": "best_of_breed",
                    "exploration_rate": 0.2,
                },
            ),
        ]
        create_proposals_file(tmp_path, "s1", proposals)

        # Apply
        corps_dir = tmp_path / "corps"
        corps_dir.mkdir()
        pool_dir = tmp_path / "pool"
        pool_dir.mkdir()
        audit = apply_proposals(
            tmp_path, "s1", corps_dir, pool_dir, apply=True, db=db,
        )

        assert len(audit) == 1
        assert audit[0]["result"] == "applied"

        # Verify DB was updated
        strategy = (
            db.query(CorpsStrategy)
            .filter(CorpsStrategy.corps_id == corps_id)
            .first()
        )
        assert strategy.model_policy == "best_of_breed"
        assert strategy.exploration_rate == pytest.approx(0.2)

    def test_apply_strategy_change_without_db_errors(self, tmp_path):
        """strategy_change proposal without db session returns error."""
        season_dir = tmp_path / "seasons" / "s1" / "offseason"
        season_dir.mkdir(parents=True, exist_ok=True)
        proposals = [
            Proposal(
                proposal_type="strategy_change",
                corps_id="no-db-corps",
                description="Test",
                changes={"model_policy": "best_of_breed"},
            ),
        ]
        create_proposals_file(tmp_path, "s1", proposals)

        corps_dir = tmp_path / "corps"
        corps_dir.mkdir()
        pool_dir = tmp_path / "pool"
        pool_dir.mkdir()
        audit = apply_proposals(
            tmp_path, "s1", corps_dir, pool_dir, apply=True, db=None,
        )

        assert audit[0]["result"] == "error"
        assert "db session" in audit[0]["error"]


class TestExplorationRateIncreaseProposed:
    def test_exploration_rate_increase_proposed(self, db):
        """An underperforming corps with low exploration gets a rate-increase proposal."""
        top = _make_corps(db, "top-ex", "Top")
        weak = _make_corps(db, "weak-ex", "Weak")

        _make_strategy(db, top, policy="best_of_breed", exploration=0.3)
        _make_strategy(db, weak, policy="best_of_breed", exploration=0.05)

        spec = _make_spec(db, "spec-ex", categories="backend")
        _seed_performance(db, spec.id, "backend", score=85.0, corps_id=None)
        # weak corps performs well below league average
        _seed_performance(db, spec.id, "backend", score=60.0, corps_id=weak)

        standings = _make_standings([top, weak])
        proposals = generate_strategy_proposals(db, "season-1", standings)

        weak_proposals = [p for p in proposals if p.corps_id == weak]
        rate_increases = [
            p for p in weak_proposals
            if "exploration_rate" in p.changes
        ]
        assert len(rate_increases) == 1
        assert rate_increases[0].changes["exploration_rate"] == pytest.approx(0.15)
        assert rate_increases[0].proposal_type == "strategy_change"


class TestSectionOverrideSwapProposed:
    def test_section_override_swap_proposed(self, db):
        """When a section override spec underperforms, propose swapping it
        for the league-best spec in that category."""
        top = _make_corps(db, "top-so", "Top")
        weak = _make_corps(db, "weak-so", "Weak")

        # Create two specs
        bad_spec = _make_spec(db, "bad-override", provider="ollama",
                              model_id="bad-v1", categories="frontend")
        good_spec = _make_spec(db, "good-global", provider="anthropic",
                               model_id="good-v1", categories="frontend")

        # Global: good_spec is the best
        _seed_performance(db, good_spec.id, "frontend", score=92.0, corps_id=None)
        _seed_performance(db, bad_spec.id, "frontend", score=60.0, corps_id=None)

        # weak corps has bad_spec as frontend override and scores poorly
        overrides = json.dumps({"frontend": bad_spec.id})
        _make_strategy(db, weak, policy="section_specialized",
                       section_overrides=overrides, exploration=0.1)
        _make_strategy(db, top, policy="best_of_breed", exploration=0.3)

        _seed_performance(db, bad_spec.id, "frontend", score=50.0, corps_id=weak)

        standings = _make_standings([top, weak])
        proposals = generate_strategy_proposals(db, "season-1", standings)

        weak_proposals = [p for p in proposals if p.corps_id == weak]
        override_swaps = [
            p for p in weak_proposals
            if "section_overrides" in p.changes
        ]
        assert len(override_swaps) >= 1
        swap = override_swaps[0]
        assert swap.proposal_type == "strategy_change"
        new_overrides = json.loads(swap.changes["section_overrides"])
        assert new_overrides["frontend"] == good_spec.id


class TestEdgeCases:
    def test_empty_standings_returns_empty(self, db):
        assert generate_strategy_proposals(db, "s1", []) == []

    def test_single_corps_returns_empty(self, db):
        cid = _make_corps(db)
        _make_strategy(db, cid)
        assert generate_strategy_proposals(db, "s1", [{"corps_id": cid, "rank": 1}]) == []

    def test_corps_without_strategy_skipped(self, db):
        """Corps without a CorpsStrategy row are silently skipped."""
        a = _make_corps(db, "has-strat", "A")
        b = _make_corps(db, "no-strat", "B")
        _make_strategy(db, a, policy="best_of_breed", exploration=0.3)
        # b has no strategy

        spec = _make_spec(db, "spec", categories="backend")
        _seed_performance(db, spec.id, "backend", score=80.0, corps_id=None)

        standings = _make_standings([a, b])
        # Should not raise
        proposals = generate_strategy_proposals(db, "s1", standings)
        # No proposals for corps without strategy
        b_proposals = [p for p in proposals if p.corps_id == b]
        assert len(b_proposals) == 0
