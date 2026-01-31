"""Tests for scoresheet API, auto-scoring on rep completion, and chat context builder."""

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.database import Base

# Import all models for table creation
import backend.models.segment  # noqa: F401
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
import backend.models.work_log  # noqa: F401

from backend.models.segment import Segment, SegmentType
from backend.models.rep import Rep, RepStatus
from backend.models.score import JudgeType, Score
from backend.models.penalty import Penalty, PenaltyType
from backend.models.corps import Corps, CorpsStatus
from backend.models.show import Show, ShowStatus
from backend.models.agent_definition import AgentDefinition, ModelTier
from backend.models.agent_session import AgentSession, SessionStatus
from backend.models.message import Message, MessageType, MessagePriority
from backend.services.rep_service import create_rep, transition_rep
from backend.services.scoring_service import record_score, record_penalty


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def show_with_corps(db):
    """Create a show with a corps and segment tree."""
    corps = Corps(name="Test Corps", status=CorpsStatus.WINTER_CAMPS)
    db.add(corps)
    db.flush()

    root = Segment(type=SegmentType.SHOW, title="Test Show Root")
    db.add(root)
    db.flush()

    show = Show(title="Test Show", status=ShowStatus.ACTIVE,
                corps_id=corps.id, segment_root_id=root.id)
    db.add(show)
    db.flush()

    child = Segment(type=SegmentType.SEGMENT, title="Task 1",
                       parent_id=root.id, caption="brass")
    db.add(child)
    db.commit()
    db.refresh(corps)
    db.refresh(root)
    db.refresh(show)
    db.refresh(child)
    return {"show": show, "corps": corps, "root": root, "child": child}


# --- Auto-scoring tests ---

class TestAutoScoring:
    def test_auto_score_on_completion(self, db, show_with_corps):
        """When a rep transitions to COMPLETED, a score should be auto-generated."""
        child = show_with_corps["child"]
        corps = show_with_corps["corps"]

        rep = create_rep(db, segment_id=child.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED, assigned_to="agent-1")
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="This is a solid implementation with detailed output " * 20)
        transition_rep(db, rep.id, RepStatus.COMPLETED)

        scores = db.query(Score).filter(Score.rep_id == rep.id).all()
        assert len(scores) == 1
        score = scores[0]
        assert score.corps_id == corps.id
        assert score.judge_type == JudgeType.BRASS  # child.caption = "brass"
        assert 0 <= score.value <= 100
        assert 1 <= score.box <= 5
        assert "Auto-scored" in score.feedback

    def test_auto_score_maps_caption_to_judge(self, db, show_with_corps):
        """Caption on segment maps to the correct judge type."""
        root = show_with_corps["root"]
        corps = show_with_corps["corps"]

        # Create coord with guard caption
        guard_coord = Segment(type=SegmentType.SEGMENT, title="Guard Task",
                                 parent_id=root.id, caption="guard")
        db.add(guard_coord)
        db.commit()

        rep = create_rep(db, segment_id=guard_coord.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED, assigned_to="agent-1")
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="Guard work done")
        transition_rep(db, rep.id, RepStatus.COMPLETED)

        scores = db.query(Score).filter(Score.rep_id == rep.id).all()
        assert len(scores) == 1
        assert scores[0].judge_type == JudgeType.GUARD

    def test_auto_score_general_effect_for_unknown_caption(self, db, show_with_corps):
        """Segments without a recognized caption get scored as GENERAL_EFFECT."""
        root = show_with_corps["root"]

        coord = Segment(type=SegmentType.SEGMENT, title="Generic Task",
                           parent_id=root.id, caption=None)
        db.add(coord)
        db.commit()

        rep = create_rep(db, segment_id=coord.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED, assigned_to="agent-1")
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.REVIEW, result="Completed generic task output")
        transition_rep(db, rep.id, RepStatus.COMPLETED)

        scores = db.query(Score).filter(Score.rep_id == rep.id).all()
        assert len(scores) == 1
        assert scores[0].judge_type == JudgeType.GENERAL_EFFECT

    def test_auto_score_higher_for_longer_result(self, db, show_with_corps):
        """Longer results should produce higher scores."""
        child = show_with_corps["child"]

        # Short result
        rep1 = create_rep(db, segment_id=child.id)
        transition_rep(db, rep1.id, RepStatus.ASSIGNED, assigned_to="a1")
        transition_rep(db, rep1.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep1.id, RepStatus.REVIEW, result="Short result text")
        transition_rep(db, rep1.id, RepStatus.COMPLETED)

        # Long result
        rep2 = create_rep(db, segment_id=child.id)
        transition_rep(db, rep2.id, RepStatus.ASSIGNED, assigned_to="a2")
        transition_rep(db, rep2.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep2.id, RepStatus.REVIEW, result="Detailed output " * 100)
        transition_rep(db, rep2.id, RepStatus.COMPLETED)

        s1 = db.query(Score).filter(Score.rep_id == rep1.id).first()
        s2 = db.query(Score).filter(Score.rep_id == rep2.id).first()
        assert s2.value > s1.value

    def test_no_auto_score_on_failure(self, db, show_with_corps):
        """Failed reps should not be auto-scored."""
        child = show_with_corps["child"]

        rep = create_rep(db, segment_id=child.id)
        transition_rep(db, rep.id, RepStatus.ASSIGNED, assigned_to="agent-1")
        transition_rep(db, rep.id, RepStatus.IN_PROGRESS)
        transition_rep(db, rep.id, RepStatus.FAILED, error="Something broke")

        scores = db.query(Score).filter(Score.rep_id == rep.id).all()
        assert len(scores) == 0


