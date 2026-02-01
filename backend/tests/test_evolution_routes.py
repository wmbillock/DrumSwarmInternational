"""Tests for Evolution & Talent Pool routes — genome, selection events, mutation simulation."""

import json
import pytest
from sqlalchemy.orm import Session

from backend.database import Base, create_db_engine, create_session_factory
from backend.models.performer import Performer, PerformerStatus
from backend.models.agent_definition import AgentDefinition, ModelTier, AgentClassification
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.self_improvement_log import SelfImprovementLog, ImprovementStatus
from backend.models.capability_ledger import CapabilityLedgerEntry, LedgerEntryType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = create_session_factory(engine)
    session = SessionFactory()
    yield session
    session.close()


def _make_performer(db, name="Echo Brass", role="drill_writer", trust=65.0, age=18):
    p = Performer(name=name, role_type=role, trust_score=trust, age=age, experience_seasons=2)
    p.total_sessions = 10
    p.successful_sessions = 7
    p.failed_sessions = 3
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _make_definition(db, role="drill_writer", corps_id="corps-1"):
    d = AgentDefinition(
        role=role,
        system_prompt="You are a drill writer.",
        model_tier=ModelTier.SONNET,
        tools_allowed="create_segment,get_segment",
        version=3,
        nickname="Dash",
        classification=AgentClassification.INSTRUCTIONAL_STAFF,
        corps_id=corps_id,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


# ---------------------------------------------------------------------------
# Genome rendering
# ---------------------------------------------------------------------------

class TestGenomeRendering:
    """Test that the agent genome returns full identity metadata."""

    def test_genome_includes_performer_fields(self, db):
        p = _make_performer(db)
        from backend.api.evolution_routes import api_get_performer_genome

        result = api_get_performer_genome(p.id, db)

        assert result["name"] == "Echo Brass"
        assert result["role_type"] == "drill_writer"
        assert result["trust_score"] == 65.0
        assert result["age"] == 18
        assert result["experience_seasons"] == 2

    def test_genome_includes_performance_stats(self, db):
        p = _make_performer(db)
        from backend.api.evolution_routes import api_get_performer_genome

        result = api_get_performer_genome(p.id, db)

        perf = result["performance"]
        assert perf["total_sessions"] == 10
        assert perf["successful_sessions"] == 7
        assert perf["failed_sessions"] == 3
        assert perf["success_rate"] == 0.7

    def test_genome_includes_definition_when_session_exists(self, db):
        p = _make_performer(db)
        d = _make_definition(db)

        session = AgentSession(
            definition_id=d.id,
            corps_id="corps-1",
            performer_id=p.id,
            status=SessionStatus.COMPLETED,
        )
        db.add(session)
        db.commit()

        from backend.api.evolution_routes import api_get_performer_genome

        result = api_get_performer_genome(p.id, db)

        assert result["definition"] is not None
        defn = result["definition"]
        assert defn["role"] == "drill_writer"
        assert defn["model_tier"] == "sonnet"
        assert "create_segment" in defn["tools_allowed"]
        assert defn["version"] == 3
        assert defn["nickname"] == "Dash"

    def test_genome_no_definition_without_session(self, db):
        p = _make_performer(db)
        from backend.api.evolution_routes import api_get_performer_genome

        result = api_get_performer_genome(p.id, db)
        assert result["definition"] is None

    def test_genome_not_found(self, db):
        from backend.api.evolution_routes import api_get_performer_genome
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            api_get_performer_genome("nonexistent", db)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Selection events (ledger)
# ---------------------------------------------------------------------------

class TestSelectionEvents:
    def test_events_returns_ledger_entries(self, db):
        entry = CapabilityLedgerEntry(
            performer_id="p-1", performer_name="Test",
            role_type="drill_writer", entry_type=LedgerEntryType.TRUST_CHANGE,
            trust_before=50.0, trust_after=53.0, details="session_success",
        )
        db.add(entry)
        db.commit()

        from backend.api.evolution_routes import api_get_selection_events
        result = api_get_selection_events(db=db)

        assert len(result) == 1
        assert result[0]["entry_type"] == "trust_change"
        assert result[0]["trust_before"] == 50.0

    def test_events_filters_by_type(self, db):
        db.add(CapabilityLedgerEntry(
            performer_name="A", role_type="x",
            entry_type=LedgerEntryType.TRUST_CHANGE,
        ))
        db.add(CapabilityLedgerEntry(
            performer_name="B", role_type="x",
            entry_type=LedgerEntryType.RETIREMENT,
        ))
        db.commit()

        from backend.api.evolution_routes import api_get_selection_events
        result = api_get_selection_events(event_type="retirement", db=db)

        assert len(result) == 1
        assert result[0]["performer_name"] == "B"


# ---------------------------------------------------------------------------
# Mutation simulation
# ---------------------------------------------------------------------------

class TestMutationSimulation:
    def test_simulate_model_upgrade(self, db):
        d = _make_definition(db)
        from backend.api.evolution_routes import api_simulate_mutation, MutationSimulation

        data = MutationSimulation(
            definition_id=d.id,
            changes={"model_tier": "opus"},
            reason="Need more capability for complex drill",
        )
        result = api_simulate_mutation(data, db)

        assert result["sandbox"] is True
        assert result["applied"] is False
        assert result["requires_approval"] is True
        assert result["risk_level"] == "high"
        assert any(i["field"] == "model_tier" for i in result["impacts"])

    def test_simulate_tool_addition(self, db):
        d = _make_definition(db)
        from backend.api.evolution_routes import api_simulate_mutation, MutationSimulation

        data = MutationSimulation(
            definition_id=d.id,
            changes={"tools_allowed": ["create_segment", "get_segment", "delete_segment"]},
            reason="Need delete capability",
        )
        result = api_simulate_mutation(data, db)

        tool_impact = [i for i in result["impacts"] if i.get("impact") == "tools_added"]
        assert len(tool_impact) == 1
        assert "delete_segment" in tool_impact[0]["added"]

    def test_simulate_prompt_change(self, db):
        d = _make_definition(db)
        from backend.api.evolution_routes import api_simulate_mutation, MutationSimulation

        data = MutationSimulation(
            definition_id=d.id,
            changes={"system_prompt": "You are an expert drill writer with 10 years of experience."},
            reason="More specific instructions",
        )
        result = api_simulate_mutation(data, db)

        assert result["risk_level"] == "low"
        assert result["requires_approval"] is False
        prompt_impact = [i for i in result["impacts"] if i["field"] == "system_prompt"]
        assert len(prompt_impact) == 1
        assert "prompt" in prompt_impact[0]["impact"]

    def test_simulate_unknown_field_flagged(self, db):
        d = _make_definition(db)
        from backend.api.evolution_routes import api_simulate_mutation, MutationSimulation

        data = MutationSimulation(
            definition_id=d.id,
            changes={"forbidden_field": "value"},
            reason="test",
        )
        result = api_simulate_mutation(data, db)

        assert any(i.get("risk") == "error" for i in result["impacts"])

    def test_simulate_nonexistent_definition(self, db):
        from backend.api.evolution_routes import api_simulate_mutation, MutationSimulation
        from fastapi import HTTPException

        data = MutationSimulation(
            definition_id="nonexistent",
            changes={"model_tier": "opus"},
            reason="test",
        )
        with pytest.raises(HTTPException) as exc_info:
            api_simulate_mutation(data, db)
        assert exc_info.value.status_code == 404
