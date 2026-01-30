"""Phase 8: Support staff and improvement lifecycle tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.agent_definition import AgentDefinition, ModelTier
from backend.models.coordinate import Coordinate, CoordinateType, CoordinateStatus
from backend.models.rep import Rep, RepStatus
from backend.models.score import JudgeType, Score
from backend.services.support_staff import (
    SUPPORT_STAFF_ROLES,
    create_support_staff_definitions,
    spawn_support_staff,
)
from backend.services.improvement import (
    run_basics,
    run_critique,
    run_banquet,
    BasicsResult,
    CritiqueResult,
    BanquetReport,
)
from backend.services.scoring_service import record_score

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


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


CORPS_ID = "corps-test"


class TestSupportStaffDefinitions:
    def test_all_roles_defined(self):
        assert "souvie_crew" in SUPPORT_STAFF_ROLES
        assert "accountant" in SUPPORT_STAFF_ROLES
        assert "board_of_directors" in SUPPORT_STAFF_ROLES
        assert "housing_coordinator" in SUPPORT_STAFF_ROLES

    def test_create_definitions(self, db):
        defs = create_support_staff_definitions(db, CORPS_ID)
        assert len(defs) == 4
        assert "souvie_crew" in defs
        assert defs["souvie_crew"].role == "souvie_crew"
        assert defs["accountant"].model_tier == ModelTier.HAIKU
        assert defs["board_of_directors"].model_tier == ModelTier.OPUS

    def test_spawn_support_staff(self, db):
        defs = create_support_staff_definitions(db, CORPS_ID)
        sessions = spawn_support_staff(db, CORPS_ID, defs)
        assert len(sessions) == 4
        for role, session in sessions.items():
            assert session.corps_id == CORPS_ID

    def test_souvie_crew_has_tools(self, db):
        defs = create_support_staff_definitions(db, CORPS_ID)
        assert "cleaning" in defs["souvie_crew"].tools_allowed_list
        assert "dressing" in defs["souvie_crew"].tools_allowed_list

    def test_accountant_no_tools(self, db):
        defs = create_support_staff_definitions(db, CORPS_ID)
        assert defs["accountant"].tools_allowed_list == []


class TestBasicsEngine:
    def test_basics_no_data(self, db):
        result = run_basics(db, CORPS_ID, "brass")
        assert isinstance(result, BasicsResult)
        assert result.caption == "brass"
        assert result.definitions_reviewed == 0

    def test_basics_finds_definitions(self, db):
        defn = AgentDefinition(
            role="brass_tech", system_prompt="test", corps_id=CORPS_ID
        )
        db.add(defn)
        db.commit()
        result = run_basics(db, CORPS_ID, "brass")
        assert result.definitions_reviewed == 1

    def test_basics_suggests_from_failures(self, db):
        coord = Coordinate(
            type=CoordinateType.SET, title="Set 1", caption="brass",
            status=CoordinateStatus.FAILED,
        )
        # Need a show parent for the coordinate to be valid in isolation
        show = Coordinate(type=CoordinateType.SHOW, title="Show")
        db.add(show)
        db.commit()
        db.refresh(show)
        coord.parent_id = show.id
        db.add(coord)
        db.commit()
        db.refresh(coord)

        rep = Rep(coordinate_id=coord.id, status=RepStatus.FAILED, error="Bad")
        db.add(rep)
        db.commit()

        result = run_basics(db, CORPS_ID, "brass")
        assert result.improvements_suggested >= 1
        assert any("failed" in s.lower() for s in result.suggestions)

    def test_basics_flags_low_scores(self, db):
        show = Coordinate(type=CoordinateType.SHOW, title="Show")
        db.add(show)
        db.commit()
        db.refresh(show)

        coord = Coordinate(
            type=CoordinateType.SET, title="Set", caption="brass",
            parent_id=show.id, status=CoordinateStatus.COMPLETED,
        )
        db.add(coord)
        db.commit()
        db.refresh(coord)

        rep = Rep(coordinate_id=coord.id, status=RepStatus.COMPLETED)
        db.add(rep)
        db.commit()
        db.refresh(rep)

        record_score(db, corps_id=CORPS_ID, judge_type=JudgeType.BRASS,
                     value=45.0, box=2, rep_id=rep.id)

        result = run_basics(db, CORPS_ID, "brass")
        assert result.improvements_suggested >= 1


class TestCritiqueEngine:
    def _make_scored_rep(self, db):
        show = Coordinate(type=CoordinateType.SHOW, title="Show")
        db.add(show)
        db.commit()
        db.refresh(show)
        coord = Coordinate(type=CoordinateType.SET, title="S1",
                          parent_id=show.id, status=CoordinateStatus.COMPLETED)
        db.add(coord)
        db.commit()
        db.refresh(coord)
        rep = Rep(coordinate_id=coord.id, status=RepStatus.COMPLETED)
        db.add(rep)
        db.commit()
        db.refresh(rep)
        return rep

    def test_critique_no_scores(self, db):
        rep = self._make_scored_rep(db)
        result = run_critique(db, rep.id, CORPS_ID)
        assert isinstance(result, CritiqueResult)
        assert len(result.feedbacks) == 0

    def test_critique_with_high_score(self, db):
        rep = self._make_scored_rep(db)
        record_score(db, corps_id=CORPS_ID, judge_type=JudgeType.BRASS,
                     value=85.0, box=4, rep_id=rep.id, feedback="Great work")
        result = run_critique(db, rep.id, CORPS_ID)
        assert len(result.feedbacks) == 1
        assert result.feedbacks[0].strengths
        assert "Strong" in result.overall_assessment

    def test_critique_with_low_score(self, db):
        rep = self._make_scored_rep(db)
        record_score(db, corps_id=CORPS_ID, judge_type=JudgeType.BRASS,
                     value=40.0, box=1, rep_id=rep.id)
        result = run_critique(db, rep.id, CORPS_ID)
        assert result.needs_rework
        assert result.feedbacks[0].weaknesses
        assert "rework" in result.overall_assessment.lower()

    def test_critique_multiple_judges(self, db):
        rep = self._make_scored_rep(db)
        record_score(db, corps_id=CORPS_ID, judge_type=JudgeType.BRASS,
                     value=80.0, box=4, rep_id=rep.id)
        record_score(db, corps_id=CORPS_ID, judge_type=JudgeType.GUARD,
                     value=70.0, box=3, rep_id=rep.id)
        result = run_critique(db, rep.id, CORPS_ID)
        assert len(result.feedbacks) == 2


class TestBanquetEngine:
    def test_banquet_empty_corps(self, db):
        report = run_banquet(db, CORPS_ID)
        assert isinstance(report, BanquetReport)
        assert report.total_reps == 0
        assert report.generated_at is not None

    def test_banquet_with_data(self, db):
        show = Coordinate(type=CoordinateType.SHOW, title="Show")
        db.add(show)
        db.commit()
        db.refresh(show)

        coord = Coordinate(type=CoordinateType.SET, title="S1",
                          parent_id=show.id)
        db.add(coord)
        db.commit()
        db.refresh(coord)

        # Create some reps
        for status in [RepStatus.COMPLETED, RepStatus.COMPLETED, RepStatus.FAILED]:
            r = Rep(coordinate_id=coord.id, status=status)
            db.add(r)
        db.commit()

        # Add a definition for the corps
        defn = AgentDefinition(role="brass_tech", system_prompt="t", corps_id=CORPS_ID)
        db.add(defn)
        db.commit()

        report = run_banquet(db, CORPS_ID)
        assert report.total_reps == 3
        assert report.completed_reps == 2
        assert report.failed_reps == 1
        assert any("failed" in w.lower() for w in report.what_failed)

    def test_banquet_with_scores(self, db):
        show = Coordinate(type=CoordinateType.SHOW, title="Show")
        db.add(show)
        db.commit()
        db.refresh(show)
        coord = Coordinate(type=CoordinateType.SET, title="S1", parent_id=show.id)
        db.add(coord)
        db.commit()
        db.refresh(coord)
        rep = Rep(coordinate_id=coord.id, status=RepStatus.COMPLETED)
        db.add(rep)
        db.commit()
        db.refresh(rep)

        record_score(db, corps_id=CORPS_ID, judge_type=JudgeType.BRASS,
                     value=90.0, box=5, rep_id=rep.id)

        report = run_banquet(db, CORPS_ID)
        assert report.average_score == pytest.approx(90.0)
        assert report.top_caption == "brass"
        assert any("Strong" in w for w in report.what_worked)

    def test_banquet_low_completion(self, db):
        show = Coordinate(type=CoordinateType.SHOW, title="Show")
        db.add(show)
        db.commit()
        db.refresh(show)
        coord = Coordinate(type=CoordinateType.SET, title="S1", parent_id=show.id)
        db.add(coord)
        db.commit()
        db.refresh(coord)

        for _ in range(5):
            db.add(Rep(coordinate_id=coord.id, status=RepStatus.FAILED))
        db.add(Rep(coordinate_id=coord.id, status=RepStatus.COMPLETED))
        db.commit()

        report = run_banquet(db, CORPS_ID)
        assert report.total_reps == 6
        assert any("success rate" in i.lower() for i in report.improvements)
