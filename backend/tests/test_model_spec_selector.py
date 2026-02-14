"""Tests for model spec selector — strategy-driven model selection."""

import json
import random
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
import backend.models  # noqa: F401

from backend.models.agent_definition import AgentDefinition, ModelTier
from backend.models.corps import Corps
from backend.models.corps_strategy import CorpsStrategy
from backend.models.model_spec import ModelSpec
from backend.services.model_spec_service import record_model_spec_outcome
from backend.services.model_spec_selector import (
    model_spec_to_model_tier,
    model_spec_to_provider_kwargs,
    select_model_spec,
)


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


def _make_corps(db, name="Test Corps"):
    corps = Corps(id=str(uuid.uuid4()), name=name)
    db.add(corps)
    db.flush()
    return corps.id


def _make_spec(db, name, provider="anthropic", model_id="claude-sonnet-4-5", categories="general"):
    spec = ModelSpec(name=name, provider=provider, model_id=model_id, task_categories=categories)
    db.add(spec)
    db.flush()
    return spec


def _make_agent_def(db, role="performer", tier=ModelTier.SONNET, corps_id=None):
    defn = AgentDefinition(
        role=role,
        system_prompt="test prompt",
        model_tier=tier,
        corps_id=corps_id,
    )
    db.add(defn)
    db.flush()
    return defn


def _make_strategy(db, corps_id, policy="best_of_breed", provider=None,
                   risk=0.5, exploration=0.1, adaptation="prompt_only",
                   section_overrides=None):
    strategy = CorpsStrategy(
        corps_id=corps_id,
        model_policy=policy,
        preferred_provider=provider,
        risk_tolerance=risk,
        exploration_rate=exploration,
        adaptation_style=adaptation,
        section_overrides=section_overrides,
    )
    db.add(strategy)
    db.flush()
    return strategy


class TestSingleProviderFilter:
    def test_single_provider_filters_correctly(self, db):
        """single_provider policy only returns specs from preferred_provider."""
        corps_id = _make_corps(db)
        _make_strategy(db, corps_id, policy="single_provider", provider="anthropic",
                       risk=0.5, exploration=0.0)

        anthropic_spec = _make_spec(db, "anthropic-model", provider="anthropic",
                                    model_id="claude-sonnet-4-5", categories="frontend")
        ollama_spec = _make_spec(db, "ollama-model", provider="ollama",
                                 model_id="deepseek-coder-v2:16b", categories="frontend")

        # Give ollama a much higher score
        for _ in range(5):
            record_model_spec_outcome(db, ollama_spec.id, "frontend", score=99.0, success=True)
            record_model_spec_outcome(db, anthropic_spec.id, "frontend", score=70.0, success=True)

        agent_def = _make_agent_def(db, corps_id=corps_id)
        rng = random.Random(42)

        result = select_model_spec(db, corps_id, "frontend", agent_def, rng=rng)
        assert result is not None
        assert result.provider == "anthropic"
        assert result.id == anthropic_spec.id


class TestExplorationRate:
    def test_exploration_rate_triggers(self, db):
        """When exploration roll wins, an untested spec is chosen over the best-tested one."""
        corps_id = _make_corps(db)
        # High exploration rate so it always explores
        _make_strategy(db, corps_id, policy="best_of_breed", exploration=1.0, risk=0.5)

        tested_spec = _make_spec(db, "tested", model_id="tested-v1", categories="backend")
        untested_spec = _make_spec(db, "untested", model_id="untested-v1", categories="backend")

        # Give tested_spec lots of data
        for _ in range(20):
            record_model_spec_outcome(db, tested_spec.id, "backend", score=90.0, success=True)
        # untested_spec has zero data → higher exploration weight

        agent_def = _make_agent_def(db, corps_id=corps_id)

        # Run selection many times and verify the untested spec gets picked
        untested_chosen = 0
        for seed in range(50):
            rng = random.Random(seed)
            result = select_model_spec(db, corps_id, "backend", agent_def, rng=rng)
            if result and result.id == untested_spec.id:
                untested_chosen += 1

        # With exploration=1.0, untested spec (weight 1.0) vs tested (weight ~0.048)
        # should be chosen most of the time
        assert untested_chosen > 25, f"Untested only chosen {untested_chosen}/50 times"