# --- Scoresheet API tests ---

class TestScoresheetAPI:
    @pytest.fixture
    def client(self):
        from backend.api.app import app, get_db
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine)

        def override_get_db():
            _db = TestingSession()
            try:
                yield _db
            finally:
                _db.close()

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as c:
            yield c, TestingSession
        app.dependency_overrides.clear()

    def test_scoresheet_not_found(self, client):
        c, _ = client
        resp = c.get("/api/corps/nonexistent/scoresheet")
        assert resp.status_code == 404

    def test_scoresheet_empty_corps(self, client):
        c, SessionFactory = client
        db = SessionFactory()
        corps = Corps(name="Empty Corps", status=CorpsStatus.WINTER_CAMPS)
        db.add(corps)
        db.commit()
        db.refresh(corps)
        db.close()

        resp = c.get(f"/api/corps/{corps.id}/scoresheet")
        assert resp.status_code == 200
        data = resp.json()
        assert data["corps_name"] == "Empty Corps"
        assert data["composite"]["final_score"] == 0.0
        assert data["execution"]["reps_total"] == 0

    def test_scoresheet_with_scores(self, client):
        c, SessionFactory = client
        db = SessionFactory()

        corps = Corps(name="Scored Corps", status=CorpsStatus.WINTER_CAMPS)
        db.add(corps)
        db.flush()

        root = Segment(type=SegmentType.SHOW, title="Root")
        db.add(root)
        db.flush()

        show = Show(title="Scored Show", status=ShowStatus.ACTIVE,
                    corps_id=corps.id, segment_root_id=root.id)
        db.add(show)
        db.flush()

        rep = Rep(segment_id=root.id)
        db.add(rep)
        db.flush()

        record_score(db, corps_id=corps.id, judge_type=JudgeType.BRASS,
                     value=85.0, box=4, rep_id=rep.id)
        record_score(db, corps_id=corps.id, judge_type=JudgeType.PERCUSSION,
                     value=90.0, box=5, rep_id=rep.id)
        record_penalty(db, corps_id=corps.id, type=PenaltyType.TIMING,
                       amount=3.0, reason="Late delivery")
        corps_id = corps.id
        db.close()

        resp = c.get(f"/api/corps/{corps_id}/scoresheet")
        assert resp.status_code == 200
        data = resp.json()
        assert data["caption_scores"]["brass"]["average"] == 85.0
        assert data["caption_scores"]["percussion"]["average"] == 90.0
        assert data["penalties"]["timing"]["count"] == 1
        assert data["penalties"]["timing"]["total"] == 3.0
        assert data["composite"]["penalties_total"] == 3.0
        assert data["composite"]["raw_total"] > 0

    def test_scoresheet_execution_metrics(self, client):
        c, SessionFactory = client
        db = SessionFactory()

        corps = Corps(name="Exec Corps", status=CorpsStatus.WINTER_CAMPS)
        db.add(corps)
        db.flush()

        root = Segment(type=SegmentType.SHOW, title="Root")
        db.add(root)
        db.flush()

        show = Show(title="Exec Show", status=ShowStatus.ACTIVE,
                    corps_id=corps.id, segment_root_id=root.id)
        db.add(show)
        db.flush()

        # Add some reps
        rep1 = Rep(segment_id=root.id, status=RepStatus.COMPLETED)
        rep2 = Rep(segment_id=root.id, status=RepStatus.FAILED)
        rep3 = Rep(segment_id=root.id, status=RepStatus.IN_PROGRESS)
        db.add_all([rep1, rep2, rep3])
        db.commit()
        corps_id = corps.id
        db.close()

        resp = c.get(f"/api/corps/{corps_id}/scoresheet")
        data = resp.json()
        assert data["execution"]["reps_total"] >= 3
        assert data["execution"]["reps_completed"] >= 1
        assert data["execution"]["reps_failed"] >= 1


