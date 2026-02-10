"""Tests for drill book models and service."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
import backend.models  # noqa: F401

from backend.models.drill_book import (
    BookStatus,
    BookType,
    DrillBook,
    DrillStep,
    StepStatus,
)
from backend.services.drill_book_service import (
    InvalidBookTransition,
    InvalidStepTransition,
    add_evidence,
    add_step,
    assign_book,
    complete_book,
    complete_step,
    create_book,
    fail_book,
    fail_step,
    get_next_steps,
    get_resumption_context,
    list_books,
    skip_step,
    spawn_child_book,
    start_book,
    start_step,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


class TestCreateBook:
    def test_create_basic(self, db):
        book = create_book(db, title="Implement feature X")
        assert book.id
        assert book.title == "Implement feature X"
        assert book.status == BookStatus.PENDING
        assert book.book_type == BookType.LINEAR.value

    def test_create_with_options(self, db):
        book = create_book(
            db, title="DAG book", description="complex task",
            book_type=BookType.DAG.value, corps_id="corps-1", role="brass_tech",
        )
        assert book.book_type == BookType.DAG.value
        assert book.corps_id == "corps-1"
        assert book.assigned_role == "brass_tech"


class TestBookLifecycle:
    def test_pending_to_assigned(self, db):
        book = create_book(db, title="Test")
        book = assign_book(db, book.id)
        assert book.status == BookStatus.ASSIGNED

    def test_assigned_to_in_progress(self, db):
        book = create_book(db, title="Test")
        assign_book(db, book.id)
        book = start_book(db, book.id)
        assert book.status == BookStatus.IN_PROGRESS

    def test_pending_to_in_progress_direct(self, db):
        book = create_book(db, title="Test")
        book = start_book(db, book.id)
        assert book.status == BookStatus.IN_PROGRESS

    def test_complete_book_all_steps_done(self, db):
        book = create_book(db, title="Test")
        step = add_step(db, book.id, "write_code", "implement thing")
        start_book(db, book.id)
        start_step(db, step.id)
        complete_step(db, step.id)
        book = complete_book(db, book.id)
        assert book.status == BookStatus.COMPLETED

    def test_complete_book_step_not_done_raises(self, db):
        book = create_book(db, title="Test")
        add_step(db, book.id, "write_code", "implement thing")
        start_book(db, book.id)
        with pytest.raises(InvalidBookTransition, match="still pending"):
            complete_book(db, book.id)

    def test_fail_book(self, db):
        book = create_book(db, title="Test")
        start_book(db, book.id)
        book = fail_book(db, book.id, error="something broke")
        assert book.status == BookStatus.FAILED
        assert "something broke" in book.context_summary

    def test_abandon_book(self, db):
        book = create_book(db, title="Test")
        start_book(db, book.id)
        from backend.services.drill_book_service import abandon_book
        book = abandon_book(db, book.id, reason="no longer needed")
        assert book.status == BookStatus.ABANDONED

    def test_invalid_transition_raises(self, db):
        book = create_book(db, title="Test")
        with pytest.raises(InvalidBookTransition):
            complete_book(db, book.id)  # Can't go from PENDING to COMPLETED


class TestStepLifecycle:
    def test_add_step_auto_sequence(self, db):
        book = create_book(db, title="Test")
        s1 = add_step(db, book.id, "read_spec", "read the spec")
        s2 = add_step(db, book.id, "write_code", "write code")
        assert s1.sequence == 0
        assert s2.sequence == 1

    def test_start_step(self, db):
        book = create_book(db, title="Test")
        step = add_step(db, book.id, "write_code")
        step = start_step(db, step.id, session_id="sess-1")
        assert step.status == StepStatus.IN_PROGRESS
        assert step.assigned_session_id == "sess-1"

    def test_complete_step_with_result(self, db):
        book = create_book(db, title="Test")
        step = add_step(db, book.id, "write_code")
        start_step(db, step.id)
        step = complete_step(db, step.id, result={"files_changed": 3})
        assert step.status == StepStatus.COMPLETED
        assert step.result == {"files_changed": 3}

    def test_fail_step(self, db):
        book = create_book(db, title="Test")
        step = add_step(db, book.id, "write_code")
        start_step(db, step.id)
        step = fail_step(db, step.id, error="compilation error")
        assert step.status == StepStatus.FAILED
        assert step.error == "compilation error"

    def test_skip_step(self, db):
        book = create_book(db, title="Test")
        step = add_step(db, book.id, "optional_thing")
        step = skip_step(db, step.id)
        assert step.status == StepStatus.SKIPPED

    def test_invalid_step_transition(self, db):
        book = create_book(db, title="Test")
        step = add_step(db, book.id, "write_code")
        with pytest.raises(InvalidStepTransition):
            complete_step(db, step.id)  # Can't go from PENDING to COMPLETED


class TestDAGNavigation:
    def test_linear_next_step(self, db):
        book = create_book(db, title="Linear", book_type=BookType.LINEAR.value)
        s1 = add_step(db, book.id, "step_1")
        s2 = add_step(db, book.id, "step_2")

        next_steps = get_next_steps(db, book.id)
        assert len(next_steps) == 1
        assert next_steps[0].id == s1.id

    def test_linear_advances_after_completion(self, db):
        book = create_book(db, title="Linear", book_type=BookType.LINEAR.value)
        s1 = add_step(db, book.id, "step_1")
        s2 = add_step(db, book.id, "step_2")

        start_step(db, s1.id)
        complete_step(db, s1.id)

        next_steps = get_next_steps(db, book.id)
        assert len(next_steps) == 1
        assert next_steps[0].id == s2.id

    def test_dag_parallel_steps(self, db):
        book = create_book(db, title="DAG", book_type=BookType.DAG.value)
        s1 = add_step(db, book.id, "step_1")
        s2 = add_step(db, book.id, "step_2")
        s3 = add_step(db, book.id, "step_3", depends_on=[s1.id, s2.id])

        # Both s1 and s2 are ready (no deps)
        next_steps = get_next_steps(db, book.id)
        assert len(next_steps) == 2
        ids = {s.id for s in next_steps}
        assert s1.id in ids
        assert s2.id in ids

    def test_dag_dependency_blocking(self, db):
        book = create_book(db, title="DAG", book_type=BookType.DAG.value)
        s1 = add_step(db, book.id, "step_1")
        s2 = add_step(db, book.id, "step_2", depends_on=[s1.id])

        next_steps = get_next_steps(db, book.id)
        assert len(next_steps) == 1
        assert next_steps[0].id == s1.id  # s2 blocked by s1

    def test_dag_dep_resolved(self, db):
        book = create_book(db, title="DAG", book_type=BookType.DAG.value)
        s1 = add_step(db, book.id, "step_1")
        s2 = add_step(db, book.id, "step_2", depends_on=[s1.id])

        start_step(db, s1.id)
        complete_step(db, s1.id)

        next_steps = get_next_steps(db, book.id)
        assert len(next_steps) == 1
        assert next_steps[0].id == s2.id


class TestResumptionContext:
    def test_context_includes_progress(self, db):
        book = create_book(db, title="Test")
        s1 = add_step(db, book.id, "step_1")
        s2 = add_step(db, book.id, "step_2")
        start_step(db, s1.id)
        complete_step(db, s1.id)

        ctx = get_resumption_context(db, book.id)
        assert ctx["book_id"] == book.id
        assert ctx["progress"]["total"] == 2
        assert ctx["progress"]["completed"] == 1
        assert ctx["progress"]["pending"] == 1
        assert len(ctx["next_step_ids"]) == 1

    def test_context_includes_step_details(self, db):
        book = create_book(db, title="Test", description="do stuff")
        add_step(db, book.id, "write_code", "implement feature")

        ctx = get_resumption_context(db, book.id)
        assert ctx["title"] == "Test"
        assert ctx["description"] == "do stuff"
        assert len(ctx["steps"]) == 1
        assert ctx["steps"][0]["action_type"] == "write_code"


class TestEvidence:
    def test_add_evidence_to_book(self, db):
        book = create_book(db, title="Test")
        ev = add_evidence(db, book.id, "test_result", content="All tests passed")
        assert ev.id
        assert ev.evidence_type == "test_result"
        assert ev.book_id == book.id

    def test_add_evidence_to_step(self, db):
        book = create_book(db, title="Test")
        step = add_step(db, book.id, "write_code")
        ev = add_evidence(db, book.id, "file_diff", step_id=step.id, content="diff content")
        assert ev.step_id == step.id

    def test_complete_step_with_evidence(self, db):
        book = create_book(db, title="Test")
        step = add_step(db, book.id, "run_tests")
        start_step(db, step.id)
        step = complete_step(db, step.id, evidence_content="all passed", evidence_type="test_result")
        assert step.status == StepStatus.COMPLETED
        # Evidence should have been created
        from backend.models.drill_book import DrillEvidence
        ev = db.query(DrillEvidence).filter(DrillEvidence.step_id == step.id).first()
        assert ev is not None
        assert ev.evidence_type == "test_result"


class TestChildBooks:
    def test_spawn_child(self, db):
        parent = create_book(db, title="Parent task", corps_id="c1", role="brass_tech")
        child = spawn_child_book(db, parent.id, title="Subtask 1")
        assert child.parent_id == parent.id
        assert child.corps_id == "c1"
        assert child.assigned_role == "brass_tech"

    def test_spawn_child_with_steps(self, db):
        parent = create_book(db, title="Parent")
        child = spawn_child_book(
            db, parent.id, title="Subtask",
            steps=[
                {"action_type": "read_spec", "description": "Read spec"},
                {"action_type": "write_code", "description": "Write code"},
            ],
        )
        assert len(child.steps) == 2
        assert child.steps[0].action_type == "read_spec"
        assert child.steps[1].action_type == "write_code"

    def test_spawn_child_override_role(self, db):
        parent = create_book(db, title="Parent", role="brass_tech")
        child = spawn_child_book(db, parent.id, title="Guard subtask", role="guard_tech")
        assert child.assigned_role == "guard_tech"


class TestListBooks:
    def test_list_all(self, db):
        create_book(db, title="A")
        create_book(db, title="B")
        assert len(list_books(db)) == 2

    def test_list_by_corps(self, db):
        create_book(db, title="A", corps_id="c1")
        create_book(db, title="B", corps_id="c2")
        assert len(list_books(db, corps_id="c1")) == 1

    def test_list_by_status(self, db):
        b1 = create_book(db, title="A")
        b2 = create_book(db, title="B")
        start_book(db, b2.id)
        assert len(list_books(db, status=BookStatus.PENDING)) == 1
        assert len(list_books(db, status=BookStatus.IN_PROGRESS)) == 1