class TestExploitationPicksBest:
    def test_exploitation_picks_best_score(self, db):
        """With exploration=0, the highest-scoring spec is always chosen."""
        corps_id = _make_corps(db)
        _make_strategy(db, corps_id, policy="best_of_breed", exploration=0.0, risk=0.5)

        good_spec = _make_spec(db, "good", model_id="good-v1", categories="testing")
        bad_spec = _make_spec(db, "bad", model_id="bad-v1", categories="testing")

        for _ in range(5):
            record_model_spec_outcome(db, good_spec.id, "testing", score=90.0, success=True)
            record_model_spec_outcome(db, bad_spec.id, "testing", score=40.0, success=True)

        agent_def = _make_agent_def(db, corps_id=corps_id)

        for seed in range(10):
            rng = random.Random(seed)
            result = select_model_spec(db, corps_id, "testing", agent_def, rng=rng)
            assert result is not None
            assert result.id == good_spec.id


class TestSectionOverride:
    def test_section_override_takes_precedence(self, db):
        """section_specialized policy returns the overridden spec directly."""
        corps_id = _make_corps(db)
        override_spec = _make_spec(db, "override-spec", model_id="override-v1",
                                   categories="frontend")
        other_spec = _make_spec(db, "other-spec", model_id="other-v1",
                                categories="frontend")

        # Give other_spec a great score
        for _ in range(10):
            record_model_spec_outcome(db, other_spec.id, "frontend", score=99.0, success=True)

        overrides_json = json.dumps({"frontend": override_spec.id})
        _make_strategy(db, corps_id, policy="section_specialized",
                       section_overrides=overrides_json, exploration=0.0, risk=0.5)

        agent_def = _make_agent_def(db, corps_id=corps_id)
        rng = random.Random(42)

        result = select_model_spec(db, corps_id, "frontend", agent_def, rng=rng)
        assert result is not None
        assert result.id == override_spec.id

    def test_section_override_falls_through_for_unmatched_category(self, db):
        """When section_overrides doesn't cover this category, fall through to best_of_breed."""
        corps_id = _make_corps(db)
        override_spec = _make_spec(db, "override-only-frontend", model_id="of-v1",
                                   categories="frontend")
        backend_spec = _make_spec(db, "backend-best", model_id="bb-v1",
                                  categories="backend")

        overrides_json = json.dumps({"frontend": override_spec.id})
        _make_strategy(db, corps_id, policy="section_specialized",
                       section_overrides=overrides_json, exploration=0.0, risk=0.5)

        for _ in range(5):
            record_model_spec_outcome(db, backend_spec.id, "backend", score=85.0, success=True)

        agent_def = _make_agent_def(db, corps_id=corps_id)
        rng = random.Random(42)

        result = select_model_spec(db, corps_id, "backend", agent_def, rng=rng)
        assert result is not None
        assert result.id == backend_spec.id


class TestFallbackToModelTier:
    def test_fallback_to_model_tier(self, db):
        """No strategy, no performance data → falls back to matching ModelTier."""
        # Create an anthropic sonnet spec so tier fallback can find it
        sonnet_spec = _make_spec(db, "sonnet-fallback", provider="anthropic",
                                 model_id="claude-sonnet-4-5-20250929", categories="general")

        agent_def = _make_agent_def(db, tier=ModelTier.SONNET)

        rng = random.Random(42)
        result = select_model_spec(db, None, "unknown_category", agent_def, rng=rng)
        # Should fall back to a spec that matches the sonnet tier
        assert result is not None
        assert "sonnet" in result.model_id

    def test_fallback_returns_none_when_no_specs(self, db):
        """With zero specs in DB, returns None so caller can use raw ModelTier."""
        agent_def = _make_agent_def(db, tier=ModelTier.OPUS)
        rng = random.Random(42)

        result = select_model_spec(db, None, "anything", agent_def, rng=rng)
        assert result is None


