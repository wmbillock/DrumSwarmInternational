"""Tests for Batch 5: GUPP, watchdog, capability ledger, event bus wiring, seance."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# --- GUPP and Watchdog ---

class TestMetronomeGUPP:
    def _setup_corps(self, db):
        from backend.models.corps import Corps, CorpsStatus
        from backend.models.coordinate import Coordinate, CoordinateType
        from backend.models.rep import Rep, RepStatus
        from backend.models.agent_definition import AgentDefinition, ModelTier
        from backend.models.agent_session import AgentSession, SessionStatus

        corps = Corps(name="Test")
        db.add(corps)
        db.commit()

        coord = Coordinate(type=CoordinateType.COORDINATE, title="Task")
        db.add(coord)
        db.commit()

        defn = AgentDefinition(
            role="brass_tech", system_prompt="test",
            model_tier=ModelTier.HAIKU, tools_allowed="", corps_id=corps.id,
        )
        db.add(defn)
        db.commit()

        session = AgentSession(
            definition_id=defn.id, corps_id=corps.id, status=SessionStatus.ACTIVE,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        return corps, coord, session

    def test_normal_tick_no_reclaim(self, db):
        from backend.tools.metronome import tick
        corps, coord, session = self._setup_corps(db)
        from backend.models.rep import Rep, RepStatus
        rep = Rep(coordinate_id=coord.id, status=RepStatus.IN_PROGRESS, assigned_to=session.id)
        db.add(rep)
        db.commit()

        result = tick(db, corps.id)
        assert result.checked >= 1
        assert result.reclaimed == 0
        assert result.idle_kicked == 0

    def test_reclaim_dead_session(self, db):
        from backend.tools.metronome import tick
        from backend.models.agent_session import SessionStatus
        corps, coord, session = self._setup_corps(db)
        session.status = SessionStatus.FAILED
        db.commit()

        from backend.models.rep import Rep, RepStatus
        rep = Rep(coordinate_id=coord.id, status=RepStatus.ASSIGNED, assigned_to=session.id)
        db.add(rep)
        db.commit()

        result = tick(db, corps.id)
        assert result.reclaimed >= 1

    def test_watchdog_detects_dead_roles(self, db):
        from backend.tools.metronome import _watchdog_check
        from backend.models.agent_session import AgentSession, SessionStatus
        from backend.models.agent_definition import AgentDefinition, ModelTier
        from backend.models.corps import Corps

        corps = Corps(name="WD Test")
        db.add(corps)
        db.commit()

        # Create a timing_judge that's failed
        defn = AgentDefinition(
            role="timing_judge", system_prompt="test",
            model_tier=ModelTier.HAIKU, tools_allowed="", corps_id=corps.id,
        )
        db.add(defn)
        db.commit()

        session = AgentSession(
            definition_id=defn.id, corps_id=corps.id, status=SessionStatus.FAILED,
        )
        db.add(session)
        db.commit()

        dead = _watchdog_check(db, corps.id)
        assert "timing_judge" in dead

    def test_watchdog_ignores_active_roles(self, db):
        from backend.tools.metronome import _watchdog_check
        from backend.models.agent_session import AgentSession, SessionStatus
        from backend.models.agent_definition import AgentDefinition, ModelTier
        from backend.models.corps import Corps

        corps = Corps(name="WD Test 2")
        db.add(corps)
        db.commit()

        defn = AgentDefinition(
            role="timing_judge", system_prompt="test",
            model_tier=ModelTier.HAIKU, tools_allowed="", corps_id=corps.id,
        )
        db.add(defn)
        db.commit()

        session = AgentSession(
            definition_id=defn.id, corps_id=corps.id, status=SessionStatus.ACTIVE,
        )
        db.add(session)
        db.commit()

        dead = _watchdog_check(db, corps.id)
        assert "timing_judge" not in dead


# --- Capability Ledger ---

class TestCapabilityLedger:
    def test_record_entry(self, db):
        from backend.models.capability_ledger import LedgerEntryType
        from backend.services.capability_ledger_service import record_entry
        entry = record_entry(
            db, role_type="brass_tech",
            entry_type=LedgerEntryType.REP_COMPLETED,
            performer_id="p1", performer_name="Test",
            score=85.0, details="Good work",
        )
        assert entry.id
        assert entry.entry_type == LedgerEntryType.REP_COMPLETED

    def test_get_entries_for_performer(self, db):
        from backend.models.capability_ledger import LedgerEntryType
        from backend.services.capability_ledger_service import record_entry, get_entries_for_performer
        record_entry(db, role_type="tech", entry_type=LedgerEntryType.REP_COMPLETED, performer_id="p1")
        record_entry(db, role_type="tech", entry_type=LedgerEntryType.REP_FAILED, performer_id="p1")
        record_entry(db, role_type="tech", entry_type=LedgerEntryType.REP_COMPLETED, performer_id="p2")

        entries = get_entries_for_performer(db, "p1")
        assert len(entries) == 2

    def test_get_performer_stats(self, db):
        from backend.models.capability_ledger import LedgerEntryType
        from backend.services.capability_ledger_service import record_entry, get_performer_stats
        record_entry(db, role_type="tech", entry_type=LedgerEntryType.REP_COMPLETED,
                     performer_id="p1", score=90.0)
        record_entry(db, role_type="tech", entry_type=LedgerEntryType.REP_COMPLETED,
                     performer_id="p1", score=80.0)
        record_entry(db, role_type="tech", entry_type=LedgerEntryType.REP_FAILED,
                     performer_id="p1")

        stats = get_performer_stats(db, "p1")
        assert stats["reps_completed"] == 2
        assert stats["reps_failed"] == 1
        assert stats["avg_score"] == 85.0

    def test_trust_change_logged_to_ledger(self, db):
        from backend.models.performer import Performer
        from backend.services.performer_service import update_trust
        from backend.services.capability_ledger_service import get_entries_for_performer
        from backend.models.capability_ledger import LedgerEntryType

        p = Performer(name="Ledger Test", role_type="tech", trust_score=50.0)
        db.add(p)
        db.commit()
        db.refresh(p)

        update_trust(db, p.id, 5.0, reason="test bonus")
        entries = get_entries_for_performer(db, p.id, entry_type=LedgerEntryType.TRUST_CHANGE)
        assert len(entries) >= 1
        assert entries[0].trust_before == 50.0
        assert entries[0].trust_after == 55.0


# --- Event Bus Wiring ---

class TestEventBusWiring:
    def test_rep_transition_publishes_event(self, db):
        from backend.models.coordinate import Coordinate, CoordinateType
        from backend.services.rep_service import create_rep, transition_rep
        from backend.models.rep import RepStatus
        from backend.services.event_bus import get_event_bus

        bus = get_event_bus()
        received = []
        bus.subscribe("rep.status_changed", lambda t, p: received.append(p))

        coord = Coordinate(type=CoordinateType.COORDINATE, title="Test")
        db.add(coord)
        db.commit()

        rep = create_rep(db, coord.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)

        assert len(received) >= 1
        assert received[-1]["new_status"] == "assigned"


# --- Seance ---

class TestSeance:
    def test_seance_empty_result(self):
        from backend.services.seance import query_previous_sessions
        result = query_previous_sessions("test query", role="executive_director")
        # Should not crash, may return empty if memory bank has nothing
        assert result.query == "test query"

    def test_query_for_agent_context(self, db):
        from backend.services.seance import query_for_agent_context
        # Should return a string (possibly empty) without crashing
        ctx = query_for_agent_context(db, "executive_director", "Build an app")
        assert isinstance(ctx, str)


# --- Prompt Arranger Feedback Injection ---

class TestFeedbackInjection:
    def test_assemble_prompt_doesnt_crash_with_feedback(self):
        from backend.services.prompt_arranger import assemble_prompt
        # Should not crash even if memory bank is empty
        result = assemble_prompt("executive_director")
        assert isinstance(result, str)
