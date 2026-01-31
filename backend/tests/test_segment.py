import pytest

from backend.models.segment import SegmentStatus, SegmentType
from backend.services.segment_service import (
    InvalidSegmentStructure,
    create_segment,
    get_children,
    get_segment,
    rollup_status,
    update_status_from_children,
)


class TestSegmentCreation:
    def test_create_show(self, db):
        show = create_segment(db, SegmentType.SHOW, "My Show")
        assert show.id is not None
        assert show.type == SegmentType.SHOW
        assert show.title == "My Show"
        assert show.status == SegmentStatus.PENDING
        assert show.parent_id is None

    def test_create_movement_under_show(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        movement = create_segment(
            db, SegmentType.MOVEMENT, "Movement 1", parent_id=show.id
        )
        assert movement.parent_id == show.id
        assert movement.type == SegmentType.MOVEMENT

    def test_create_set_under_movement(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        movement = create_segment(
            db, SegmentType.MOVEMENT, "M1", parent_id=show.id
        )
        s = create_segment(
            db, SegmentType.SET, "Set 1", parent_id=movement.id, caption="brass"
        )
        assert s.parent_id == movement.id
        assert s.caption == "brass"

    def test_create_segment_under_set(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        movement = create_segment(
            db, SegmentType.MOVEMENT, "M1", parent_id=show.id
        )
        s = create_segment(db, SegmentType.SET, "S1", parent_id=movement.id)
        coord = create_segment(
            db, SegmentType.SEGMENT, "Implement login", parent_id=s.id
        )
        assert coord.parent_id == s.id
        assert coord.type == SegmentType.SEGMENT

    def test_full_tree(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        m1 = create_segment(
            db, SegmentType.MOVEMENT, "M1", parent_id=show.id
        )
        s1 = create_segment(db, SegmentType.SET, "S1", parent_id=m1.id)
        c1 = create_segment(
            db, SegmentType.SEGMENT, "C1", parent_id=s1.id
        )
        c2 = create_segment(
            db, SegmentType.SEGMENT, "C2", parent_id=s1.id
        )

        children = get_children(db, s1.id)
        assert len(children) == 2
        assert {c.id for c in children} == {c1.id, c2.id}


class TestInvalidStructure:
    def test_non_show_root_rejected(self, db):
        with pytest.raises(InvalidSegmentStructure, match="Only shows"):
            create_segment(db, SegmentType.MOVEMENT, "M1")

    def test_movement_under_movement_rejected(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        m1 = create_segment(
            db, SegmentType.MOVEMENT, "M1", parent_id=show.id
        )
        with pytest.raises(InvalidSegmentStructure, match="Cannot add"):
            create_segment(
                db, SegmentType.MOVEMENT, "M2", parent_id=m1.id
            )

    def test_segment_under_show_rejected(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        with pytest.raises(InvalidSegmentStructure, match="Cannot add"):
            create_segment(
                db, SegmentType.SEGMENT, "C1", parent_id=show.id
            )

    def test_set_under_show_rejected(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        with pytest.raises(InvalidSegmentStructure, match="Cannot add"):
            create_segment(db, SegmentType.SET, "S1", parent_id=show.id)

    def test_children_under_segment_rejected(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        m = create_segment(db, SegmentType.MOVEMENT, "M1", parent_id=show.id)
        s = create_segment(db, SegmentType.SET, "S1", parent_id=m.id)
        c = create_segment(
            db, SegmentType.SEGMENT, "C1", parent_id=s.id
        )
        with pytest.raises(InvalidSegmentStructure, match="Cannot add"):
            create_segment(
                db, SegmentType.SEGMENT, "C2", parent_id=c.id
            )

    def test_nonexistent_parent_rejected(self, db):
        with pytest.raises(InvalidSegmentStructure, match="not found"):
            create_segment(
                db, SegmentType.MOVEMENT, "M1", parent_id="nonexistent"
            )


class TestStatusRollup:
    def _build_tree(self, db):
        """Build a show → movement → set → 2 segments tree."""
        show = create_segment(db, SegmentType.SHOW, "Show")
        m = create_segment(db, SegmentType.MOVEMENT, "M1", parent_id=show.id)
        s = create_segment(db, SegmentType.SET, "S1", parent_id=m.id)
        c1 = create_segment(
            db, SegmentType.SEGMENT, "C1", parent_id=s.id
        )
        c2 = create_segment(
            db, SegmentType.SEGMENT, "C2", parent_id=s.id
        )
        return show, m, s, c1, c2

    def test_all_pending(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        assert rollup_status(db, s.id) == SegmentStatus.PENDING

    def test_all_completed(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = SegmentStatus.COMPLETED
        c2.status = SegmentStatus.COMPLETED
        db.commit()
        assert rollup_status(db, s.id) == SegmentStatus.COMPLETED

    def test_one_in_progress(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = SegmentStatus.IN_PROGRESS
        db.commit()
        assert rollup_status(db, s.id) == SegmentStatus.IN_PROGRESS

    def test_one_failed_one_pending(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = SegmentStatus.FAILED
        db.commit()
        # One failed, one pending → still in_progress (work remains)
        assert rollup_status(db, s.id) == SegmentStatus.IN_PROGRESS

    def test_all_failed(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = SegmentStatus.FAILED
        c2.status = SegmentStatus.FAILED
        db.commit()
        assert rollup_status(db, s.id) == SegmentStatus.FAILED

    def test_one_blocked(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = SegmentStatus.BLOCKED
        db.commit()
        assert rollup_status(db, s.id) == SegmentStatus.BLOCKED

    def test_rollup_propagates_up_tree(self, db):
        show, m, s, c1, c2 = self._build_tree(db)
        c1.status = SegmentStatus.COMPLETED
        c2.status = SegmentStatus.COMPLETED
        db.commit()

        update_status_from_children(db, s.id)

        db.refresh(s)
        db.refresh(m)
        db.refresh(show)
        assert s.status == SegmentStatus.COMPLETED
        assert m.status == SegmentStatus.COMPLETED
        assert show.status == SegmentStatus.COMPLETED

    def test_leaf_node_returns_own_status(self, db):
        show = create_segment(db, SegmentType.SHOW, "Show")
        m = create_segment(db, SegmentType.MOVEMENT, "M1", parent_id=show.id)
        s = create_segment(db, SegmentType.SET, "S1", parent_id=m.id)
        c = create_segment(
            db, SegmentType.SEGMENT, "C1", parent_id=s.id
        )
        c.status = SegmentStatus.IN_PROGRESS
        db.commit()
        assert rollup_status(db, c.id) == SegmentStatus.IN_PROGRESS
