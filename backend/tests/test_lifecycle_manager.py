"""Tests for agent lifecycle management — ageouts, auditions, hiring, self-improvement."""

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.performer import Performer, PerformerStatus
from backend.models.agent_definition import AgentDefinition, ModelTier, AgentClassification
from backend.models.agent_experience import AgentExperience
from backend.models.self_improvement_log import SelfImprovementLog, ImprovementStatus

# Import all models for table creation
import backend.models.segment  # noqa: F401
import backend.models.rep  # noqa: F401
import backend.models.message  # noqa: F401
import backend.models.problem  # noqa: F401
import backend.models.subscription  # noqa: F401
import backend.models.agent_session  # noqa: F401
import backend.models.score  # noqa: F401
import backend.models.penalty  # noqa: F401
import backend.models.corps  # noqa: F401

from backend.services.lifecycle_manager import (
    age_performer,
    check_ageouts,
    conduct_auditions,
    fire_staff,
    record_agent_learning,
    propose_self_improvement,
    approve_self_improvement,
    reject_self_improvement,
    conduct_season_transition,
    MAX_PERFORMER_AGE,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _make_performer(db, name="Test Performer", age=16, role_type="brass", trust_score=0.8):
    p = Performer(name=name, age=age, role_type=role_type, trust_score=trust_score)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _make_definition(db, role="brass_tech", corps_id="corps-1"):
    d = AgentDefinition(
        role=role,
        system_prompt="Test prompt",
        model_tier=ModelTier.HAIKU,
        corps_id=corps_id,
        version=1,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


class TestAgePerformer:
    def test_age_increments(self, db):
        p = _make_performer(db, age=16)
        result = age_performer(db, p.id)
        assert result.age == 17
        assert result.experience_seasons == 1

    def test_ageout_at_limit(self, db):
        p = _make_performer(db, age=MAX_PERFORMER_AGE)
        result = age_performer(db, p.id)
        assert result.age == MAX_PERFORMER_AGE + 1
        assert result.status == PerformerStatus.RETIRED
        assert "Aged out" in result.retirement_reason

    def test_age_not_found(self, db):
        with pytest.raises(ValueError, match="not found"):
            age_performer(db, "nonexistent")


class TestCheckAgeouts:
    def test_finds_performers_at_limit(self, db):
        _make_performer(db, name="Young", age=16)
        _make_performer(db, name="Old", age=MAX_PERFORMER_AGE)
        result = check_ageouts(db)
        assert len(result) == 1
        assert result[0].name == "Old"

    def test_no_ageouts(self, db):
        _make_performer(db, age=16)
        assert check_ageouts(db) == []


class TestConductAuditions:
    def test_selects_top_by_trust(self, db):
        _make_performer(db, name="Low", trust_score=0.3, role_type="brass")
        _make_performer(db, name="High", trust_score=0.9, role_type="brass")
        _make_performer(db, name="Mid", trust_score=0.6, role_type="brass")
        result = conduct_auditions(db, "brass", n_spots=2)
        assert len(result) == 2
        assert result[0].name == "High"

    def test_excludes_aged_out(self, db):
        _make_performer(db, name="Old", age=MAX_PERFORMER_AGE + 1, role_type="brass")
        _make_performer(db, name="Young", age=16, role_type="brass")
        result = conduct_auditions(db, "brass")
        assert len(result) == 1
        assert result[0].name == "Young"


class TestFireStaff:
    def test_retires_definition(self, db):
        d = _make_definition(db)
        fire_staff(db, d.id, "Budget cuts")
        db.refresh(d)
        assert d.version == -1

    def test_not_found(self, db):
        with pytest.raises(ValueError, match="not found"):
            fire_staff(db, "nonexistent", "reason")


class TestRecordAgentLearning:
    def test_stores_experience(self, db):
        p = _make_performer(db)
        exp = record_agent_learning(
            db,
            performer_id=p.id,
            activity_type="rep_completion",
            learned_skills=["python", "testing"],
            corps_id="corps-1",
        )
        assert exp.id is not None
        assert json.loads(exp.learned_skills) == ["python", "testing"]
        assert exp.activity_type == "rep_completion"


class TestSelfImprovement:
    def test_propose(self, db):
        d = _make_definition(db)
        log = propose_self_improvement(
            db, d.id, {"system_prompt": "New prompt"}, "Better performance"
        )
        assert log.status == ImprovementStatus.PENDING
        assert log.old_version == 1
        assert log.new_version == 2

    def test_approve(self, db):
        d = _make_definition(db)
        log = propose_self_improvement(
            db, d.id, {"system_prompt": "New prompt"}, "Better"
        )
        result = approve_self_improvement(db, log.id, "approver-1")
        assert result.system_prompt == "New prompt"
        assert result.version == 2
        db.refresh(log)
        assert log.status == ImprovementStatus.APPROVED

    def test_reject(self, db):
        d = _make_definition(db)
        log = propose_self_improvement(db, d.id, {}, "Bad idea")
        result = reject_self_improvement(db, log.id, "approver-1")
        assert result.status == ImprovementStatus.REJECTED

    def test_approve_already_approved(self, db):
        d = _make_definition(db)
        log = propose_self_improvement(db, d.id, {}, "reason")
        approve_self_improvement(db, log.id, "a-1")
        with pytest.raises(ValueError, match="not pending"):
            approve_self_improvement(db, log.id, "a-2")

    def test_propose_not_found(self, db):
        with pytest.raises(ValueError, match="not found"):
            propose_self_improvement(db, "bad-id", {}, "reason")


class TestSeasonTransition:
    def test_empty_corps(self, db):
        result = conduct_season_transition(db, "corps-1")
        assert result["aged"] == 0
