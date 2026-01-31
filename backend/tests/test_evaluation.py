"""Tests for evaluation service — post-show performer evaluation."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.agent_definition import AgentDefinition, ModelTier
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.corps import Corps, CorpsStatus
from backend.models.performer import Performer, PerformerStatus
from backend.services.evaluation_service import evaluate_corps


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def corps(db):
    c = Corps(name="Test Corps")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture
def performer(db):
    p = Performer(name="Test Player", role_type="brass_tech", trust_score=50.0)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _make_session(db, corps, performer, status=SessionStatus.COMPLETED):
    defn = AgentDefinition(
        role="brass_tech", system_prompt="test", model_tier=ModelTier.HAIKU,
        tools_allowed="", corps_id=corps.id,
    )
    db.add(defn)
    db.commit()
    db.refresh(defn)

    session = AgentSession(
        definition_id=defn.id, corps_id=corps.id,
        status=status, performer_id=performer.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


class TestEvaluateCorps:
    def test_evaluate_empty_corps(self, db, corps):
        result = evaluate_corps(db, corps.id)
        assert result["performers_evaluated"] == 0
        assert result["corps_id"] == corps.id

    def test_evaluate_successful_session(self, db, corps, performer):
        _make_session(db, corps, performer, status=SessionStatus.COMPLETED)
        result = evaluate_corps(db, corps.id)
        assert result["performers_evaluated"] == 1
        detail = result["details"][0]
        assert detail["success"] is True
        assert detail["performer_name"] == "Test Player"
        # Trust should have increased
        db.refresh(performer)
        assert performer.trust_score > 50.0

    def test_evaluate_failed_session(self, db, corps, performer):
        _make_session(db, corps, performer, status=SessionStatus.FAILED)
        result = evaluate_corps(db, corps.id)
        assert result["performers_evaluated"] == 1
        detail = result["details"][0]
        assert detail["success"] is False
        # Trust should have decreased
        db.refresh(performer)
        assert performer.trust_score < 50.0

    def test_evaluate_ignores_sessions_without_performer(self, db, corps):
        defn = AgentDefinition(
            role="brass_tech", system_prompt="test", model_tier=ModelTier.HAIKU,
            tools_allowed="", corps_id=corps.id,
        )
        db.add(defn)
        db.commit()
        db.refresh(defn)
        session = AgentSession(
            definition_id=defn.id, corps_id=corps.id,
            status=SessionStatus.COMPLETED, performer_id=None,
        )
        db.add(session)
        db.commit()
        result = evaluate_corps(db, corps.id)
        assert result["performers_evaluated"] == 0
