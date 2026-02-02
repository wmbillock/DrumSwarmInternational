"""Regression tests for admin ping rep counting."""

import uuid

from backend.models.rep import Rep, RepStatus
from backend.models.segment import Segment, SegmentType
from backend.services.task_manager import _count_reps_for_show


def test_count_reps_for_show_filters_by_tree(db):
    root_a = str(uuid.uuid4())
    root_b = str(uuid.uuid4())
    child_a = str(uuid.uuid4())

    db.add_all(
        [
            Segment(id=root_a, type=SegmentType.SHOW, title="Show A"),
            Segment(id=child_a, parent_id=root_a, type=SegmentType.SET, title="A1"),
            Segment(id=root_b, type=SegmentType.SHOW, title="Show B"),
        ]
    )
    db.add_all(
        [
            Rep(segment_id=child_a, status=RepStatus.PENDING),
            Rep(segment_id=root_b, status=RepStatus.COMPLETED),
        ]
    )
    db.commit()

    counts = _count_reps_for_show(db, root_a)
    assert counts is not None
    assert counts["pending"] == 1
    assert counts["completed"] == 0
    assert counts["failed"] == 0
    assert counts["in_progress"] == 0