class TestRiskTolerance:
    def test_risk_tolerance_rejects_untested_spec(self, db):
        """Low risk_tolerance + no well-tested specs → falls back to tier."""
        corps_id = _make_corps(db)
        _make_strategy(db, corps_id, policy="best_of_breed", exploration=0.0,
                       risk=0.1)  # very conservative

        # Create a spec with only 1 attempt (below _WELL_TESTED_THRESHOLD=3)
        new_spec = _make_spec(db, "barely-tested", model_id="bt-v1", categories="frontend")
        record_model_spec_outcome(db, new_spec.id, "frontend", score=95.0, success=True)

        # Create a sonnet spec for tier fallback
        sonnet = _make_spec(db, "sonnet-safe", provider="anthropic",
                            model_id="claude-sonnet-4-5-20250929", categories="general")

        agent_def = _make_agent_def(db, corps_id=corps_id, tier=ModelTier.SONNET)
        rng = random.Random(42)

        result = select_model_spec(db, corps_id, "frontend", agent_def, rng=rng)
        # With risk_tolerance=0.1 (< 0.5), min_attempts=3, and only 1 attempt,
        # the barely-tested spec won't qualify → falls back to tier
        assert result is not None
        assert result.id == sonnet.id

    def test_high_risk_allows_untested_spec(self, db):
        """High risk_tolerance allows specs with few attempts."""
        corps_id = _make_corps(db)
        _make_strategy(db, corps_id, policy="best_of_breed", exploration=0.0,
                       risk=0.9)  # very aggressive

        new_spec = _make_spec(db, "new-hotness", model_id="nh-v1", categories="frontend")
        record_model_spec_outcome(db, new_spec.id, "frontend", score=95.0, success=True)

        agent_def = _make_agent_def(db, corps_id=corps_id, tier=ModelTier.SONNET)
        rng = random.Random(42)

        result = select_model_spec(db, corps_id, "frontend", agent_def, rng=rng)
        # With risk_tolerance=0.9 (>= 0.5), min_attempts=1, so spec qualifies
        assert result is not None
        assert result.id == new_spec.id


class _FakeSpec:
    """Lightweight stand-in for ModelSpec — avoids SQLAlchemy instrumentation."""
    def __init__(self, model_id, provider="anthropic", lora_id=None, adapter_path=None):
        self.model_id = model_id
        self.provider = provider
        self.lora_id = lora_id
        self.adapter_path = adapter_path


class TestModelSpecToModelTier:
    def test_opus_mapping(self):
        assert model_spec_to_model_tier(_FakeSpec("claude-opus-4-5-20251101")) == ModelTier.OPUS

    def test_sonnet_mapping(self):
        assert model_spec_to_model_tier(_FakeSpec("claude-sonnet-4-5-20250929")) == ModelTier.SONNET

    def test_haiku_mapping(self):
        assert model_spec_to_model_tier(_FakeSpec("claude-haiku-4-5-20251001")) == ModelTier.HAIKU

    def test_deepseek_maps_to_sonnet(self):
        assert model_spec_to_model_tier(_FakeSpec("deepseek-coder-v2:16b")) == ModelTier.SONNET

    def test_unknown_defaults_to_sonnet(self):
        assert model_spec_to_model_tier(_FakeSpec("some-custom-model-v3")) == ModelTier.SONNET


class TestModelSpecToProviderKwargs:
    def test_basic_kwargs(self):
        spec = _FakeSpec("claude-sonnet-4-5", provider="anthropic")
        result = model_spec_to_provider_kwargs(spec)
        assert result == {"provider": "anthropic", "model_id": "claude-sonnet-4-5"}

    def test_kwargs_with_lora(self):
        spec = _FakeSpec(
            "deepseek-coder-v2:16b",
            provider="ollama",
            lora_id="react-lora-v3",
            adapter_path="/models/loras/react-v3.safetensors",
        )
        result = model_spec_to_provider_kwargs(spec)
        assert result == {
            "provider": "ollama",
            "model_id": "deepseek-coder-v2:16b",
            "lora_id": "react-lora-v3",
            "adapter_path": "/models/loras/react-v3.safetensors",
        }


class TestRandomExplorationPolicy:
    def test_random_exploration_uses_all_candidates(self, db):
        """random_exploration policy picks from all active specs weighted by novelty."""
        corps_id = _make_corps(db)
        _make_strategy(db, corps_id, policy="random_exploration", risk=1.0, exploration=1.0)

        specs = [
            _make_spec(db, f"spec-{i}", model_id=f"model-{i}", categories="backend")
            for i in range(5)
        ]

        agent_def = _make_agent_def(db, corps_id=corps_id)

        chosen_ids = set()
        for seed in range(100):
            rng = random.Random(seed)
            result = select_model_spec(db, corps_id, "backend", agent_def, rng=rng)
            if result:
                chosen_ids.add(result.id)

        # With 5 specs and 100 trials, all should be chosen at least once
        assert len(chosen_ids) == 5
