"""Tests for ModelSpec and CorpsStrategy models."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.database import Base
import backend.models  # noqa: F401 — ensure all models registered

from backend.models.model_spec import ModelSpec, ModelSpecCapability
from backend.models.corps_strategy import (
    AdaptationStyle,
    CorpsStrategy,
    ModelPolicy,
)
from backend.models.corps import Corps


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


def _make_corps(db, corps_id=None):
    """Helper: insert a minimal corps row and return its id."""
    cid = corps_id or str(uuid.uuid4())
    corps = Corps(id=cid, name=f"Test Corps {cid[:8]}")
    db.add(corps)
    db.flush()
    return cid


class TestCreateModelSpec:
    def test_create_model_spec(self, db):
        spec = ModelSpec(
            name="claude-sonnet-frontend",
            provider="anthropic",
            model_id="claude-sonnet-4-5-20250929",
            task_categories="frontend,react,css",
        )
        db.add(spec)
        db.flush()

        fetched = db.get(ModelSpec, spec.id)
        assert fetched is not None
        assert fetched.name == "claude-sonnet-frontend"
        assert fetched.provider == "anthropic"
        assert fetched.model_id == "claude-sonnet-4-5-20250929"
        assert fetched.is_active is True
        assert fetched.lora_id is None
        assert fetched.adapter_path is None
        assert fetched.categories_list == ["frontend", "react", "css"]

    def test_create_with_lora(self, db):
        spec = ModelSpec(
            name="deepseek-react-lora",
            provider="ollama",
            model_id="deepseek-coder-v2:16b",
            lora_id="react-specialist-v3",
            adapter_path="/models/loras/react-v3.safetensors",
            task_categories="frontend",
        )
        db.add(spec)
        db.flush()

        fetched = db.get(ModelSpec, spec.id)
        assert fetched.lora_id == "react-specialist-v3"
        assert fetched.adapter_path == "/models/loras/react-v3.safetensors"

    def test_empty_categories(self, db):
        spec = ModelSpec(
            name="bare-model",
            provider="openai",
            model_id="gpt-4o",
        )
        db.add(spec)
        db.flush()
        assert spec.categories_list == []


class TestCreateCorpsStrategy:
    def test_create_corps_strategy(self, db):
        corps_id = _make_corps(db)
        strategy = CorpsStrategy(
            corps_id=corps_id,
            model_policy=ModelPolicy.BEST_OF_BREED.value,
            preferred_provider="anthropic",
            risk_tolerance=0.3,
            exploration_rate=0.2,
            adaptation_style=AdaptationStyle.MODEL_SWAP.value,
        )
        db.add(strategy)
        db.flush()

        fetched = db.get(CorpsStrategy, strategy.id)
        assert fetched is not None
        assert fetched.corps_id == corps_id
        assert fetched.model_policy == ModelPolicy.BEST_OF_BREED.value
        assert fetched.preferred_provider == "anthropic"
        assert fetched.risk_tolerance == 0.3
        assert fetched.exploration_rate == 0.2
        assert fetched.adaptation_style == AdaptationStyle.MODEL_SWAP.value

    def test_defaults(self, db):
        corps_id = _make_corps(db)
        strategy = CorpsStrategy(
            corps_id=corps_id,
            model_policy=ModelPolicy.SINGLE_PROVIDER.value,
        )
        db.add(strategy)
        db.flush()

        assert strategy.risk_tolerance == 0.5
        assert strategy.exploration_rate == 0.1
        assert strategy.adaptation_style == AdaptationStyle.PROMPT_ONLY.value
        assert strategy.preferred_provider is None
        assert strategy.section_overrides is None


class TestCorpsStrategyUniquePerCorps:
    def test_second_strategy_raises(self, db):
        corps_id = _make_corps(db)
        s1 = CorpsStrategy(
            corps_id=corps_id,
            model_policy=ModelPolicy.SINGLE_PROVIDER.value,
        )
        db.add(s1)
        db.flush()

        s2 = CorpsStrategy(
            corps_id=corps_id,
            model_policy=ModelPolicy.RANDOM_EXPLORATION.value,
        )
        db.add(s2)
        with pytest.raises(IntegrityError):
            db.flush()


class TestModelSpecDeactivation:
    def test_deactivate(self, db):
        spec = ModelSpec(
            name="to-deactivate",
            provider="anthropic",
            model_id="claude-haiku-4-5-20251001",
        )
        db.add(spec)
        db.flush()
        assert spec.is_active is True

        spec.is_active = False
        db.flush()

        fetched = db.get(ModelSpec, spec.id)
        assert fetched.is_active is False


class TestModelSpecCapabilityEnum:
    def test_enum_values(self):
        assert ModelSpecCapability.GENERAL.value == "general"
        assert ModelSpecCapability.FRONTEND.value == "frontend"
        assert ModelSpecCapability.IMAGE_GEN.value == "image_gen"
        assert len(ModelSpecCapability) == 7
