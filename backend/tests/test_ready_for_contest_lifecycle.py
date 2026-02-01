"""Tests for Ready-for-Contest lifecycle transitions."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.corps import Corps, CorpsStatus, RehearsalMode
from backend.services.corps_service import ready_for_contest, complete_corps, return_to_tour, CorpsError


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
        mascot="Test Mascot",
    )
    db.add(corps)
    db.commit()
    db.refresh(corps)
    return corps


# =========================================================================
# State Transition Tests
# =========================================================================


class TestReadyForContestTransition:
    """Tests for ON_TOUR → READY_FOR_CONTEST transition."""

    def test_transition_from_on_tour_succeeds(self, db):
        """Test successful transition from ON_TOUR to READY_FOR_CONTEST."""
        corps = create_test_corps(db, status="on_tour")

        result = ready_for_contest(db, corps.id)

        assert result.status == CorpsStatus.READY_FOR_CONTEST
        assert result.rehearsal_mode == RehearsalMode.RUN_THROUGH  # Preserved

    def test_transition_fails_from_winter_camps(self, db):
        """Test that transition from WINTER_CAMPS fails."""
        corps = create_test_corps(db, status="winter_camps")

        with pytest.raises(CorpsError) as exc_info:
            ready_for_contest(db, corps.id)

        assert "must be ON_TOUR" in str(exc_info.value)

    def test_transition_fails_from_completed(self, db):
        """Test that transition from COMPLETED fails."""
        corps = create_test_corps(db, status="completed")

        with pytest.raises(CorpsError):
            ready_for_contest(db, corps.id)

    def test_transition_preserves_rehearsal_mode(self, db):
        """Test that rehearsal mode is preserved during transition."""
        for mode in ["basics", "sectionals", "full_ensemble", "run_through"]:
            corps = create_test_corps(db, corps_id=f"corps-{mode}", status="on_tour", mode=mode)

            result = ready_for_contest(db, corps.id)

            assert result.rehearsal_mode == RehearsalMode(mode)


class TestCompleteCorpsTransition:
    """Tests for READY_FOR_CONTEST → COMPLETED transition with evaluation gate."""

    def test_complete_succeeds_with_run_through(self, db):
        """Test successful completion with RUN_THROUGH mode."""
        corps = create_test_corps(db, status="ready_for_contest", mode="run_through")

        result = complete_corps(db, corps.id)

        assert result.status == CorpsStatus.COMPLETED

    def test_complete_succeeds_with_full_ensemble(self, db):
        """Test successful completion with FULL_ENSEMBLE mode."""
        corps = create_test_corps(db, status="ready_for_contest", mode="full_ensemble")

        result = complete_corps(db, corps.id)

        assert result.status == CorpsStatus.COMPLETED

    def test_complete_fails_with_basics_mode(self, db):
        """Test that completion fails with BASICS rehearsal mode."""
        corps = create_test_corps(db, status="ready_for_contest", mode="basics")

        with pytest.raises(CorpsError) as exc_info:
            complete_corps(db, corps.id)

        assert "FULL_ENSEMBLE" in str(exc_info.value)

    def test_complete_fails_with_sectionals_mode(self, db):
        """Test that completion fails with SECTIONALS rehearsal mode."""
        corps = create_test_corps(db, status="ready_for_contest", mode="sectionals")

        with pytest.raises(CorpsError):
            complete_corps(db, corps.id)

    def test_complete_fails_if_not_ready_for_contest(self, db):
        """Test that completion fails if corps is not in READY_FOR_CONTEST state."""
        corps = create_test_corps(db, status="on_tour")

        with pytest.raises(CorpsError) as exc_info:
            complete_corps(db, corps.id)

        assert "READY_FOR_CONTEST" in str(exc_info.value)


class TestReturnToTourTransition:
    """Tests for READY_FOR_CONTEST → ON_TOUR transition (rework)."""

    def test_return_to_tour_from_ready_for_contest(self, db):
        """Test successful return to ON_TOUR from READY_FOR_CONTEST."""
        corps = create_test_corps(db, status="ready_for_contest", mode="run_through")

        result = return_to_tour(db, corps.id)

        assert result.status == CorpsStatus.ON_TOUR
        assert result.rehearsal_mode == RehearsalMode.RUN_THROUGH  # Preserved

    def test_return_to_tour_fails_from_on_tour(self, db):
        """Test that return fails if already ON_TOUR."""
        corps = create_test_corps(db, status="on_tour")

        with pytest.raises(CorpsError):
            return_to_tour(db, corps.id)


class TestStateMachineIntegrity:
    """Tests for overall state machine integrity and constraints."""

    def test_full_lifecycle_cycle(self, db):
        """Test complete lifecycle: ON_TOUR → READY_FOR_CONTEST → COMPLETED."""
        corps = create_test_corps(db, status="on_tour")

        # ON_TOUR → READY_FOR_CONTEST
        corps = ready_for_contest(db, corps.id)
        assert corps.status == CorpsStatus.READY_FOR_CONTEST

        # READY_FOR_CONTEST → COMPLETED
        corps = complete_corps(db, corps.id)
        assert corps.status == CorpsStatus.COMPLETED

    def test_rework_cycle(self, db):
        """Test rework cycle: ON_TOUR → READY_FOR_CONTEST → ON_TOUR."""
        corps = create_test_corps(db, status="on_tour")

        # ON_TOUR → READY_FOR_CONTEST
        corps = ready_for_contest(db, corps.id)
        assert corps.status == CorpsStatus.READY_FOR_CONTEST

        # READY_FOR_CONTEST → ON_TOUR (rework)
        corps = return_to_tour(db, corps.id)
        assert corps.status == CorpsStatus.ON_TOUR

        # Can go back to READY_FOR_CONTEST
        corps = ready_for_contest(db, corps.id)
        assert corps.status == CorpsStatus.READY_FOR_CONTEST

    def test_cannot_skip_ready_for_contest_state(self, db):
        """Test that ON_TOUR corps cannot go directly to COMPLETED."""
        corps = create_test_corps(db, status="on_tour")

        with pytest.raises(CorpsError):
            complete_corps(db, corps.id)

    def test_corps_id_validation(self, db):
        """Test that operations fail for non-existent corps."""
        with pytest.raises(CorpsError) as exc_info:
            ready_for_contest(db, "nonexistent-corps")

        assert "not found" in str(exc_info.value)

    def test_status_preserved_on_error(self, db):
        """Test that corps status is unchanged when transition fails."""
        corps = create_test_corps(db, status="on_tour")

        original_status = corps.status

        with pytest.raises(CorpsError):
            complete_corps(db, corps.id)

        # Refresh from DB to get latest state
        db.refresh(corps)
        assert corps.status == original_status
