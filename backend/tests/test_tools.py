"""Tests for rehearsal tools: metronome, tuner, gock block, dressing, cleaning."""

import pytest

from backend.models.agent_definition import ModelTier
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.coordinate import Coordinate, CoordinateStatus, CoordinateType
from backend.models.rep import Rep, RepStatus
from backend.services.agent_lifecycle import create_definition, spawn_session
from backend.tools.cleaning import Cleaning
from backend.tools.dressing import Dressing
from backend.tools.gock_block import GockBlock
from backend.tools.metronome import tick
from backend.tools.tuner import Tuner


CORPS_ID = "test-corps-1"


# ── Tuner ──────────────────────────────────────────────────────


class TestTuner:
    def test_all_checks_pass(self):
        tuner = Tuner()
        tuner.add_check("not_empty", lambda a: None if a else "empty")
        tuner.add_check("has_return", lambda a: None if "return" in a else "no return")
        result = tuner.validate("return 42")
        assert result.passed is True
        assert result.summary == "2/2 checks passed"

    def test_check_fails(self):
        tuner = Tuner()
        tuner.add_check("not_empty", lambda a: None if a else "empty")
        tuner.add_check("has_return", lambda a: None if "return" in a else "no return statement")
        result = tuner.validate("x = 42")
        assert result.passed is False
        assert result.summary == "1/2 checks passed"
        failed = [c for c in result.checks if not c["passed"]]
        assert len(failed) == 1
        assert failed[0]["error"] == "no return statement"

    def test_no_checks(self):
        tuner = Tuner()
        result = tuner.validate("anything")
        assert result.passed is True
        assert result.summary == "0/0 checks passed"

    def test_check_exception_treated_as_failure(self):
        tuner = Tuner()
        tuner.add_check("boom", lambda a: (_ for _ in ()).throw(RuntimeError("kaboom")))
        result = tuner.validate("test")
        assert result.passed is False
        assert "kaboom" in result.checks[0]["error"]


# ── Gock Block ─────────────────────────────────────────────────


class TestGockBlock:
    def test_all_benchmarks_pass(self):
        gb = GockBlock()
        gb.add_benchmark("line_count", lambda a: a.count("\n"), threshold=10)
        result = gb.run("one\ntwo\n")
        assert result.passed is True
        assert result.benchmarks[0]["measurement"] == 2
        assert result.summary == "1/1 benchmarks passed"

    def test_benchmark_exceeds_threshold(self):
        gb = GockBlock()
        gb.add_benchmark("length", lambda a: len(a), threshold=5)
        result = gb.run("this is way too long")
        assert result.passed is False
        assert result.benchmarks[0]["passed"] is False
        assert result.benchmarks[0]["threshold"] == 5

    def test_no_threshold_always_passes(self):
        gb = GockBlock()
        gb.add_benchmark("length", lambda a: len(a))
        result = gb.run("anything at all")
        assert result.passed is True

    def test_benchmark_exception(self):
        gb = GockBlock()
        gb.add_benchmark("bad", lambda a: 1 / 0)
        result = gb.run("test")
        assert result.passed is False
        assert "error" in result.benchmarks[0]

    def test_multiple_benchmarks_mixed(self):
        gb = GockBlock()
        gb.add_benchmark("short", lambda a: len(a), threshold=100)
        gb.add_benchmark("few_lines", lambda a: a.count("\n"), threshold=1)
        result = gb.run("line1\nline2\nline3\n")
        assert result.passed is False
        assert result.summary == "1/2 benchmarks passed"


# ── Dressing ───────────────────────────────────────────────────


class TestDressing:
    def test_all_aligned(self):
        d = Dressing()
        d.add_check(
            "same_prefix",
            lambda a, related: None if all(r[:3] == a[:3] for r in related) else "prefix mismatch",
        )
        result = d.check_alignment("abc_main", ["abc_util", "abc_helper"])
        assert result.aligned is True
        assert result.summary == "1/1 alignment checks passed"

    def test_misaligned(self):
        d = Dressing()
        d.add_check(
            "same_prefix",
            lambda a, related: None if all(r[:3] == a[:3] for r in related) else "prefix mismatch",
        )
        result = d.check_alignment("abc_main", ["xyz_other"])
        assert result.aligned is False
        assert result.checks[0]["issue"] == "prefix mismatch"

    def test_no_related_artifacts(self):
        d = Dressing()
        d.add_check("always_ok", lambda a, related: None)
        result = d.check_alignment("standalone", [])
        assert result.aligned is True

    def test_check_exception(self):
        d = Dressing()
        d.add_check("boom", lambda a, related: (_ for _ in ()).throw(ValueError("oops")))
        result = d.check_alignment("test", ["other"])
        assert result.aligned is False
        assert "oops" in result.checks[0]["issue"]


# ── Cleaning ───────────────────────────────────────────────────