# --- Chat context builder tests ---

class TestChatContextBuilder:
    @pytest.fixture
    def db_with_chat(self, db):
        """Set up a corps with chat history."""
        corps = Corps(name="Chat Corps", status=CorpsStatus.WINTER_CAMPS)
        db.add(corps)
        db.flush()

        root = Segment(type=SegmentType.SHOW, title="Chat Show Root")
        db.add(root)
        db.flush()

        show = Show(title="Chat Show", status=ShowStatus.ACTIVE,
                    corps_id=corps.id, segment_root_id=root.id,
                    description="A test show for chat")
        db.add(show)
        db.flush()

        defn = AgentDefinition(
            role="executive_director",
            model_tier=ModelTier.OPUS,
            system_prompt="You are the ED.",
            nickname="Director Test",
        )
        db.add(defn)
        db.flush()

        session = AgentSession(
            definition_id=defn.id,
            corps_id=corps.id,
            status=SessionStatus.ACTIVE,
            context_snapshot=json.dumps({"final_response": "Previous context here", "iterations": 3}),
        )
        db.add(session)
        db.flush()

        # Add chat messages
        for i, (fr, body) in enumerate([
            ("user", "Hello, how are you?"),
            ("executive_director", "I'm doing great! Ready to help."),
            ("user", "Let's plan the show structure"),
            ("executive_director", "Sure, I'll create segments for the movements."),
            ("user", "What's the current status?"),  # current message
        ]):
            msg = Message(
                corps_id=corps.id,
                from_role=fr,
                to_role="executive_director" if fr == "user" else "user",
                type=MessageType.DIRECTIVE,
                subject=body[:100],
                body=body,
                priority=MessagePriority.NORMAL,
            )
            db.add(msg)
        db.commit()

        return {
            "corps": corps, "show": show, "session": session,
            "defn": defn, "root": root,
        }

    def test_context_includes_chat_history(self, db, db_with_chat):
        from backend.api.app import _build_chat_agent_context
        corps = db_with_chat["corps"]
        session = db_with_chat["session"]

        task_desc, snapshot = _build_chat_agent_context(
            db, corps.id, "executive_director", "What's the current status?", session.id
        )

        # Should contain prior messages (order may vary with same-timestamp SQLite)
        assert "Recent conversation" in task_desc
        # At least some chat messages should be present
        assert "executive_director:" in task_desc or "User:" in task_desc
        # Current message should be present
        assert "What's the current status?" in task_desc
        # Show context
        assert "Chat Show" in task_desc

    def test_context_includes_snapshot(self, db, db_with_chat):
        from backend.api.app import _build_chat_agent_context
        corps = db_with_chat["corps"]
        session = db_with_chat["session"]

        _, snapshot = _build_chat_agent_context(
            db, corps.id, "executive_director", "test", session.id
        )

        assert snapshot is not None
        parsed = json.loads(snapshot)
        assert parsed["final_response"] == "Previous context here"
        assert parsed["iterations"] == 3

    def test_context_without_snapshot(self, db, db_with_chat):
        from backend.api.app import _build_chat_agent_context
        corps = db_with_chat["corps"]
        session = db_with_chat["session"]

        # Clear the snapshot
        session.context_snapshot = None
        db.commit()

        _, snapshot = _build_chat_agent_context(
            db, corps.id, "executive_director", "test", session.id
        )
        assert snapshot is None

    def test_context_includes_show_description(self, db, db_with_chat):
        from backend.api.app import _build_chat_agent_context
        corps = db_with_chat["corps"]
        session = db_with_chat["session"]

        task_desc, _ = _build_chat_agent_context(
            db, corps.id, "executive_director", "test", session.id
        )
        assert "A test show for chat" in task_desc

    def test_context_includes_root_segment(self, db, db_with_chat):
        from backend.api.app import _build_chat_agent_context
        corps = db_with_chat["corps"]
        session = db_with_chat["session"]
        root = db_with_chat["root"]

        task_desc, _ = _build_chat_agent_context(
            db, corps.id, "executive_director", "test", session.id
        )
        assert root.id in task_desc


