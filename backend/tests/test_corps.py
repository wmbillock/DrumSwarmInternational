"""Phase 7: Corps orchestration tests — initialization, tour mode, handoff, escalation,
merge monitor, rehearsal modes."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.corps import Corps, CorpsStatus, RehearsalMode
from backend.models.coordinate import Coordinate, CoordinateType, CoordinateStatus
from backend.models.rep import Rep, RepStatus
from backend.services.corps_service import (
    create_corps,
    initialize_corps,
    start_tour,
    stop_tour,
    set_rehearsal_mode,
    validate_handoff,
    handoff,
    escalate,
    merge_monitor_check,
    disband_corps,
    CorpsError,
    InvalidHandoff,
    EscalationRequired,
    CORPS_HIERARCHY,
    HANDOFF_CHAIN,
    ESCALATION_CHAIN,
)

# Import all models
import backend.models.coordinate  # noqa: F401
import backend.models.rep  # noqa: F401
import backend.models.message  # noqa: F401
import backend.models.problem  # noqa: F401
import backend.models.subscription  # noqa: F401
import backend.models.agent_definition  # noqa: F401
import backend.models.agent_session  # noqa: F401
import backend.models.score  # noqa: F401
import backend.models.penalty  # noqa: F401
import backend.models.corps  # noqa: F401


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


class TestCorpsCreation:
    def test_create_corps(self, db):
        corps = create_corps(db, name="Phantom Regiment")
        assert corps.id is not None
        assert corps.name == "Phantom Regiment"
        assert corps.status == CorpsStatus.INITIALIZING
        assert corps.tour_mode is False

    def test_create_corps_with_show(self, db):
        corps = create_corps(db, name="Blue Devils", show_id="show-1")
        assert corps.show_id == "show-1"


class TestCorpsInitialization:
    def test_initialize_spawns_hierarchy(self, db):
        corps = create_corps(db, name="Test Corps")
        sessions = initialize_corps(db, corps.id)
        assert len(sessions) == len(CORPS_HIERARCHY)
        assert "executive_director" in sessions
        assert "program_coordinator" in sessions
        assert "brass_tech" in sessions

    def test_initialize_sets_rehearsal_status(self, db):
        corps = create_corps(db, name="Test Corps")
        initialize_corps(db, corps.id)
        db.refresh(corps)
        assert corps.status == CorpsStatus.REHEARSAL

    def test_initialize_parent_child_chain(self, db):
        corps = create_corps(db, name="Test Corps")
        sessions = initialize_corps(db, corps.id)
        # ED has no parent
        assert sessions["executive_director"].parent_session_id is None
        # PC's parent is ED
        assert sessions["program_coordinator"].parent_session_id == sessions["executive_director"].id
        # Brass tech's parent is brass caption head
        assert sessions["brass_tech"].parent_session_id == sessions["brass_caption_head"].id

    def test_initialize_nonexistent_corps(self, db):
        with pytest.raises(CorpsError):
            initialize_corps(db, "nonexistent")


class TestTourMode:
    def test_start_tour(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        corps = start_tour(db, corps.id)
        assert corps.tour_mode is True
        assert corps.status == CorpsStatus.TOUR

    def test_stop_tour(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        start_tour(db, corps.id)
        corps = stop_tour(db, corps.id)
        assert corps.tour_mode is False
        assert corps.status == CorpsStatus.REHEARSAL

    def test_cannot_tour_from_initializing(self, db):
        corps = create_corps(db, name="Test")
        with pytest.raises(CorpsError, match="Cannot start tour"):
            start_tour(db, corps.id)

    def test_cannot_tour_disbanded(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        disband_corps(db, corps.id)
        with pytest.raises(CorpsError, match="Cannot start tour"):
            start_tour(db, corps.id)


class TestHandoffChain:
    def test_valid_handoff_pc_to_caption(self):
        assert validate_handoff("program_coordinator", "brass_caption_head")

    def test_valid_handoff_tech_to_performer(self):
        assert validate_handoff("brass_tech", "performer")

    def test_invalid_handoff_performer_to_ed(self):
        assert not validate_handoff("performer", "executive_director")

    def test_invalid_handoff_reverse_chain(self):
        assert not validate_handoff("brass_tech", "brass_caption_head")

    def test_handoff_sends_message(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        # Should not raise
        handoff(db, corps.id, "program_coordinator", "brass_caption_head",
                subject="New brass arrangement")

    def test_handoff_invalid_raises(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        with pytest.raises(InvalidHandoff):
            handoff(db, corps.id, "performer", "executive_director",
                    subject="Skip the chain")


class TestEscalation:
    def test_escalate_performer(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        target = escalate(db, corps.id, "performer", subject="Need help")
        assert target == "section_leader"

    def test_escalate_tech_to_caption_head(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        target = escalate(db, corps.id, "brass_tech", subject="Issue")
        assert target == "brass_caption_head"

    def test_escalate_to_user(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        with pytest.raises(EscalationRequired, match="user"):
            escalate(db, corps.id, "executive_director", subject="Critical")

    def test_full_escalation_chain(self, db):
        """Walk the full chain from performer to ED."""
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        role = "performer"
        chain = [role]
        while True:
            try:
                role = escalate(db, corps.id, role, subject=f"Escalate from {role}")
                chain.append(role)
            except EscalationRequired:
                chain.append("user")
                break
        assert chain[-1] == "user"
        assert len(chain) >= 4  # performer → section_leader → tech → caption → PC → ED → user


class TestRehearsalModes:
    def test_set_basics(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        corps = set_rehearsal_mode(db, corps.id, RehearsalMode.BASICS)
        assert corps.rehearsal_mode == RehearsalMode.BASICS

    def test_set_sectionals(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        corps = set_rehearsal_mode(db, corps.id, RehearsalMode.SECTIONALS)
        assert corps.rehearsal_mode == RehearsalMode.SECTIONALS

    def test_set_full_ensemble(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        corps = set_rehearsal_mode(db, corps.id, RehearsalMode.FULL_ENSEMBLE)
        assert corps.rehearsal_mode == RehearsalMode.FULL_ENSEMBLE

    def test_set_run_through(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        corps = set_rehearsal_mode(db, corps.id, RehearsalMode.RUN_THROUGH)
        assert corps.rehearsal_mode == RehearsalMode.RUN_THROUGH

    def test_cannot_set_mode_when_initializing(self, db):
        corps = create_corps(db, name="Test")
        with pytest.raises(CorpsError):
            set_rehearsal_mode(db, corps.id, RehearsalMode.BASICS)

    def test_can_set_mode_during_tour(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        start_tour(db, corps.id)
        corps = set_rehearsal_mode(db, corps.id, RehearsalMode.RUN_THROUGH)
        assert corps.rehearsal_mode == RehearsalMode.RUN_THROUGH


class TestMergeMonitor:
    def test_merge_completed_siblings(self, db):
        show = Coordinate(type=CoordinateType.SHOW, title="Show",
                          status=CoordinateStatus.IN_PROGRESS)
        db.add(show)
        db.commit()
        db.refresh(show)

        m1 = Coordinate(type=CoordinateType.MOVEMENT, title="M1",
                         parent_id=show.id, status=CoordinateStatus.COMPLETED)
        m2 = Coordinate(type=CoordinateType.MOVEMENT, title="M2",
                         parent_id=show.id, status=CoordinateStatus.COMPLETED)
        db.add_all([m1, m2])
        db.commit()

        result = merge_monitor_check(db, "corps-1")
        assert result.merged >= 1
        db.refresh(show)
        assert show.status == CoordinateStatus.COMPLETED

    def test_merge_with_incomplete_siblings(self, db):
        show = Coordinate(type=CoordinateType.SHOW, title="Show",
                          status=CoordinateStatus.IN_PROGRESS)
        db.add(show)
        db.commit()
        db.refresh(show)

        m1 = Coordinate(type=CoordinateType.MOVEMENT, title="M1",
                         parent_id=show.id, status=CoordinateStatus.COMPLETED)
        m2 = Coordinate(type=CoordinateType.MOVEMENT, title="M2",
                         parent_id=show.id, status=CoordinateStatus.IN_PROGRESS)
        db.add_all([m1, m2])
        db.commit()

        result = merge_monitor_check(db, "corps-1")
        assert result.merged == 0
        db.refresh(show)
        assert show.status == CoordinateStatus.IN_PROGRESS  # unchanged

    def test_merge_detects_conflicts(self, db):
        show = Coordinate(type=CoordinateType.SHOW, title="Show",
                          status=CoordinateStatus.IN_PROGRESS)
        db.add(show)
        db.commit()
        db.refresh(show)

        m1 = Coordinate(type=CoordinateType.MOVEMENT, title="M1",
                         parent_id=show.id, status=CoordinateStatus.COMPLETED)
        m2 = Coordinate(type=CoordinateType.MOVEMENT, title="M2",
                         parent_id=show.id, status=CoordinateStatus.FAILED)
        db.add_all([m1, m2])
        db.commit()

        result = merge_monitor_check(db, "corps-1")
        assert result.conflicts >= 1


class TestDisbandCorps:
    def test_disband(self, db):
        corps = create_corps(db, name="Test")
        initialize_corps(db, corps.id)
        corps = disband_corps(db, corps.id)
        assert corps.status == CorpsStatus.DISBANDED
        assert corps.tour_mode is False

    def test_disband_nonexistent(self, db):
        with pytest.raises(CorpsError):
            disband_corps(db, "nope")
