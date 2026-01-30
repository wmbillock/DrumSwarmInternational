"""Phase 9: Show model and DCI layer tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.show import Show, ShowStatus
from backend.services.show_service import (
    create_show,
    get_show,
    list_shows,
    update_show,
    activate_show,
    complete_show,
    archive_show,
    toggle_tour,
    ShowError,
)

# Import all models
import backend.models.coordinate  # noqa: F401
import backend.models.rep  # noqa: F401
import backend.models.message  # noqa: F401
import backend.models.problem  # noqa: F401
import backend.models.subscription  # noqa: F401
import backend.models.agent_definition  # noqa: F401
import backend.models.agent_session  # noqa: F401
import backend.models.score  # noqa: F401
import backend.models.penalty  # noqa: F401
import backend.models.corps  # noqa: F401
import backend.models.show  # noqa: F401


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


class TestShowCRUD:
    def test_create_show(self, db):
        show = create_show(db, title="My Show", description="A test show")
        assert show.id is not None
        assert show.title == "My Show"
        assert show.status == ShowStatus.DRAFT
        assert show.coordinate_root_id is not None

    def test_get_show(self, db):
        show = create_show(db, title="Get Test")
        found = get_show(db, show.id)
        assert found is not None
        assert found.title == "Get Test"

    def test_get_nonexistent(self, db):
        assert get_show(db, "nope") is None

    def test_list_shows(self, db):
        create_show(db, title="Show A")
        create_show(db, title="Show B")
        shows = list_shows(db)
        assert len(shows) == 2

    def test_update_show(self, db):
        show = create_show(db, title="Old Title")
        updated = update_show(db, show.id, title="New Title")
        assert updated.title == "New Title"

    def test_update_nonexistent(self, db):
        with pytest.raises(ShowError):
            update_show(db, "nope", title="X")


class TestShowLifecycle:
    def test_activate_show(self, db):
        show = create_show(db, title="Activate Test")
        show = activate_show(db, show.id)
        assert show.status == ShowStatus.ACTIVE
        assert show.corps_id is not None

    def test_cannot_activate_twice(self, db):
        show = create_show(db, title="Double Activate")
        activate_show(db, show.id)
        with pytest.raises(ShowError, match="draft"):
            activate_show(db, show.id)

    def test_complete_show(self, db):
        show = create_show(db, title="Complete Test")
        activate_show(db, show.id)
        show = complete_show(db, show.id)
        assert show.status == ShowStatus.COMPLETED

    def test_archive_show(self, db):
        show = create_show(db, title="Archive Test")
        show = archive_show(db, show.id)
        assert show.status == ShowStatus.ARCHIVED


class TestTourToggle:
    def test_enable_tour(self, db):
        show = create_show(db, title="Tour Test")
        activate_show(db, show.id)
        show = toggle_tour(db, show.id, enable=True)
        assert show is not None

    def test_disable_tour(self, db):
        show = create_show(db, title="Tour Test")
        activate_show(db, show.id)
        toggle_tour(db, show.id, enable=True)
        show = toggle_tour(db, show.id, enable=False)
        assert show is not None

    def test_tour_without_corps(self, db):
        show = create_show(db, title="No Corps")
        with pytest.raises(ShowError, match="corps"):
            toggle_tour(db, show.id, enable=True)


class TestEndToEnd:
    def test_create_activate_coordinate_rep(self, db):
        """Integration test: show → corps → coordinate → rep."""
        from backend.models.coordinate import CoordinateType
        from backend.services.coordinate_service import create_coordinate
        from backend.services.rep_service import create_rep, transition_rep
        from backend.models.rep import RepStatus
        from backend.services.scoring_service import record_score
        from backend.models.score import JudgeType

        # Create and activate show
        show = create_show(db, title="Integration Test")
        show = activate_show(db, show.id)
        assert show.corps_id is not None

        # Create coordinate tree
        movement = create_coordinate(
            db, type=CoordinateType.MOVEMENT, title="Movement 1",
            parent_id=show.coordinate_root_id
        )
        set_coord = create_coordinate(
            db, type=CoordinateType.SET, title="Set 1",
            parent_id=movement.id, caption="brass"
        )

        # Create and run a rep
        rep = create_rep(db, coordinate_id=set_coord.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED, assigned_to="agent-1")
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="Done")
        transition_rep(db, rep.id, RepStatus.COMPLETED)

        # Score it
        score = record_score(
            db, corps_id=show.corps_id, judge_type=JudgeType.BRASS,
            value=85.0, box=4, rep_id=rep.id
        )
        assert score.value == 85.0