class TestCleaning:
    def _create_completed_rep(self, db, coordinate_id, result_text):
        rep = Rep(coordinate_id=coordinate_id, status=RepStatus.COMPLETED, result=result_text)
        db.add(rep)
        db.commit()
        return rep

    def _create_coordinate(self, db):
        coord = Coordinate(
            type=CoordinateType.COORDINATE,
            title="Test coord",
            status=CoordinateStatus.COMPLETED,
        )
        db.add(coord)
        db.commit()
        return coord

    def test_clean_sweep(self, db):
        coord = self._create_coordinate(db)
        self._create_completed_rep(db, coord.id, "good code")
        cleaning = Cleaning()
        cleaning.add_rule("not_empty", lambda a: None if a else "empty")
        result = cleaning.sweep(db, coord.id)
        assert result.swept == 1
        assert result.issues_found == 0

    def test_issue_found(self, db):
        coord = self._create_coordinate(db)
        self._create_completed_rep(db, coord.id, "")
        cleaning = Cleaning()
        cleaning.add_rule("not_empty", lambda a: None if a else "empty artifact")
        result = cleaning.sweep(db, coord.id)
        assert result.swept == 1
        assert result.issues_found == 1
        assert result.issues[0].rule == "not_empty"
        assert result.issues[0].description == "empty artifact"

    def test_skips_non_completed_reps(self, db):
        coord = self._create_coordinate(db)
        rep = Rep(coordinate_id=coord.id, status=RepStatus.IN_PROGRESS, result="wip")
        db.add(rep)
        db.commit()
        cleaning = Cleaning()
        cleaning.add_rule("anything", lambda a: "found")
        result = cleaning.sweep(db, coord.id)
        assert result.swept == 0

    def test_multiple_reps_multiple_rules(self, db):
        coord = self._create_coordinate(db)
        self._create_completed_rep(db, coord.id, "short")
        self._create_completed_rep(db, coord.id, "this is a longer artifact with content")
        cleaning = Cleaning()
        cleaning.add_rule("min_length", lambda a: None if len(a) > 10 else "too short")
        result = cleaning.sweep(db, coord.id)
        assert result.swept == 2
        assert result.issues_found == 1  # "short" fails

    def test_rule_exception(self, db):
        coord = self._create_coordinate(db)
        self._create_completed_rep(db, coord.id, "test")
        cleaning = Cleaning()
        cleaning.add_rule("bad_rule", lambda a: 1 / 0)
        result = cleaning.sweep(db, coord.id)
        assert result.issues_found == 1
        assert "Rule error" in result.issues[0].description


# ── Metronome ──────────────────────────────────────────────────


class TestMetronome:
    def _setup_corps(self, db):
        """Create a coordinate with an assigned rep owned by an active session."""
        coord = Coordinate(
            type=CoordinateType.COORDINATE,
            title="Login page",
            status=CoordinateStatus.IN_PROGRESS,
        )
        db.add(coord)
        db.commit()

        defn = create_definition(db, "performer", "You perform.")
        session = spawn_session(db, defn.id, CORPS_ID)

        rep = Rep(
            coordinate_id=coord.id,
            status=RepStatus.IN_PROGRESS,
            assigned_to=session.id,
        )
        db.add(rep)
        db.commit()
        return coord, session, rep

    def test_no_reclaim_for_active_session(self, db):
        coord, session, rep = self._setup_corps(db)
        result = tick(db, CORPS_ID)
        assert result.checked == 1
        assert result.reclaimed == 0
        db.refresh(rep)
        assert rep.status == RepStatus.IN_PROGRESS

    def test_reclaim_dead_session(self, db):
        coord, session, rep = self._setup_corps(db)
        # Kill the session
        session.status = SessionStatus.FAILED
        db.commit()

        result = tick(db, CORPS_ID)
        assert result.checked == 1
        assert result.reclaimed == 1
        assert rep.id in result.reclaimed_rep_ids

        db.refresh(rep)
        assert rep.status == RepStatus.PENDING
        assert rep.assigned_to is None

    def test_reclaim_missing_session(self, db):
        coord = Coordinate(
            type=CoordinateType.COORDINATE,
            title="Orphan rep",
            status=CoordinateStatus.IN_PROGRESS,
        )
        db.add(coord)
        db.commit()

        rep = Rep(
            coordinate_id=coord.id,
            status=RepStatus.ASSIGNED,
            assigned_to="nonexistent-session-id",
        )
        db.add(rep)
        db.commit()

        result = tick(db, CORPS_ID)
        assert result.reclaimed == 1

        db.refresh(rep)
        assert rep.status == RepStatus.PENDING

    def test_no_reps_to_check(self, db):
        result = tick(db, CORPS_ID)
        assert result.checked == 0
        assert result.reclaimed == 0

    def test_completed_reps_ignored(self, db):
        coord = Coordinate(
            type=CoordinateType.COORDINATE,
            title="Done",
            status=CoordinateStatus.COMPLETED,
        )
        db.add(coord)
        db.commit()
        rep = Rep(coordinate_id=coord.id, status=RepStatus.COMPLETED)
        db.add(rep)
        db.commit()

        result = tick(db, CORPS_ID)
        assert result.checked == 0