# --- Dashboard final_score tests ---

class TestDashboardFinalScore:
    @pytest.fixture
    def client(self):
        from backend.api.app import app, get_db
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        TestingSession = sessionmaker(bind=engine)

        def override_get_db():
            _db = TestingSession()
            try:
                yield _db
            finally:
                _db.close()

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as c:
            yield c, TestingSession
        app.dependency_overrides.clear()

    def test_shows_overview_includes_final_score(self, client):
        c, SessionFactory = client
        db = SessionFactory()

        corps = Corps(name="Score Corps", status=CorpsStatus.WINTER_CAMPS)
        db.add(corps)
        db.flush()

        show = Show(title="Scored Show", status=ShowStatus.ACTIVE, corps_id=corps.id)
        db.add(show)
        db.flush()

        root = Segment(type=SegmentType.SHOW, title="Root")
        db.add(root)
        db.flush()
        rep = Rep(segment_id=root.id)
        db.add(rep)
        db.flush()

        record_score(db, corps_id=corps.id, judge_type=JudgeType.BRASS,
                     value=80.0, box=4, rep_id=rep.id)
        record_score(db, corps_id=corps.id, judge_type=JudgeType.GUARD,
                     value=90.0, box=5, rep_id=rep.id)
        db.close()

        resp = c.get("/api/shows-overview")
        assert resp.status_code == 200
        shows = resp.json()
        scored_show = next(s for s in shows if s["title"] == "Scored Show")
        assert scored_show["final_score"] == 85.0  # avg of 80 and 90

    def test_shows_overview_null_score_when_none(self, client):
        c, SessionFactory = client
        db = SessionFactory()

        show = Show(title="No Score Show", status=ShowStatus.DRAFT)
        db.add(show)
        db.commit()
        db.close()

        resp = c.get("/api/shows-overview")
        shows = resp.json()
        no_score = next(s for s in shows if s["title"] == "No Score Show")
        assert no_score["final_score"] is None
