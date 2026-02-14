"""Tests for model spec integration with agent runtime and LLM client."""

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
from backend.models.model_spec_performance import ModelSpecPerformance
from backend.services.agent_lifecycle import create_definition, spawn_session
from backend.services.agent_runtime import (
    RunStatus,
    infer_task_category,
    run_agent,
)
from backend.services.llm_client import (
    LLMResponse,
    MockLLMClient,
    MODEL_TIER_MAP,
)
from backend.services.model_spec_service import record_model_spec_outcome
from backend.services.tool_executor import ToolExecutor, ToolRegistry


CORPS_ID = "test-corps-integration"


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


def _make_registry_and_executor():
    registry = ToolRegistry()
    registry.register(
        "tuner",
        lambda value: {"in_tune": True, "value": value},
        schema={"name": "tuner", "description": "Check if value is in tune"},
    )
    return registry, ToolExecutor(registry)


def _setup_corps_with_strategy(db, policy="best_of_breed", provider=None,
                                risk=0.5, exploration=0.0):
    """Create a corps with a strategy and return corps_id."""
    corps = Corps(id=CORPS_ID, name="Integration Test Corps")
    db.add(corps)
    db.flush()

    strategy = CorpsStrategy(
        corps_id=CORPS_ID,
        model_policy=policy,
        preferred_provider=provider,
        risk_tolerance=risk,
        exploration_rate=exploration,
        adaptation_style="model_swap",
    )
    db.add(strategy)
    db.flush()
    return CORPS_ID


def _seed_spec(db, name, provider="anthropic", model_id="claude-sonnet-4-5-20250929",
               categories="general,frontend,backend"):
    spec = ModelSpec(
        name=name, provider=provider, model_id=model_id,
        task_categories=categories,
    )
    db.add(spec)
    db.flush()
    return spec


class TestAgentRuntimeUsesSpec:
    def test_agent_runtime_uses_spec_when_strategy_exists(self, db):
        """When a corps has a strategy and specs exist, the spec's model_id
        is passed to llm_client.chat() as model_override."""
        _setup_corps_with_strategy(db, policy="best_of_breed", exploration=0.0, risk=0.8)

        # Create a spec and give it enough data to be selected
        spec = _seed_spec(db, "best-frontend", model_id="custom-model-v1",
                          categories="frontend")
        for _ in range(5):
            record_model_spec_outcome(db, spec.id, "frontend", score=90.0, success=True)

        registry, executor = _make_registry_and_executor()
        client = MockLLMClient()
        client.queue_response(LLMResponse(content="React component done."))

        defn = create_definition(
            db, "performer", "You build React components.",
            model_tier=ModelTier.SONNET, tools_allowed=["tuner"],
        )
        session = spawn_session(db, defn.id, CORPS_ID)

        result = run_agent(
            db, session.id, client, executor,
            "Build a React component for the login page",
        )

        assert result.status == RunStatus.COMPLETED
        assert result.model_spec_id == spec.id
        assert result.task_category == "frontend"

        # Verify the model_override was passed to the LLM client
        assert len(client.calls) == 1
        assert client.calls[0]["model_override"] == "custom-model-v1"
        assert client.calls[0]["model_id"] == "custom-model-v1"

    def test_agent_runtime_falls_back_to_tier(self, db):
        """Without a strategy or specs, run_agent uses the tier-based model_id
        and model_override is None — identical to pre-integration behavior."""
        # No corps, no strategy, no specs
        registry, executor = _make_registry_and_executor()
        client = MockLLMClient()
        client.queue_response(LLMResponse(content="Done."))

        defn = create_definition(
            db, "performer", "You do work.",
            model_tier=ModelTier.OPUS, tools_allowed=["tuner"],
        )
        session = spawn_session(db, defn.id, "no-such-corps")

        result = run_agent(db, session.id, client, executor, "Do something")

        assert result.status == RunStatus.COMPLETED
        # No spec selected — falls back to tier
        assert result.model_spec_id is None
        assert client.calls[0]["model_override"] is None
        # model_id should be the tier-mapped value
        assert client.calls[0]["model_id"] == MODEL_TIER_MAP[ModelTier.OPUS]


