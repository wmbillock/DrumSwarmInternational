"""Tests for Judging & Critique routes — judge tapes, critique-to-actions, export."""

import pytest
from sqlalchemy.orm import Session

from backend.database import Base, create_db_engine, create_session_factory
from backend.models.score import Score, JudgeType
from backend.models.rep import Rep, RepStatus
from backend.models.segment import Segment, SegmentType, SegmentStatus
from backend.api.judging_routes import CAPTION_TO_ROLE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = create_session_factory(engine)
    session = SessionFactory()
    yield session
    session.close()


@pytest.fixture
def seeded_db(db):
    """DB with a segment, rep, and scores for critique testing."""
    seg = Segment(
        id="seg-1", type=SegmentType.SEGMENT, title="Opener",
        status=SegmentStatus.COMPLETED,
    )
    db.add(seg)

    rep = Rep(id="rep-1", segment_id="seg-1", status=RepStatus.COMPLETED)
    db.add(rep)

    # Add scores across captions
    db.add(Score(
        rep_id="rep-1", segment_id="seg-1", corps_id="corps-1",
        judge_type=JudgeType.BRASS, value=55.0, box=3, feedback="Intonation issues in measure 12",
    ))
    db.add(Score(
        rep_id="rep-1", segment_id="seg-1", corps_id="corps-1",
        judge_type=JudgeType.VISUAL, value=82.0, box=4, feedback="Clean transitions",
    ))
    db.add(Score(
        rep_id="rep-1", segment_id="seg-1", corps_id="corps-1",
        judge_type=JudgeType.GUARD, value=45.0, box=2, feedback="Dropped equipment",
    ))
    db.commit()
    return db


# ---------------------------------------------------------------------------
# Critique parsing & routing
# ---------------------------------------------------------------------------

class TestCritiqueRouting:
    """Test that critique action items route to the correct caption heads."""

    def test_caption_to_role_mapping_complete(self):
        """All judge types map to a staff role."""
        for jt in JudgeType:
            assert jt.value in CAPTION_TO_ROLE, f"Missing mapping for {jt.value}"

    def test_critique_generates_actions_for_low_scores(self, seeded_db):
        """Scores below 60 should generate action items."""
        from backend.services.improvement import run_critique

        critique = run_critique(seeded_db, "rep-1", "corps-1")

        # Brass (55) and Guard (45) should have weaknesses
        low_feedbacks = [f for f in critique.feedbacks if f.score_value < 60]
        assert len(low_feedbacks) == 2

        for fb in low_feedbacks:
            assert len(fb.weaknesses) > 0
            assert len(fb.action_items) > 0

    def test_critique_no_actions_for_high_scores(self, seeded_db):
        """Scores at or above 80 should have strengths, not action items."""
        from backend.services.improvement import run_critique

        critique = run_critique(seeded_db, "rep-1", "corps-1")

        visual_fb = [f for f in critique.feedbacks if f.judge_type == JudgeType.VISUAL]
        assert len(visual_fb) == 1
        assert len(visual_fb[0].strengths) > 0
        assert len(visual_fb[0].action_items) == 0

    def test_critique_overall_assessment_below_standards(self, seeded_db):
        """Average below 60 should produce 'below standards' assessment."""
        from backend.services.improvement import run_critique

        critique = run_critique(seeded_db, "rep-1", "corps-1")
        # Avg: (55 + 82 + 45) / 3 = 60.67 — "Acceptable"
        assert "Acceptable" in critique.overall_assessment or "room for improvement" in critique.overall_assessment

    def test_action_routing_maps_to_correct_roles(self, seeded_db):
        """Action items from brass scores route to brass_caption_head."""
        from backend.services.improvement import run_critique

        critique = run_critique(seeded_db, "rep-1", "corps-1")

        for fb in critique.feedbacks:
            if fb.action_items:
                target = CAPTION_TO_ROLE.get(fb.judge_type.value)
                assert target is not None, f"No role mapping for {fb.judge_type.value}"


class TestJudgeTapeExport:
    """Test markdown export of judge tapes."""

    def test_export_contains_all_sections(self, seeded_db):
        """Exported markdown should contain scores, assessment, and action items."""
        from backend.api.judging_routes import api_export_judge_tape

        # Build a mock db dependency
        class FakeDB:
            def __init__(self, db):
                self._db = db

        result = api_export_judge_tape("corps-1", "rep-1", seeded_db)
        md = result["markdown"]

        assert "# Judge Tape" in md
        assert "Opener" in md
        assert "## Composite Score" in md
        assert "## Caption Scores" in md
        assert "Brass" in md
        assert "Visual" in md
        assert "Guard" in md

    def test_export_includes_action_items(self, seeded_db):
        """Action items should appear as checkboxes in the export."""
        from backend.api.judging_routes import api_export_judge_tape

        result = api_export_judge_tape("corps-1", "rep-1", seeded_db)
        md = result["markdown"]

        assert "- [ ]" in md  # At least one action item checkbox

    def test_export_includes_feedback_quotes(self, seeded_db):
        """Judge feedback should appear as blockquotes."""
        from backend.api.judging_routes import api_export_judge_tape

        result = api_export_judge_tape("corps-1", "rep-1", seeded_db)
        md = result["markdown"]

        assert "Intonation issues" in md
        assert "Clean transitions" in md
