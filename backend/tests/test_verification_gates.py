"""Tests for verification gates integration with rep completion."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.coordinate import Coordinate, CoordinateType, CoordinateStatus
from backend.models.rep import Rep, RepStatus
from backend.services.rep_service import create_rep, transition_rep, InvalidRepTransition
from backend.services.verification import (
    VerificationEngine,
    VerificationError,
    GateResult,
    gate_non_empty,
    gate_minimum_length,
    gate_json_valid,
    gate_brown_m_and_m,
    get_verification_engine,
    COORDINATE_TYPE_GATES,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def coordinate(db):
    coord = Coordinate(type=CoordinateType.COORDINATE, title="Test task", status=CoordinateStatus.PENDING)
    db.add(coord)
    db.commit()
    db.refresh(coord)
    return coord


class TestBuiltInGates:
    def test_non_empty_passes(self):
        r = gate_non_empty("hello world")
        assert r.passed

    def test_non_empty_fails(self):
        r = gate_non_empty("")
        assert not r.passed

    def test_non_empty_whitespace_fails(self):
        r = gate_non_empty("   ")
        assert not r.passed

    def test_minimum_length_passes(self):
        r = gate_minimum_length("a" * 20, min_length=10)
        assert r.passed

    def test_minimum_length_fails(self):
        r = gate_minimum_length("short", min_length=10)
        assert not r.passed

    def test_json_valid_passes_for_json(self):
        r = gate_json_valid('{"key": "value"}')
        assert r.passed

    def test_json_valid_fails_for_bad_json(self):
        r = gate_json_valid('{bad json')
        assert not r.passed

    def test_json_valid_skips_non_json(self):
        r = gate_json_valid("plain text")
        assert r.passed

    def test_brown_m_and_m_passes(self):
        r = gate_brown_m_and_m("This has the CANARY word", canary_phrase="canary")
        assert r.passed

    def test_brown_m_and_m_fails(self):
        r = gate_brown_m_and_m("No secret word here", canary_phrase="canary")
        assert not r.passed

    def test_brown_m_and_m_skips_when_no_canary(self):
        r = gate_brown_m_and_m("anything", canary_phrase="")
        assert r.passed


class TestVerificationEngine:
    def test_verify_passes_good_result(self):
        engine = VerificationEngine()
        vr = engine.verify(rep_id="r1", result="A good result with enough text")
        assert vr.passed
        assert len(vr.failed_gates) == 0

    def test_verify_fails_empty_result(self):
        engine = VerificationEngine()
        vr = engine.verify(rep_id="r1", result="")
        assert not vr.passed
        assert any(g.gate_name == "non_empty" for g in vr.failed_gates)

    def test_verify_with_canary(self):
        engine = VerificationEngine()
        vr = engine.verify(rep_id="r1", result="Result with canary123 embedded", canary_phrase="canary123")
        assert vr.passed

    def test_verify_fails_missing_canary(self):
        engine = VerificationEngine()
        vr = engine.verify(rep_id="r1", result="A result without the secret", canary_phrase="canary123")
        assert not vr.passed

    def test_custom_gate_per_coordinate(self):
        engine = VerificationEngine()

        def custom_gate(result: str, **kwargs) -> GateResult:
            return GateResult(gate_name="custom", passed="REQUIRED" in result)

        engine.add_custom_gate("coord-1", custom_gate)
        vr = engine.verify(rep_id="r1", result="Has REQUIRED word", coordinate_id="coord-1")
        assert vr.passed

        vr2 = engine.verify(rep_id="r2", result="Missing the word", coordinate_id="coord-1")
        assert not vr2.passed

    def test_type_gate(self):
        engine = VerificationEngine()

        def type_gate(result: str, **kwargs) -> GateResult:
            return GateResult(gate_name="type_check", passed=len(result) > 100)

        engine.add_type_gate("show", type_gate)
        vr = engine.verify(rep_id="r1", result="short", coordinate_type="show")
        assert not vr.passed

    def test_type_kwargs_override_min_length(self):
        engine = VerificationEngine()
        engine.set_type_kwargs("show", min_length=50)
        vr = engine.verify(rep_id="r1", result="a" * 30, coordinate_type="show")
        assert not vr.passed  # 30 < 50

        vr2 = engine.verify(rep_id="r2", result="a" * 60, coordinate_type="show")
        assert vr2.passed

    def test_coordinate_type_gates_config(self):
        assert "show" in COORDINATE_TYPE_GATES
        assert COORDINATE_TYPE_GATES["show"]["min_length"] == 50

    def test_singleton_engine(self):
        e1 = get_verification_engine()
        e2 = get_verification_engine()
        assert e1 is e2


class TestVerificationInRepTransition:
    def test_completion_blocked_by_empty_result(self, db, coordinate):
        rep = create_rep(db, coordinate.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="")

        with pytest.raises(VerificationError):
            transition_rep(db, rep.id, RepStatus.COMPLETED)

    def test_completion_succeeds_with_good_result(self, db, coordinate):
        rep = create_rep(db, coordinate.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="A sufficiently long result for verification gates")
        rep = transition_rep(db, rep.id, RepStatus.COMPLETED)
        assert rep.status == RepStatus.COMPLETED

    def test_completion_blocked_by_short_result(self, db, coordinate):
        rep = create_rep(db, coordinate.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="tiny")

        with pytest.raises(VerificationError):
            transition_rep(db, rep.id, RepStatus.COMPLETED)