class TestTaskCategoryInference:
    def test_frontend_keywords(self):
        assert infer_task_category("Build a React component with JSX") == "frontend"

    def test_backend_keywords(self):
        assert infer_task_category("Create an API endpoint for user queries") == "backend"

    def test_testing_keywords(self):
        assert infer_task_category("Write pytest tests with assert statements") == "testing"

    def test_architecture_keywords(self):
        assert infer_task_category("Design the system architecture and module structure") == "architecture"

    def test_documentation_keywords(self):
        assert infer_task_category("Write a README and docstrings for the guide") == "documentation"

    def test_default_to_general(self):
        assert infer_task_category("Do this task") == "general"

    def test_role_influences_category(self):
        # "database" is a backend keyword
        assert infer_task_category("handle the thing", role="database_admin") == "backend"

    def test_mixed_keywords_picks_highest(self):
        # More frontend keywords than backend
        desc = "Build a React component with CSS and HTML layout for the API page"
        assert infer_task_category(desc) == "frontend"


class TestOutcomeRecordedAfterCompletion:
    def test_outcome_recorded_after_completion(self, db):
        """After successful agent completion, a ModelSpecPerformance row
        is created/updated for the spec that was used."""
        _setup_corps_with_strategy(db, policy="best_of_breed", exploration=0.0, risk=0.8)

        spec = _seed_spec(db, "outcome-spec", model_id="outcome-model-v1",
                          categories="backend")
        for _ in range(5):
            record_model_spec_outcome(db, spec.id, "backend", score=80.0, success=True)

        registry, executor = _make_registry_and_executor()
        client = MockLLMClient()
        client.queue_response(LLMResponse(content="API endpoint created."))

        defn = create_definition(
            db, "performer", "You build API endpoints.",
            model_tier=ModelTier.SONNET, tools_allowed=["tuner"],
        )
        session = spawn_session(db, defn.id, CORPS_ID)

        # Get the attempt count before
        perf_before = (
            db.query(ModelSpecPerformance)
            .filter(
                ModelSpecPerformance.model_spec_id == spec.id,
                ModelSpecPerformance.task_category == "backend",
                ModelSpecPerformance.corps_id == CORPS_ID,
            )
            .first()
        )
        attempts_before = perf_before.total_attempts if perf_before else 0

        result = run_agent(
            db, session.id, client, executor,
            "Create an API endpoint for user database queries",
        )

        assert result.status == RunStatus.COMPLETED
        assert result.model_spec_id == spec.id

        # Verify outcome was recorded
        perf_after = (
            db.query(ModelSpecPerformance)
            .filter(
                ModelSpecPerformance.model_spec_id == spec.id,
                ModelSpecPerformance.task_category == "backend",
                ModelSpecPerformance.corps_id == CORPS_ID,
            )
            .first()
        )
        assert perf_after is not None
        assert perf_after.total_attempts == attempts_before + 1
        assert perf_after.successful_attempts > 0


class TestModelOverrideInLLMClient:
    def test_mock_client_records_override(self):
        """MockLLMClient records model_override in calls."""
        client = MockLLMClient()
        from backend.services.llm_client import LLMMessage
        msgs = [LLMMessage("user", "Hello")]

        client.chat(msgs, ModelTier.SONNET, model_override="custom-model-v3")

        assert client.calls[0]["model_override"] == "custom-model-v3"
        assert client.calls[0]["model_id"] == "custom-model-v3"

    def test_mock_client_no_override(self):
        """Without model_override, model_id comes from tier mapping."""
        client = MockLLMClient()
        from backend.services.llm_client import LLMMessage
        msgs = [LLMMessage("user", "Hello")]

        client.chat(msgs, ModelTier.HAIKU)

        assert client.calls[0]["model_override"] is None
        assert client.calls[0]["model_id"] == MODEL_TIER_MAP[ModelTier.HAIKU]
