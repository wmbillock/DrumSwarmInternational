import pytest

from backend.models.coordinate import CoordinateStatus, CoordinateType
from backend.services.coordinate_service import (
    InvalidCoordinateStructure,
    create_coordinate,
    get_children,
    get_coordinate,
    rollup_status,
    update_status_from_children,
)


class TestCoordinateCreation:
    def test_create_show(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "My Show")
        assert show.id is not None
        assert show.type == CoordinateType.SHOW
        assert show.title == "My Show"
        assert show.status == CoordinateStatus.PENDING
        assert show.parent_id is None

    def test_create_movement_under_show(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        movement = create_coordinate(
            db, CoordinateType.MOVEMENT, "Movement 1", parent_id=show.id
        )
        assert movement.parent_id == show.id
        assert movement.type == CoordinateType.MOVEMENT

    def test_create_set_under_movement(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        movement = create_coordinate(
            db, CoordinateType.MOVEMENT, "M1", parent_id=show.id
        )
        s = create_coordinate(
            db, CoordinateType.SET, "Set 1", parent_id=movement.id, caption="brass"
        )
        assert s.parent_id == movement.id
        assert s.caption == "brass"

    def test_create_coordinate_under_set(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        movement = create_coordinate(
            db, CoordinateType.MOVEMENT, "M1", parent_id=show.id
        )
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=movement.id)
        coord = create_coordinate(
            db, CoordinateType.COORDINATE, "Implement login", parent_id=s.id
        )
        assert coord.parent_id == s.id
        assert coord.type == CoordinateType.COORDINATE

    def test_full_tree(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m1 = create_coordinate(
            db, CoordinateType.MOVEMENT, "M1", parent_id=show.id
        )
        s1 = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m1.id)
        c1 = create_coordinate(
            db, CoordinateType.COORDINATE, "C1", parent_id=s1.id
        )
        c2 = create_coordinate(
            db, CoordinateType.COORDINATE, "C2", parent_id=s1.id
        )

        children = get_children(db, s1.id)
        assert len(children) == 2
        assert {c.id for c in children} == {c1.id, c2.id}


class TestInvalidStructure:
    def test_non_show_root_rejected(self, db):
        with pytest.raises(InvalidCoordinateStructure, match="Only shows"):
            create_coordinate(db, CoordinateType.MOVEMENT, "M1")

    def test_movement_under_movement_rejected(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m1 = create_coordinate(
            db, CoordinateType.MOVEMENT, "M1", parent_id=show.id
        )
        with pytest.raises(InvalidCoordinateStructure, match="Cannot add"):
            create_coordinate(
                db, CoordinateType.MOVEMENT, "M2", parent_id=m1.id
            )

    def test_coordinate_under_show_rejected(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        with pytest.raises(InvalidCoordinateStructure, match="Cannot add"):
            create_coordinate(
                db, CoordinateType.COORDINATE, "C1", parent_id=show.id
            )

    def test_set_under_show_rejected(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        with pytest.raises(InvalidCoordinateStructure, match="Cannot add"):
            create_coordinate(db, CoordinateType.SET, "S1", parent_id=show.id)

    def test_children_under_coordinate_rejected(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m = create_coordinate(db, CoordinateType.MOVEMENT, "M1", parent_id=show.id)
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m.id)
        c = create_coordinate(
            db, CoordinateType.COORDINATE, "C1", parent_id=s.id
        )
        with pytest.raises(InvalidCoordinateStructure, match="Cannot add"):
            create_coordinate(
                db, CoordinateType.COORDINATE, "C2", parent_id=c.id
            )

    def test_nonexistent_parent_rejected(self, db):
        with pytest.raises(InvalidCoordinateStructure, match="not found"):
            create_coordinate(
                db, CoordinateType.MOVEMENT, "M1", parent_id="nonexistent"
            )


class TestStatusRollup:
    def _build_tree(self, db):
        """Build a show → movement → set → 2 coordinates tree."""
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m = create_coordinate(db, CoordinateType.MOVEMENT, "M1", parent_id=show.id)
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m.id)
        c1 = create_coordinate(
            db, CoordinateType.COORDINATE, "C1", parent_id=s.id
        )
        c2 = create_coordinate(
            db, CoordinateType.COORDINATE, "C2", parent_id=s.id
        )
        return show, m, s, c1, c2

    def test_all_pending(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        assert rollup_status(db, s.id) == CoordinateStatus.PENDING

    def test_all_completed(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = CoordinateStatus.COMPLETED
        c2.status = CoordinateStatus.COMPLETED
        db.commit()
        assert rollup_status(db, s.id) == CoordinateStatus.COMPLETED

    def test_one_in_progress(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = CoordinateStatus.IN_PROGRESS
        db.commit()
        assert rollup_status(db, s.id) == CoordinateStatus.IN_PROGRESS

    def test_one_failed_one_pending(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = CoordinateStatus.FAILED
        db.commit()
        # One failed, one pending → still in_progress (work remains)
        assert rollup_status(db, s.id) == CoordinateStatus.IN_PROGRESS

    def test_all_failed(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = CoordinateStatus.FAILED
        c2.status = CoordinateStatus.FAILED
        db.commit()
        assert rollup_status(db, s.id) == CoordinateStatus.FAILED

    def test_one_blocked(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = CoordinateStatus.BLOCKED
        db.commit()
        assert rollup_status(db, s.id) == CoordinateStatus.BLOCKED

    def test_rollup_propagates_up_tree(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = CoordinateStatus.COMPLETED
        c2.status = CoordinateStatus.COMPLETED
        db.commit()

        update_status_from_children(db, s.id)

        db.refresh(s)
        db.refresh(m)
        db.refresh(show)
        assert s.status == CoordinateStatus.COMPLETED
        assert m.status == CoordinateStatus.COMPLETED
        assert show.status == CoordinateStatus.COMPLETED

    def test_leaf_node_returns_own_status(self, db):
        show = create_coordinate(db, CoordinateType.SHOW, "Show")
        m = create_coordinate(db, CoordinateType.MOVEMENT, "M1", parent_id=show.id)
        s = create_coordinate(db, CoordinateType.SET, "S1", parent_id=m.id)
        c = create_coordinate(
            db, CoordinateType.COORDINATE, "C1", parent_id=s.id
        )
        c.status = CoordinateStatus.IN_PROGRESS
        db.commit()
        assert rollup_status(db, c.id) == CoordinateStatus.IN_PROGRESS
