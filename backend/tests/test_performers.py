"""Tests for performer model and service."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base

# Import all models to populate metadata
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


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestPerformerCreation:
    def test_create_performer(self, db):
        from backend.services.performer_service import create_performer
        p = create_performer(db, "executive_director")
        assert p.name is not None
        assert p.role_type == "executive_director"
        assert p.trust_score == 50.0
        assert p.status.value == "active"
        assert p.total_sessions == 0

    def test_create_with_custom_name(self, db):
        from backend.services.performer_service import create_performer
        p = create_performer(db, "brass_tech", name="Custom Name")
        assert p.name == "Custom Name"

    def test_unique_names(self, db):
        from backend.services.performer_service import create_performer
        p1 = create_performer(db, "brass_tech")
        p2 = create_performer(db, "brass_tech")
        assert p1.name != p2.name


class TestTrustScoring:
    def test_trust_increases_on_success(self, db):
        from backend.services.performer_service import create_performer, record_session_completion
        p = create_performer(db, "brass_tech")
        pid = p.id
        p = record_session_completion(db, pid, success=True)
        assert p.trust_score > 50.0
        assert p.successful_sessions == 1
        assert p.total_sessions == 1

    def test_trust_decreases_on_failure(self, db):
        from backend.services.performer_service import create_performer, record_session_completion
        p = create_performer(db, "brass_tech")
        pid = p.id
        p = record_session_completion(db, pid, success=False)
        assert p.trust_score < 50.0
        assert p.failed_sessions == 1

    def test_trust_capped_at_100(self, db):
        from backend.services.performer_service import create_performer, update_trust
        p = create_performer(db, "brass_tech")
        p = update_trust(db, p.id, 200.0, "test")
        assert p.trust_score == 100.0

    def test_trust_floor_at_0(self, db):
        from backend.services.performer_service import create_performer, update_trust
        p = create_performer(db, "brass_tech")
        p = update_trust(db, p.id, -200.0, "test")
        assert p.trust_score == 0.0

    def test_high_score_bonus(self, db):
        from backend.services.performer_service import create_performer, record_session_completion
        p = create_performer(db, "brass_tech")
        pid = p.id
        p = record_session_completion(db, pid, success=True, score=90)
        # High score gives +5 instead of +3
        assert p.trust_score == 55.0


class TestRetirement:
    def test_auto_retirement_on_low_trust(self, db):
        from backend.services.performer_service import create_performer, update_trust
        p = create_performer(db, "brass_tech")
        # Drop trust below threshold
        p = update_trust(db, p.id, -35.0, "repeated failures")
        assert p.status.value == "retired"
        assert p.retirement_reason is not None

    def test_probation_before_retirement(self, db):
        from backend.services.performer_service import create_performer, update_trust
        p = create_performer(db, "brass_tech")
        # Drop to probation zone (30)
        p = update_trust(db, p.id, -22.0, "some failures")
        assert p.status.value == "probation"

    def test_manual_retirement(self, db):
        from backend.services.performer_service import create_performer, retire_performer
        p = create_performer(db, "brass_tech")
        p = retire_performer(db, p.id, reason="Manual retirement test")
        assert p.status.value == "retired"
        assert "Manual" in p.retirement_reason


class TestAuditions:
    def test_audition_creates_performer_when_pool_empty(self, db):
        from backend.services.performer_service import audition_for_role
        p = audition_for_role(db, "guard_tech")
        assert p is not None
        assert p.role_type == "guard_tech"
        assert p.status.value == "active"

    def test_audition_picks_highest_trust(self, db):
        from backend.services.performer_service import create_performer, update_trust, audition_for_role
        p1 = create_performer(db, "brass_tech", name="Low Trust")
        p2 = create_performer(db, "brass_tech", name="High Trust")
        update_trust(db, p1.id, -20.0, "bad")
        update_trust(db, p2.id, 20.0, "good")

        winner = audition_for_role(db, "brass_tech")
        assert winner.id == p2.id

    def test_audition_excludes_retired(self, db):
        from backend.services.performer_service import (
            create_performer, retire_performer, audition_for_role,
        )
        p1 = create_performer(db, "brass_tech", name="Retired One")
        retire_performer(db, p1.id, "old")
        p2 = create_performer(db, "brass_tech", name="Active One")

        winner = audition_for_role(db, "brass_tech")
        assert winner.id == p2.id

    def test_audition_includes_probation(self, db):
        from backend.services.performer_service import (
            create_performer, update_trust, audition_for_role,
        )
        # Only one performer, on probation
        p = create_performer(db, "visual_tech")
        update_trust(db, p.id, -22.0, "test")  # drops to probation
        assert p.status.value == "probation"

        winner = audition_for_role(db, "visual_tech")
        assert winner.id == p.id


class TestPerformerListing:
    def test_list_all_performers(self, db):
        from backend.services.performer_service import create_performer, list_performers
        create_performer(db, "brass_tech")
        create_performer(db, "guard_tech")
        all_p = list_performers(db)
        assert len(all_p) == 2

    def test_list_by_status(self, db):
        from backend.models.performer import PerformerStatus
        from backend.services.performer_service import (
            create_performer, retire_performer, list_performers,
        )
        p1 = create_performer(db, "brass_tech")
        create_performer(db, "guard_tech")
        retire_performer(db, p1.id, "test")

        active = list_performers(db, status=PerformerStatus.ACTIVE)
        assert len(active) == 1
        retired = list_performers(db, status=PerformerStatus.RETIRED)
        assert len(retired) == 1

    def test_get_performers_by_role(self, db):
        from backend.services.performer_service import create_performer, get_performers_by_role
        create_performer(db, "brass_tech")
        create_performer(db, "brass_tech")
        create_performer(db, "guard_tech")
        brass = get_performers_by_role(db, "brass_tech")
        assert len(brass) == 2
