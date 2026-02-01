"""Tests for Ready-for-Contest lifecycle transitions and evaluation gate."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.corps import Corps, CorpsStatus, RehearsalMode
from backend.models.segment import Segment, SegmentStatus
from backend.models.rep import Rep, RepStatus
from backend.services.corps_service import ready_for_contest, complete_corps
from fastapi.exceptions import HTTPException


@pytest.fixture
def db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def create_test_corps(db, corps_id: str = "test-corps", status: str = "on_tour", mode: str = "run_through") -> Corps:
    """Create a test corps with specified status and mode."""
    corps = Corps(
        id=corps_id,
        name=f"Test Corps {corps_id}",
        status=CorpsStatus(status),
        rehearsal_mode=RehearsalMode(mode),
        philosophy="Test philosophy",
        mascot="Test Mascot",
    )
    db.add(corps)
    db.commit()
    db.refresh(corps)
    return corps


def create_test_segments(db, corps_id: str, statuses: list[str] = None) -> list[Segment]:
    """Create test segments with specified statuses."""
    if statuses is None:
        statuses = ["completed", "completed", "completed"]

    segments = []
    for i, status in enumerate(statuses):
        seg = Segment(
            id=f"seg-{corps_id}-{i}",
            parent_id=None,
            title=f"Segment {i}",
            description=f"Test segment {i}",
            corps_id=corps_id,
            status=SegmentStatus(status),
        )
        db.add(seg)
        segments.append(seg)
    db.commit()
    return segments


# =========================================================================
# State Transition Tests
# =========================================================================


class TestReadyForContestTransition:
    """Tests for ON_TOUR → READY_FOR_CONTEST transition."""

    def test_transition_from_on_tour_succeeds(self, db):
        """Test successful transition from ON_TOUR to READY_FOR_CONTEST."""
        corps = create_test_corps(db, status="on_tour")
        create_test_segments(db, corps.id, ["completed", "completed"])

        result = ready_for_contest(db, corps.id)

        assert result.status == CorpsStatus.READY_FOR_CONTEST
        assert result.rehearsal_mode == RehearsalMode.RUN_THROUGH  # Preserved

    def test_transition_fails_from_winter_camps(self, db):
        """Test that transition from WINTER_CAMPS fails."""
        corps = create_test_corps(db, status="winter_camps")

        with pytest.raises(HTTPException) as exc_info:
            ready_for_contest(db, corps.id)

        assert exc_info.value.status_code == 400
        assert "must be ON_TOUR" in str(exc_info.value.detail)

    def test_transition_fails_from_completed(self, db):
        """Test that transition from COMPLETED fails."""
        corps = create_test_corps(db, status="completed")

        with pytest.raises(HTTPException) as exc_info:
            ready_for_contest(db, corps.id)

        assert exc_info.value.status_code == 400

    def test_transition_preserves_rehearsal_mode(self, db):
        """Test that rehearsal mode is preserved during transition."""
        for mode in ["basics", "sectionals", "full_ensemble", "run_through"]:
            corps = create_test_corps(db, corps_id=f"corps-{mode}", status="on_tour", mode=mode)
            create_test_segments(db, corps.id)

            result = ready_for_contest(db, corps.id)

            assert result.rehearsal_mode == RehearsalMode(mode)


class TestCompleteCorpsTransition:
    """Tests for READY_FOR_CONTEST → COMPLETED transition with evaluation gate."""

    def test_complete_succeeds_with_run_through_and_completed_segments(self, db):
        """Test successful completion with RUN_THROUGH mode and all segments completed."""
        corps = create_test_corps(db, status="ready_for_contest", mode="run_through")
        create_test_segments(db, corps.id, ["completed", "completed", "completed"])

        result = complete_corps(db, corps.id)

        assert result.status == CorpsStatus.COMPLETED

    def test_complete_succeeds_with_full_ensemble_and_completed_segments(self, db):
        """Test successful completion with FULL_ENSEMBLE mode."""
        corps = create_test_corps(db, status="ready_for_contest", mode="full_ensemble")
        create_test_segments(db, corps.id, ["completed"])

        result = complete_corps(db, corps.id)

        assert result.status == CorpsStatus.COMPLETED

    def test_complete_fails_with_basics_mode(self, db):
        """Test that completion fails with BASICS rehearsal mode."""
        corps = create_test_corps(db, status="ready_for_contest", mode="basics")
        create_test_segments(db, corps.id, ["completed"])

        with pytest.raises(HTTPException) as exc_info:
            complete_corps(db, corps.id)

        assert exc_info.value.status_code == 400
        assert "FULL_ENSEMBLE or RUN_THROUGH" in str(exc_info.value.detail)

    def test_complete_fails_with_sectionals_mode(self, db):
        """Test that completion fails with SECTIONALS rehearsal mode."""
        corps = create_test_corps(db, status="ready_for_contest", mode="sectionals")
        create_test_segments(db, corps.id, ["completed"])

        with pytest.raises(HTTPException) as exc_info:
            complete_corps(db, corps.id)

        assert exc_info.value.status_code == 400

    def test_complete_fails_with_pending_segments(self, db):
        """Test that completion fails if any segments are PENDING."""
        corps = create_test_corps(db, status="ready_for_contest")
        create_test_segments(db, corps.id, ["completed", "pending", "completed"])

        with pytest.raises(HTTPException) as exc_info:
            complete_corps(db, corps.id)

        assert exc_info.value.status_code == 400
        assert "all segments" in str(exc_info.value.detail).lower()

    def test_complete_fails_with_in_progress_segments(self, db):
        """Test that completion fails if any segments are IN_PROGRESS."""
        corps = create_test_corps(db, status="ready_for_contest")
        create_test_segments(db, corps.id, ["completed", "in_progress", "completed"])

        with pytest.raises(HTTPException) as exc_info:
            complete_corps(db, corps.id)

        assert exc_info.value.status_code == 400

    def test_complete_fails_with_review_segments(self, db):
        """Test that completion fails if any segments are REVIEW."""
        corps = create_test_corps(db, status="ready_for_contest")
        create_test_segments(db, corps.id, ["completed", "review", "completed"])

        with pytest.raises(HTTPException) as exc_info:
            complete_corps(db, corps.id)

        assert exc_info.value.status_code == 400

    def test_complete_fails_with_blocked_segments(self, db):
        """Test that completion fails if any segments are BLOCKED."""
        corps = create_test_corps(db, status="ready_for_contest")
        create_test_segments(db, corps.id, ["completed", "blocked", "completed"])

        with pytest.raises(HTTPException) as exc_info:
            complete_corps(db, corps.id)

        assert exc_info.value.status_code == 400

    def test_complete_fails_with_failed_segments(self, db):
        """Test that completion fails if any segments are FAILED."""
        corps = create_test_corps(db, status="ready_for_contest")
        create_test_segments(db, corps.id, ["completed", "failed", "completed"])

        with pytest.raises(HTTPException) as exc_info:
            complete_corps(db, corps.id)

        assert exc_info.value.status_code == 400

    def test_complete_fails_if_not_ready_for_contest(self, db):
        """Test that completion fails if corps is not in READY_FOR_CONTEST state."""
        corps = create_test_corps(db, status="on_tour")
        create_test_segments(db, corps.id, ["completed"])

        with pytest.raises(HTTPException) as exc_info:
            complete_corps(db, corps.id)

        assert exc_info.value.status_code == 400
        assert "READY_FOR_CONTEST" in str(exc_info.value.detail)


class TestReturnToTourTransition:
    """Tests for READY_FOR_CONTEST → ON_TOUR transition (rework)."""

    def test_return_to_tour_from_ready_for_contest(self, db):
        """Test successful return to ON_TOUR from READY_FOR_CONTEST."""
        corps = create_test_corps(db, status="ready_for_contest", mode="run_through")

        # Import the return function (need to check if it exists)
        from backend.services.corps_service import return_to_tour

        result = return_to_tour(db, corps.id)

        assert result.status == CorpsStatus.ON_TOUR
        assert result.rehearsal_mode == RehearsalMode.RUN_THROUGH  # Preserved

    def test_return_to_tour_fails_from_on_tour(self, db):
        """Test that return fails if already ON_TOUR."""
        corps = create_test_corps(db, status="on_tour")

        from backend.services.corps_service import return_to_tour

        with pytest.raises(HTTPException) as exc_info:
            return_to_tour(db, corps.id)

        assert exc_info.value.status_code == 400


class TestStateMachineIntegrity:
    """Tests for overall state machine integrity and constraints."""

    def test_full_lifecycle_cycle(self, db):
        """Test complete lifecycle: ON_TOUR → READY_FOR_CONTEST → COMPLETED."""
        corps = create_test_corps(db, status="on_tour")
        create_test_segments(db, corps.id, ["completed"])

        # ON_TOUR → READY_FOR_CONTEST
        corps = ready_for_contest(db, corps.id)
        assert corps.status == CorpsStatus.READY_FOR_CONTEST

        # READY_FOR_CONTEST → COMPLETED
        corps = complete_corps(db, corps.id)
        assert corps.status == CorpsStatus.COMPLETED

    def test_rework_cycle(self, db):
        """Test rework cycle: ON_TOUR → READY_FOR_CONTEST → ON_TOUR."""
        corps = create_test_corps(db, status="on_tour")
        create_test_segments(db, corps.id, ["completed"])

        # ON_TOUR → READY_FOR_CONTEST
        corps = ready_for_contest(db, corps.id)
        assert corps.status == CorpsStatus.READY_FOR_CONTEST

        # READY_FOR_CONTEST → ON_TOUR (rework)
        from backend.services.corps_service import return_to_tour
        corps = return_to_tour(db, corps.id)
        assert corps.status == CorpsStatus.ON_TOUR

        # Can go back to READY_FOR_CONTEST
        corps = ready_for_contest(db, corps.id)
        assert corps.status == CorpsStatus.READY_FOR_CONTEST

    def test_cannot_skip_ready_for_contest_state(self, db):
        """Test that ON_TOUR corps cannot go directly to COMPLETED."""
        corps = create_test_corps(db, status="on_tour")
        create_test_segments(db, corps.id, ["completed"])

        with pytest.raises(HTTPException):
            complete_corps(db, corps.id)

    def test_corps_id_validation(self, db):
        """Test that operations fail for non-existent corps."""
        with pytest.raises(HTTPException) as exc_info:
            ready_for_contest(db, "nonexistent-corps")

        assert exc_info.value.status_code == 404

    def test_status_preserved_on_error(self, db):
        """Test that corps status is unchanged when transition fails."""
        corps = create_test_corps(db, status="on_tour")
        create_test_segments(db, corps.id, ["pending"])

        original_status = corps.status

        with pytest.raises(HTTPException):
            complete_corps(db, corps.id)

        # Refresh from DB to get latest state
        db.refresh(corps)
        assert corps.status == original_status


class TestEvaluationGateDetails:
    """Detailed tests for the evaluation gate logic."""

    def test_evaluation_gate_all_segment_statuses(self, db):
        """Test evaluation gate against all invalid segment statuses."""
        invalid_statuses = ["pending", "in_progress", "review", "blocked", "failed"]

        for invalid_status in invalid_statuses:
            corps = create_test_corps(db, corps_id=f"corps-{invalid_status}", status="ready_for_contest")
            create_test_segments(db, corps.id, ["completed", invalid_status, "completed"])

            with pytest.raises(HTTPException) as exc_info:
                complete_corps(db, corps.id)

            assert exc_info.value.status_code == 400

    def test_evaluation_gate_mixed_valid_statuses(self, db):
        """Test that only COMPLETED segments pass evaluation."""
        # COMPLETED is the only valid status
        corps = create_test_corps(db, status="ready_for_contest")
        create_test_segments(db, corps.id, ["completed", "completed", "completed", "completed"])

        result = complete_corps(db, corps.id)
        assert result.status == CorpsStatus.COMPLETED

    def test_empty_segments_list_allows_completion(self, db):
        """Test that corps with no segments can complete."""
        corps = create_test_corps(db, status="ready_for_contest")
        # Don't create any segments

        result = complete_corps(db, corps.id)
        assert result.status == CorpsStatus.COMPLETED
