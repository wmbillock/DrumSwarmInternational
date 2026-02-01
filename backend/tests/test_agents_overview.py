"""Comprehensive test suite for /api/agents-overview endpoint.

Tests the enhanced agents-overview endpoint which returns all active agent sessions
with:
- Eager loading of AgentDefinition (no N+1 queries)
- Batch loading of Corps records for corps_name resolution
- Correct response structure with all expected fields
- Edge cases (no sessions, null corps_id, null definitions, etc.)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone

from backend.database import Base

# Import all models to ensure Base.metadata is populated
import backend.models.segment  # noqa: F401
import backend.models.rep  # noqa: F401
import backend.models.message  # noqa: F401
import backend.models.problem  # noqa: F401
import backend.models.subscription  # noqa: F401
import backend.models.agent_definition  # noqa: F401
import backend.models.agent_session  # noqa: F401
import backend.models.score  # noqa: F401
import backend.models.penalty  # noqa: F401
import backend.models.corps  # noqa: F401
import backend.models.show  # noqa: F401
import backend.models.performer  # noqa: F401

from backend.api.app import app, get_db
from backend.models.agent_definition import AgentDefinition, ModelTier, AgentClassification
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.corps import Corps, CorpsStatus

# Enum values for reference
DEFAULT_MODEL_TIER = ModelTier.SONNET
DEFAULT_CLASSIFICATION = AgentClassification.ADMINISTRATIVE_STAFF


@pytest.fixture
def db_engine():
    """Create a shared database engine for all tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(db_engine):
    """Set up test client with shared in-memory SQLite database."""
    TestingSession = sessionmaker(bind=db_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db(db_engine):
    """Provide a database session for test setup using shared engine."""
    TestingSession = sessionmaker(bind=db_engine)
    session = TestingSession()
    yield session
    session.close()


class TestAgentsOverviewBasic:
    """Basic functionality tests for /api/agents-overview."""

    def test_empty_sessions_returns_empty_list(self, client):
        """Test endpoint returns empty list when no active sessions exist."""
        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_response_structure_with_single_session(self, client, db):
        """Test response structure is correct with a single active session."""
        # Create corps
        corps = Corps(
            id="test-corps-1",
            name="Test Corps",
            status=CorpsStatus.WINTER_CAMPS
        )
        db.add(corps)

        # Create agent definition
        defn = AgentDefinition(
            id="exec-dir-1",
            role="executive_director",
            nickname="ED",
            model_tier=ModelTier.SONNET,
            system_prompt="You are an ED.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add(defn)
        db.commit()

        # Create active agent session
        session = AgentSession(
            id="session-1",
            definition_id="exec-dir-1",
            corps_id="test-corps-1",
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()

        # Query endpoint
        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        session_data = data[0]
        assert session_data["id"] == "session-1"
        assert session_data["role"] == "executive_director"
        assert session_data["nickname"] == "ED"
        assert session_data["model_tier"] == "sonnet"
        assert session_data["status"] == "active"
        assert session_data["corps_id"] == "test-corps-1"
        assert session_data["corps_name"] == "Test Corps"
        assert session_data["started_at"] is not None

    def test_only_active_sessions_returned(self, client, db):
        """Test endpoint only returns ACTIVE sessions, excludes COMPLETED/FAILED/TIMED_OUT."""
        # Create corps
        corps = Corps(
            id="test-corps-1",
            name="Test Corps",
            status=CorpsStatus.WINTER_CAMPS
        )
        db.add(corps)

        # Create agent definition
        defn = AgentDefinition(
            id="ed-1",
            role="executive_director",
            nickname="ED",
            model_tier=ModelTier.SONNET,
            system_prompt="You are an agent.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add(defn)
        db.commit()

        # Create sessions with different statuses
        active_session = AgentSession(
            id="session-active",
            definition_id="ed-1",
            corps_id="test-corps-1",
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc)
        )
        completed_session = AgentSession(
            id="session-completed",
            definition_id="ed-1",
            corps_id="test-corps-1",
            status=SessionStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc)
        )
        failed_session = AgentSession(
            id="session-failed",
            definition_id="ed-1",
            corps_id="test-corps-1",
            status=SessionStatus.FAILED,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc)
        )

        db.add_all([active_session, completed_session, failed_session])
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()

        # Only active session should be returned
        assert len(data) == 1
        assert data[0]["id"] == "session-active"
        assert data[0]["status"] == "active"


class TestAgentsOverviewCorpsNameResolution:
    """Test corps_name field resolution from Corps table."""

    def test_valid_corps_id_resolves_to_corps_name(self, client, db):
        """Test session with valid corps_id returns correct corps_name."""
        # Create corps
        corps = Corps(
            id="blue-devils",
            name="Blue Devils",
            status=CorpsStatus.WINTER_CAMPS
        )
        db.add(corps)

        # Create definition and session
        defn = AgentDefinition(
            id="ed-1",
            role="executive_director",
            nickname="ED",
            model_tier=ModelTier.SONNET,
            system_prompt="You are an agent.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add(defn)
        db.commit()

        session = AgentSession(
            id="session-1",
            definition_id="ed-1",
            corps_id="blue-devils",
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["corps_name"] == "Blue Devils"

    def test_inactive_session_not_returned(self, client, db):
        """Test that inactive sessions are not returned (corps_id must be non-null in model)."""
        # Create definition
        defn = AgentDefinition(
            id="ed-1",
            role="executive_director",
            nickname="ED",
            model_tier=ModelTier.SONNET,
            system_prompt="You are an agent.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add(defn)

        # Create corps
        corps = Corps(
            id="test-corps",
            name="Test Corps",
            status=CorpsStatus.WINTER_CAMPS
        )
        db.add(corps)
        db.commit()

        # Create inactive session (should not be returned)
        session = AgentSession(
            id="session-1",
            definition_id="ed-1",
            corps_id="test-corps",
            status=SessionStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        # No active sessions
        assert len(data) == 0

    def test_nonexistent_corps_id_returns_null_corps_name(self, client, db):
        """Test session referencing non-existent corps returns null corps_name."""
        # Create definition
        defn = AgentDefinition(
            id="ed-1",
            role="executive_director",
            nickname="ED",
            model_tier=ModelTier.SONNET,
            system_prompt="You are an agent.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add(defn)
        db.commit()

        # Create session with non-existent corps_id
        session = AgentSession(
            id="session-1",
            definition_id="ed-1",
            corps_id="nonexistent-corps",
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["corps_id"] == "nonexistent-corps"
        assert data[0]["corps_name"] is None

    def test_multiple_sessions_from_same_corps(self, client, db):
        """Test multiple sessions from same corps all resolve corps_name correctly."""
        # Create corps
        corps = Corps(
            id="blue-devils",
            name="Blue Devils",
            status=CorpsStatus.WINTER_CAMPS
        )
        db.add(corps)

        # Create multiple definitions
        defn_ed = AgentDefinition(
            id="ed-1",
            role="executive_director",
            nickname="ED",
            model_tier=ModelTier.SONNET,
            system_prompt="You are an agent.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        defn_pc = AgentDefinition(
            id="pc-1",
            role="program_coordinator",
            nickname="PC",
            model_tier=ModelTier.SONNET,
            system_prompt="You are an agent.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        defn_tj = AgentDefinition(
            id="tj-1",
            role="timing_judge",
            nickname="TJ",
            model_tier=ModelTier.SONNET,
            system_prompt="You are an agent.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add_all([defn_ed, defn_pc, defn_tj])
        db.commit()

        # Create multiple sessions for same corps
        session_ed = AgentSession(
            id="session-ed",
            definition_id="ed-1",
            corps_id="blue-devils",
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc)
        )
        session_pc = AgentSession(
            id="session-pc",
            definition_id="pc-1",
            corps_id="blue-devils",
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc)
        )
        session_tj = AgentSession(
            id="session-tj",
            definition_id="tj-1",
            corps_id="blue-devils",
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc)
        )
        db.add_all([session_ed, session_pc, session_tj])
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

        # All should have same corps_name
        corps_names = {item["corps_name"] for item in data}
        assert corps_names == {"Blue Devils"}

        # Verify all have correct roles
        roles = {item["role"] for item in data}
        assert roles == {"executive_director", "program_coordinator", "timing_judge"}


class TestAgentsOverviewEdgeCases:
    """Test edge cases and null value handling."""

    def test_null_definition_returns_unknown_role(self, client, db):
        """Test session with non-existent definition_id returns 'unknown' for role."""
        # Create corps
        corps = Corps(
            id="test-corps",
            name="Test Corps",
            status=CorpsStatus.WINTER_CAMPS
        )
        db.add(corps)
        db.commit()

        # Create session with non-existent definition_id
        session = AgentSession(
            id="session-1",
            definition_id="nonexistent-def",
            corps_id="test-corps",
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["role"] == "unknown"
        assert data[0]["nickname"] is None
        assert data[0]["model_tier"] == "unknown"

    def test_null_nickname_in_definition(self, client, db):
        """Test definition with null nickname returns null in response."""
        # Create corps
        corps = Corps(
            id="test-corps",
            name="Test Corps",
            status=CorpsStatus.WINTER_CAMPS
        )
        db.add(corps)

        # Create definition without nickname
        defn = AgentDefinition(
            id="def-1",
            role="executive_director",
            nickname=None,
            model_tier=ModelTier.SONNET,
            system_prompt="You are an agent.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add(defn)
        db.commit()

        # Create session
        session = AgentSession(
            id="session-1",
            definition_id="def-1",
            corps_id="test-corps",
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["nickname"] is None

    def test_multiple_corps_batch_loading(self, client, db):
        """Test batch loading of multiple different corps."""
        # Create multiple corps
        corps1 = Corps(id="corp-1", name="Corps One", status=CorpsStatus.WINTER_CAMPS)
        corps2 = Corps(id="corp-2", name="Corps Two", status=CorpsStatus.ON_TOUR)
        corps3 = Corps(id="corp-3", name="Corps Three", status=CorpsStatus.WINTER_CAMPS)
        db.add_all([corps1, corps2, corps3])

        # Create definition
        defn = AgentDefinition(
            id="ed-1",
            role="executive_director",
            nickname="ED",
            model_tier=ModelTier.SONNET,
            system_prompt="You are an agent.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add(defn)
        db.commit()

        # Create sessions across different corps
        session1 = AgentSession(
            id="session-1", definition_id="ed-1", corps_id="corp-1",
            status=SessionStatus.ACTIVE, started_at=datetime.now(timezone.utc)
        )
        session2 = AgentSession(
            id="session-2", definition_id="ed-1", corps_id="corp-2",
            status=SessionStatus.ACTIVE, started_at=datetime.now(timezone.utc)
        )
        session3 = AgentSession(
            id="session-3", definition_id="ed-1", corps_id="corp-3",
            status=SessionStatus.ACTIVE, started_at=datetime.now(timezone.utc)
        )
        db.add_all([session1, session2, session3])
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

        # Verify all corps names are resolved correctly
        corps_map = {item["corps_id"]: item["corps_name"] for item in data}
        assert corps_map == {
            "corp-1": "Corps One",
            "corp-2": "Corps Two",
            "corp-3": "Corps Three",
        }


class TestAgentsOverviewResponseValidation:
    """Test response structure and field validation."""

    def test_all_required_fields_present(self, client, db):
        """Test all required fields are present in response."""
        # Setup
        corps = Corps(id="corp-1", name="Test Corps", status=CorpsStatus.WINTER_CAMPS)
        defn = AgentDefinition(
            id="def-1", role="executive_director", nickname="ED",
            model_tier=ModelTier.SONNET, system_prompt="You are an ED.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add_all([corps, defn])
        db.commit()

        session = AgentSession(
            id="session-1", definition_id="def-1", corps_id="corp-1",
            status=SessionStatus.ACTIVE, started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        item = data[0]
        required_fields = ["id", "role", "nickname", "model_tier", "status",
                          "corps_id", "corps_name", "started_at"]
        for field in required_fields:
            assert field in item, f"Missing field: {field}"

    def test_field_types_are_correct(self, client, db):
        """Test response field types match expectations."""
        # Setup
        corps = Corps(id="corp-1", name="Test Corps", status=CorpsStatus.WINTER_CAMPS)
        defn = AgentDefinition(
            id="def-1", role="executive_director", nickname="ED",
            model_tier=ModelTier.SONNET, system_prompt="You are an ED.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add_all([corps, defn])
        db.commit()

        session = AgentSession(
            id="session-1", definition_id="def-1", corps_id="corp-1",
            status=SessionStatus.ACTIVE, started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        item = data[0]
        assert isinstance(item["id"], str)
        assert isinstance(item["role"], str)
        assert isinstance(item["nickname"], (str, type(None)))
        assert isinstance(item["model_tier"], str)
        assert isinstance(item["status"], str)
        assert isinstance(item["corps_id"], (str, type(None)))
        assert isinstance(item["corps_name"], (str, type(None)))
        assert isinstance(item["started_at"], str)

    def test_model_tier_values_are_valid(self, client, db):
        """Test model_tier values are valid enum values."""
        corps = Corps(id="corp-1", name="Test Corps", status=CorpsStatus.WINTER_CAMPS)

        # Test all model tiers
        for tier in ModelTier:
            defn = AgentDefinition(
                id=f"def-{tier.value}",
                role=f"role-{tier.value}",
                nickname=f"nick-{tier.value}",
                model_tier=tier,
                system_prompt="You are an agent.",
                classification=AgentClassification.ADMINISTRATIVE_STAFF
            )
            db.add(defn)

        db.add(corps)
        db.commit()

        for tier in ModelTier:
            session = AgentSession(
                id=f"session-{tier.value}",
                definition_id=f"def-{tier.value}",
                corps_id="corp-1",
                status=SessionStatus.ACTIVE,
                started_at=datetime.now(timezone.utc)
            )
            db.add(session)
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == len(ModelTier)

        valid_tiers = {tier.value for tier in ModelTier}
        for item in data:
            assert item["model_tier"] in valid_tiers

    def test_status_value_is_active(self, client, db):
        """Test all returned sessions have status='active'."""
        corps = Corps(id="corp-1", name="Test Corps", status=CorpsStatus.WINTER_CAMPS)
        defn = AgentDefinition(
            id="def-1", role="executive_director", nickname="ED",
            model_tier=ModelTier.SONNET, system_prompt="You are an ED.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add_all([corps, defn])
        db.commit()

        # Create multiple active sessions
        for i in range(5):
            session = AgentSession(
                id=f"session-{i}",
                definition_id="def-1",
                corps_id="corp-1",
                status=SessionStatus.ACTIVE,
                started_at=datetime.now(timezone.utc)
            )
            db.add(session)
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()

        for item in data:
            assert item["status"] == "active"

    def test_started_at_is_iso_format(self, client, db):
        """Test started_at timestamps are in ISO format."""
        corps = Corps(id="corp-1", name="Test Corps", status=CorpsStatus.WINTER_CAMPS)
        defn = AgentDefinition(
            id="def-1", role="executive_director", nickname="ED",
            model_tier=ModelTier.SONNET, system_prompt="You are an ED.",
            classification=AgentClassification.ADMINISTRATIVE_STAFF
        )
        db.add_all([corps, defn])
        db.commit()

        session = AgentSession(
            id="session-1", definition_id="def-1", corps_id="corp-1",
            status=SessionStatus.ACTIVE, started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()

        resp = client.get("/api/agents-overview")
        assert resp.status_code == 200
        data = resp.json()

        # Check ISO format (should be parseable back to datetime)
        for item in data:
            started = item["started_at"]
            assert started is not None
            # Should contain 'T' for ISO format and 'Z' for UTC or timezone info
            assert "T" in started
