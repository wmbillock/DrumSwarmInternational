import pytest

from backend.models.coordinate import CoordinateType
from backend.models.problem import ProblemSeverity, ProblemStatus
from backend.services.coordinate_service import create_coordinate
from backend.services.problem_service import (
    InvalidProblemTransition,
    acknowledge_problem,
    get_open_problems,
    report_problem,
    resolve_problem,
)


CORPS_ID = "test-corps-1"


class TestProblemReporting:
    def _make_coordinate(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m = create_coordinate(db, CoordinateType.MOVEMENT, "M1", parent_id=show.id)
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m.id)
        return create_coordinate(db, CoordinateType.COORDINATE, "C1", parent_id=s.id)

    def test_report_problem(self, db):
        c = self._make_coordinate(db)
        problem = report_problem(
            db,
            coordinate_id=c.id,
            corps_id=CORPS_ID,
            reported_by_role="performer",
            title="Can't resolve merge conflict",
            description="Files X and Y conflict",
            severity=ProblemSeverity.HIGH,
            reported_by_session_id="session-123",
        )
        assert problem.id is not None
        assert problem.status == ProblemStatus.OPEN
        assert problem.severity == ProblemSeverity.HIGH
        assert problem.reported_by_role == "performer"

    def test_problem_survives_without_session(self, db):
        """Problem persists even though the reporting agent is gone (ephemeral)."""
        c = self._make_coordinate(db)
        problem = report_problem(
            db,
            coordinate_id=c.id,
            corps_id=CORPS_ID,
            reported_by_role="performer",
            title="Stuck on this",
            reported_by_session_id="dead-session",
        )
        # The session is "dead" but the problem persists
        fetched = get_open_problems(db, coordinate_id=c.id)
        assert len(fetched) == 1
        assert fetched[0].id == problem.id

    def test_multiple_problems_per_coordinate(self, db):
        c = self._make_coordinate(db)
        report_problem(db, c.id, CORPS_ID, "performer", "Problem 1")
        report_problem(db, c.id, CORPS_ID, "performer", "Problem 2")

        problems = get_open_problems(db, coordinate_id=c.id)
        assert len(problems) == 2


class TestProblemLifecycle:
    def _make_coordinate(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m = create_coordinate(db, CoordinateType.MOVEMENT, "M1", parent_id=show.id)
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m.id)
        return create_coordinate(db, CoordinateType.COORDINATE, "C1", parent_id=s.id)

    def test_acknowledge_problem(self, db):
        c = self._make_coordinate(db)
        problem = report_problem(db, c.id, CORPS_ID, "performer", "Issue")
        acked = acknowledge_problem(db, problem.id)
        assert acked.status == ProblemStatus.ACKNOWLEDGED

    def test_resolve_problem(self, db):
        c = self._make_coordinate(db)
        problem = report_problem(db, c.id, CORPS_ID, "performer", "Issue")
        resolved = resolve_problem(
            db, problem.id, "brass_tech", resolution="Fixed the approach"
        )
        assert resolved.status == ProblemStatus.RESOLVED
        assert resolved.resolved_by_role == "brass_tech"
        assert resolved.resolution == "Fixed the approach"
        assert resolved.resolved_at is not None

    def test_resolve_acknowledged_problem(self, db):
        c = self._make_coordinate(db)
        problem = report_problem(db, c.id, CORPS_ID, "performer", "Issue")
        acknowledge_problem(db, problem.id)
        resolved = resolve_problem(db, problem.id, "brass_tech")
        assert resolved.status == ProblemStatus.RESOLVED

    def test_cannot_acknowledge_resolved(self, db):
        c = self._make_coordinate(db)
        problem = report_problem(db, c.id, CORPS_ID, "performer", "Issue")
        resolve_problem(db, problem.id, "brass_tech")
        with pytest.raises(InvalidProblemTransition):
            acknowledge_problem(db, problem.id)

    def test_cannot_resolve_twice(self, db):
        c = self._make_coordinate(db)
        problem = report_problem(db, c.id, CORPS_ID, "performer", "Issue")
        resolve_problem(db, problem.id, "brass_tech")
        with pytest.raises(InvalidProblemTransition):
            resolve_problem(db, problem.id, "brass_tech")

    def test_resolved_excluded_from_open(self, db):
        c = self._make_coordinate(db)
        p1 = report_problem(db, c.id, CORPS_ID, "performer", "Open issue")
        p2 = report_problem(db, c.id, CORPS_ID, "performer", "Resolved issue")
        resolve_problem(db, p2.id, "brass_tech")

        open_problems = get_open_problems(db, coordinate_id=c.id)
        assert len(open_problems) == 1
        assert open_problems[0].id == p1.id

    def test_filter_by_corps(self, db):
        c = self._make_coordinate(db)
        report_problem(db, c.id, "corps-1", "performer", "Corps 1 problem")
        report_problem(db, c.id, "corps-2", "performer", "Corps 2 problem")

        problems = get_open_problems(db, corps_id="corps-1")
        assert len(problems) == 1
        assert problems[0].title == "Corps 1 problem"
