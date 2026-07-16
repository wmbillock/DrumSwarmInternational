from backend.models.corps import Corps
from backend.models.segment import Segment, SegmentType
from backend.models.show import Show
from backend.services.season_invariants import (
    SeasonBlocker,
    check_corps_ready_for_tour,
)


def test_tour_readiness_reports_missing_corps(db):
    blockers = check_corps_ready_for_tour(db, corps_id="missing-corps")

    assert blockers == [
        SeasonBlocker(
            code="missing_corps",
            message="Corps does not exist.",
            corps_id="missing-corps",
        )
    ]


def test_tour_readiness_blocks_uncaptioned_work_segments(db):
    root = Segment(type=SegmentType.SHOW, title="Test Show")
    db.add(root)
    db.flush()
    segment = Segment(
        parent_id=root.id,
        type=SegmentType.SEGMENT,
        title="Uncaptioned feature",
        caption=None,
    )
    show = Show(title="Test Show", segment_root_id=root.id)
    db.add_all([segment, show])
    db.flush()
    corps = Corps(name="Test Corps", show_id=show.id)
    db.add(corps)
    db.commit()

    blockers = check_corps_ready_for_tour(db, corps_id=corps.id)

    assert [blocker.code for blocker in blockers] == ["unroutable_segments"]


def test_tour_readiness_allows_captioned_segment_tree(db):
    root = Segment(type=SegmentType.SHOW, title="Test Show")
    db.add(root)
    db.flush()
    segment = Segment(
        parent_id=root.id,
        type=SegmentType.SEGMENT,
        title="Captioned feature",
        caption="visual",
    )
    show = Show(title="Test Show", segment_root_id=root.id)
    db.add_all([segment, show])
    db.flush()
    corps = Corps(name="Test Corps", show_id=show.id)
    db.add(corps)
    db.commit()

    assert check_corps_ready_for_tour(db, corps_id=corps.id) == []
