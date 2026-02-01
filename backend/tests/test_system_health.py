"""Tests for system_health service."""

from backend.models.corps import Corps, CorpsStatus, CorpsMode
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.agent_definition import AgentDefinition
from backend.services.system_health import get_swarm_health


def _make_corps(db, name="Test Corps", status=CorpsStatus.WINTER_CAMPS, mode=None):
    corps = Corps(name=name, status=status, mode=mode)
    db.add(corps)
    db.commit()
    return corps


def _make_agent(db, corps_id, role="test_role", status=SessionStatus.ACTIVE):
    defn = AgentDefinition(role=role, system_prompt="test", model_tier="sonnet")
    db.add(defn)
    db.flush()
    session = AgentSession(definition_id=defn.id, corps_id=corps_id, status=status)
    db.add(session)
    db.commit()
    return session


class TestSwarmHealth:
    def test_empty_swarm(self, db):
        health = get_swarm_health(db)
        assert health.active_corps == 0
        assert health.total_agents == 0
        assert health.failure_rate == 0.0

    def test_one_active_corps(self, db):
        corps = _make_corps(db)
        _make_agent(db, corps.id)
        _make_agent(db, corps.id, role="role2")
        health = get_swarm_health(db)
        assert health.active_corps == 1
        assert health.total_agents == 2
        assert health.active_agents == 2

    def test_disbanded_corps_excluded(self, db):
        _make_corps(db, name="Active", status=CorpsStatus.WINTER_CAMPS)
        _make_corps(db, name="Dead", status=CorpsStatus.DISBANDED)
        health = get_swarm_health(db)
        assert health.active_corps == 1

    def test_corps_summaries_include_mode(self, db):
        _make_corps(db, mode=CorpsMode.DESIGN_ROOM)
        health = get_swarm_health(db)
        assert len(health.corps_summaries) == 1
        assert health.corps_summaries[0]["mode"] == "design_room"

    def test_failed_agents_counted(self, db):
        corps = _make_corps(db)
        _make_agent(db, corps.id, status=SessionStatus.ACTIVE)
        _make_agent(db, corps.id, role="r2", status=SessionStatus.FAILED)
        health = get_swarm_health(db)
        assert health.active_agents == 1
        assert health.failed_agents == 1
