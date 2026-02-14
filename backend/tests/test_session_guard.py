"""Tests for RAII session guard — verifies cleanup on normal exit, crash, and cascade."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.agent_definition import AgentDefinition, ModelTier
from backend.models.agent_session import AgentSession, SessionStatus
from backend.services.agent_lifecycle import (
    create_definition,
    spawn_session,
    complete_session,
    fail_session,
)
from backend.services.session_guard import (
    SyncSessionGuard,
    cascade_fail_children,
)


# Import all models for create_all
import backend.models  # noqa: F401


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


@pytest.fixture
def corps_id():
    return "test-corps-001"


@pytest.fixture
def definition(db, corps_id):
    return create_definition(
        db,
        role="test_worker",
        system_prompt="Test worker agent",
        model_tier=ModelTier.HAIKU,
        corps_id=corps_id,
    )


@pytest.fixture
def parent_definition(db, corps_id):
    return create_definition(
        db,
        role="test_parent",
        system_prompt="Test parent agent",
        model_tier=ModelTier.HAIKU,
        corps_id=corps_id,
    )


class TestSyncSessionGuard:
    def test_normal_exit_no_error(self, db, definition, corps_id):
        """Guard should not interfere if caller handles session properly."""
        session = spawn_session(db, definition.id, corps_id)
        assert session.status == SessionStatus.ACTIVE

        with SyncSessionGuard(db, session.id) as guard:
            # Simulate normal completion
            complete_session(db, session.id)
            guard.mark_completed()

        refreshed = db.get(AgentSession, session.id)
        assert refreshed.status == SessionStatus.COMPLETED

    def test_unhandled_exception_fails_session(self, db, definition, corps_id):
        """If an exception occurs and session isn't handled, guard fails it."""
        session = spawn_session(db, definition.id, corps_id)

        with pytest.raises(ValueError):
            with SyncSessionGuard(db, session.id):
                raise ValueError("something broke")

        refreshed = db.get(AgentSession, session.id)
        assert refreshed.status == SessionStatus.FAILED
        assert "ValueError" in refreshed.error

    def test_exception_does_not_double_fail(self, db, definition, corps_id):
        """If caller already failed the session, guard shouldn't try again."""
        session = spawn_session(db, definition.id, corps_id)

        with pytest.raises(RuntimeError):
            with SyncSessionGuard(db, session.id) as guard:
                fail_session(db, session.id, error="caller handled")
                guard.mark_failed()
                raise RuntimeError("after fail")

        refreshed = db.get(AgentSession, session.id)
        assert refreshed.status == SessionStatus.FAILED
        assert refreshed.error == "caller handled"

    def test_cascade_children_on_parent_death(self, db, parent_definition, definition, corps_id):
        """When parent guard exits with exception, children should cascade-fail."""
        parent = spawn_session(db, parent_definition.id, corps_id)
        child1 = spawn_session(db, definition.id, corps_id, parent_session_id=parent.id)
        child2 = spawn_session(db, definition.id, corps_id, parent_session_id=parent.id)

        with pytest.raises(RuntimeError):
            with SyncSessionGuard(db, parent.id, cascade_children=True):
                raise RuntimeError("parent crashed")

        p = db.get(AgentSession, parent.id)
        c1 = db.get(AgentSession, child1.id)
        c2 = db.get(AgentSession, child2.id)

        assert p.status == SessionStatus.FAILED
        assert c1.status == SessionStatus.FAILED
        assert c2.status == SessionStatus.FAILED
        assert "parent session terminated" in c1.error

    def test_cascade_skips_already_completed(self, db, parent_definition, definition, corps_id):
        """Cascade should not fail children already in terminal state."""
        parent = spawn_session(db, parent_definition.id, corps_id)
        child1 = spawn_session(db, definition.id, corps_id, parent_session_id=parent.id)
        child2 = spawn_session(db, definition.id, corps_id, parent_session_id=parent.id)

        # Complete child1 before parent dies
        complete_session(db, child1.id)

        with pytest.raises(RuntimeError):
            with SyncSessionGuard(db, parent.id, cascade_children=True):
                raise RuntimeError("parent crashed")

        c1 = db.get(AgentSession, child1.id)
        c2 = db.get(AgentSession, child2.id)

        assert c1.status == SessionStatus.COMPLETED  # unchanged
        assert c2.status == SessionStatus.FAILED


class TestCascadeFailChildren:
    def test_cascade_recursive(self, db, parent_definition, definition, corps_id):
        """Cascade should work recursively: grandchildren also fail."""
        grandparent = spawn_session(db, parent_definition.id, corps_id)
        parent = spawn_session(db, definition.id, corps_id, parent_session_id=grandparent.id)
        child = spawn_session(db, definition.id, corps_id, parent_session_id=parent.id)

        count = cascade_fail_children(db, grandparent.id)
        assert count == 2  # parent + child

        p = db.get(AgentSession, parent.id)
        c = db.get(AgentSession, child.id)
        assert p.status == SessionStatus.FAILED
        assert c.status == SessionStatus.FAILED

    def test_cascade_no_children(self, db, definition, corps_id):
        """Cascade with no children returns 0."""
        session = spawn_session(db, definition.id, corps_id)
        count = cascade_fail_children(db, session.id)
        assert count == 0

    def test_cascade_mixed_statuses(self, db, parent_definition, definition, corps_id):
        """Only ACTIVE children should be cascade-failed."""
        parent = spawn_session(db, parent_definition.id, corps_id)
        active_child = spawn_session(db, definition.id, corps_id, parent_session_id=parent.id)
        completed_child = spawn_session(db, definition.id, corps_id, parent_session_id=parent.id)
        complete_session(db, completed_child.id)

        count = cascade_fail_children(db, parent.id)
        assert count == 1

        ac = db.get(AgentSession, active_child.id)
        cc = db.get(AgentSession, completed_child.id)
        assert ac.status == SessionStatus.FAILED
        assert cc.status == SessionStatus.COMPLETED
