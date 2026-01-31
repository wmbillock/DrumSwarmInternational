import pytest

from backend.models.coordinate import CoordinateStatus, CoordinateType
from backend.models.rep import RepStatus
from backend.services.coordinate_service import create_coordinate
from backend.services.rep_service import (
    InvalidRepTransition,
    create_rep,
    get_reps_for_coordinate,
    transition_rep,
)


class TestRepCreation:
    def test_create_rep(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m = create_coordinate(db, CoordinateType.MOVEMENT, "M1", parent_id=show.id)
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m.id)
        c = create_coordinate(
            db, CoordinateType.COORDINATE, "C1", parent_id=s.id
        )

        rep = create_rep(db, c.id)
        assert rep.id is not None
        assert rep.coordinate_id == c.id
        assert rep.status == RepStatus.PENDING
        assert rep.assigned_to is None

    def test_multiple_reps_per_coordinate(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m = create_coordinate(db, CoordinateType.MOVEMENT, "M1", parent_id=show.id)
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m.id)
        c = create_coordinate(
            db, CoordinateType.COORDINATE, "C1", parent_id=s.id
        )

        r1 = create_rep(db, c.id)
        r2 = create_rep(db, c.id)

        reps = get_reps_for_coordinate(db, c.id)
        assert len(reps) == 2
        assert {r.id for r in reps} == {r1.id, r2.id}


class TestRepTransitions:
    def _make_coordinate(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m = create_coordinate(db, CoordinateType.MOVEMENT, "M1", parent_id=show.id)
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m.id)
        return create_coordinate(
            db, CoordinateType.COORDINATE, "C1", parent_id=s.id
        )

    def test_pending_to_assigned(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        rep = transition_rep(db, rep.id, RepStatus.ASSIGNED, assigned_to="agent-1")
        assert rep.status == RepStatus.ASSIGNED
        assert rep.assigned_to == "agent-1"

    def test_assigned_to_in_progress(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        rep = transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        assert rep.status == RepStatus.IN_PROGRESS

    def test_in_progress_to_review(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        rep = transition_rep(db, rep.id, RepStatus.REVIEW, result="some output")
        assert rep.status == RepStatus.REVIEW
        assert rep.result == "some output"

    def test_review_to_completed(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="Completed work output for test")
        rep = transition_rep(db, rep.id, RepStatus.COMPLETED)
        assert rep.status == RepStatus.COMPLETED

    def test_in_progress_to_failed(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        rep = transition_rep(db, rep.id, RepStatus.FAILED, error="something broke")
        assert rep.status == RepStatus.FAILED
        assert rep.error == "something broke"

    def test_review_to_failed(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW)
        rep = transition_rep(db, rep.id, RepStatus.FAILED)
        assert rep.status == RepStatus.FAILED

    def test_review_back_to_in_progress(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW)
        rep = transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        assert rep.status == RepStatus.IN_PROGRESS

    def test_assigned_back_to_pending(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        rep = transition_rep(db, rep.id, RepStatus.PENDING)
        assert rep.status == RepStatus.PENDING


class TestInvalidTransitions:
    def _make_coordinate(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m = create_coordinate(db, CoordinateType.MOVEMENT, "M1", parent_id=show.id)
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m.id)
        return create_coordinate(
            db, CoordinateType.COORDINATE, "C1", parent_id=s.id
        )

    def test_pending_to_in_progress_rejected(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        with pytest.raises(InvalidRepTransition):
            transition_rep(db, rep.id, RepStatus.IN_PROGRESS)

    def test_pending_to_completed_rejected(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        with pytest.raises(InvalidRepTransition):
            transition_rep(db, rep.id, RepStatus.COMPLETED)

    def test_completed_to_anything_rejected(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="Completed work output for test")
        transition_rep(db, rep.id, RepStatus.COMPLETED)
        with pytest.raises(InvalidRepTransition):
            transition_rep(db, rep.id, RepStatus.PENDING)

    def test_failed_to_anything_rejected(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.FAILED)
        with pytest.raises(InvalidRepTransition):
            transition_rep(db, rep.id, RepStatus.PENDING)

    def test_pending_to_review_rejected(self, db):
        c = self._make_coordinate(db)
        rep = create_rep(db, c.id)
        with pytest.raises(InvalidRepTransition):
            transition_rep(db, rep.id, RepStatus.REVIEW)


class TestRepCoordinateSync:
    def _build_tree(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m = create_coordinate(db, CoordinateType.MOVEMENT, "M1", parent_id=show.id)
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m.id)
        c = create_coordinate(
            db, CoordinateType.COORDINATE, "C1", parent_id=s.id
        )
        return show, m, s, c

    def test_rep_completion_updates_coordinate(self, db):
        show, m, s, c = self._build_tree(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="Completed work output for test")
        transition_rep(db, rep.id, RepStatus.COMPLETED)

        db.refresh(c)
        assert c.status == CoordinateStatus.COMPLETED

    def test_rep_completion_propagates_up_tree(self, db):
        show, m, s, c = self._build_tree(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="Completed work output for test")
        transition_rep(db, rep.id, RepStatus.COMPLETED)

        db.refresh(s)
        db.refresh(m)
        db.refresh(show)
        assert s.status == CoordinateStatus.COMPLETED
        assert m.status == CoordinateStatus.COMPLETED
        assert show.status == CoordinateStatus.COMPLETED

    def test_rep_in_progress_updates_coordinate(self, db):
        show, m, s, c = self._build_tree(db)
        rep = create_rep(db, c.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED)
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)

        db.refresh(c)
        assert c.status == CoordinateStatus.IN_PROGRESS

    def test_first_rep_fails_second_succeeds(self, db):
        show, m, s, c = self._build_tree(db)

        # First rep fails
        r1 = create_rep(db, c.id)
        transition_rep(db, r1.id, RepStatus.ASSIGNED)
        transition_rep(db, r1.id, RepStatus.IN_PROGRESS)
        transition_rep(db, r1.id, RepStatus.FAILED)

        db.refresh(c)
        assert c.status == CoordinateStatus.FAILED

        # Second rep succeeds
        r2 = create_rep(db, c.id)
        transition_rep(db, r2.id, RepStatus.ASSIGNED)
        transition_rep(db, r2.id, RepStatus.IN_PROGRESS)
        transition_rep(db, r2.id, RepStatus.REVIEW, result="Completed work output for test")
        transition_rep(db, r2.id, RepStatus.COMPLETED)

        db.refresh(c)
        assert c.status == CoordinateStatus.COMPLETED

    def test_rep_failure_all_reps_failed(self, db):
        show, m, s, c = self._build_tree(db)
        r1 = create_rep(db, c.id)
        r2 = create_rep(db, c.id)
        transition_rep(db, r1.id, RepStatus.ASSIGNED)
        transition_rep(db, r1.id, RepStatus.IN_PROGRESS)
        transition_rep(db, r1.id, RepStatus.FAILED)
        transition_rep(db, r2.id, RepStatus.ASSIGNED)
        transition_rep(db, r2.id, RepStatus.IN_PROGRESS)
        transition_rep(db, r2.id, RepStatus.FAILED)

        db.refresh(c)
        assert c.status == CoordinateStatus.FAILED
