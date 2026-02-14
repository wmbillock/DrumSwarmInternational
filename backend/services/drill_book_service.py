"""Drill book service — CRUD + state machine for persistent work units.

Manages the lifecycle of drill books from creation through completion,
including step management, assignment, and cold-resume context generation.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.drill_book import (
    BookStatus,
    BookType,
    DrillBook,
    DrillEvidence,
    DrillStep,
    StepStatus,
    TERMINAL_BOOK_STATUSES,
    TERMINAL_STEP_STATUSES,
)

logger = logging.getLogger(__name__)

# Valid book status transitions
BOOK_TRANSITIONS = {
    BookStatus.PENDING: {BookStatus.ASSIGNED, BookStatus.IN_PROGRESS, BookStatus.ABANDONED},
    BookStatus.ASSIGNED: {BookStatus.IN_PROGRESS, BookStatus.ABANDONED},
    BookStatus.IN_PROGRESS: {BookStatus.BLOCKED, BookStatus.COMPLETED, BookStatus.FAILED, BookStatus.ABANDONED},
    BookStatus.BLOCKED: {BookStatus.IN_PROGRESS, BookStatus.FAILED, BookStatus.ABANDONED},
    BookStatus.COMPLETED: {BookStatus.VERIFIED},
    BookStatus.VERIFIED: set(),
    BookStatus.FAILED: {BookStatus.PENDING},  # Allow retry
    BookStatus.ABANDONED: set(),
}

# Valid step status transitions
STEP_TRANSITIONS = {
    StepStatus.PENDING: {StepStatus.IN_PROGRESS, StepStatus.SKIPPED},
    StepStatus.IN_PROGRESS: {StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED},
    StepStatus.COMPLETED: {StepStatus.VERIFIED},
    StepStatus.VERIFIED: set(),
    StepStatus.FAILED: {StepStatus.PENDING},  # Allow retry
    StepStatus.SKIPPED: set(),
}


class InvalidBookTransition(Exception):
    pass


class InvalidStepTransition(Exception):
    pass


# ---------------------------------------------------------------------------
# Book CRUD
# ---------------------------------------------------------------------------


def create_book(
    db: Session,
    title: str,
    description: str = "",
    book_type: str = BookType.LINEAR.value,
    parent_id: Optional[str] = None,
    corps_id: Optional[str] = None,
    role: Optional[str] = None,
) -> DrillBook:
    """Create a new drill book."""
    book = DrillBook(
        title=title,
        description=description,
        book_type=book_type,
        parent_id=parent_id,
        corps_id=corps_id,
        assigned_role=role,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def get_book(db: Session, book_id: str) -> Optional[DrillBook]:
    """Get a drill book by ID."""
    return db.get(DrillBook, book_id)


def list_books(
    db: Session,
    corps_id: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[BookStatus] = None,
    parent_id: Optional[str] = None,
) -> list[DrillBook]:
    """List drill books with optional filters."""
    q = db.query(DrillBook)
    if corps_id:
        q = q.filter(DrillBook.corps_id == corps_id)
    if role:
        q = q.filter(DrillBook.assigned_role == role)
    if status:
        q = q.filter(DrillBook.status == status)
    if parent_id is not None:
        q = q.filter(DrillBook.parent_id == parent_id)
    return q.order_by(DrillBook.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Step CRUD
# ---------------------------------------------------------------------------


def add_step(
    db: Session,
    book_id: str,
    action_type: str,
    description: str = "",
    depends_on: Optional[list[str]] = None,
    sequence: Optional[int] = None,
) -> DrillStep:
    """Add a step to a drill book."""
    book = db.get(DrillBook, book_id)
    if book is None:
        raise ValueError(f"Book {book_id} not found")

    if sequence is None:
        # Auto-sequence: next after current max
        max_seq = max((s.sequence for s in book.steps), default=-1)
        sequence = max_seq + 1

    step = DrillStep(
        book_id=book_id,
        action_type=action_type,
        description=description,
        depends_on=depends_on,
        sequence=sequence,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def get_step(db: Session, step_id: str) -> Optional[DrillStep]:
    return db.get(DrillStep, step_id)


# ---------------------------------------------------------------------------
# Book state machine
# ---------------------------------------------------------------------------


def _transition_book(db: Session, book: DrillBook, new_status: BookStatus) -> DrillBook:
    """Transition a book to a new status with validation."""
    allowed = BOOK_TRANSITIONS.get(book.status, set())
    if new_status not in allowed:
        raise InvalidBookTransition(
            f"Cannot transition book from {book.status.value} to {new_status.value}"
        )
    book.status = new_status
    if new_status in TERMINAL_BOOK_STATUSES:
        book.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(book)
    return book


def assign_book(
    db: Session,
    book_id: str,
    performer_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> DrillBook:
    """Assign a book to a performer/session."""
    book = db.get(DrillBook, book_id)
    if book is None:
        raise ValueError(f"Book {book_id} not found")

    if performer_id:
        book.assigned_performer_id = performer_id

    return _transition_book(db, book, BookStatus.ASSIGNED)


def start_book(db: Session, book_id: str) -> DrillBook:
    """Mark a book as in-progress."""
    book = db.get(DrillBook, book_id)
    if book is None:
        raise ValueError(f"Book {book_id} not found")
    return _transition_book(db, book, BookStatus.IN_PROGRESS)


def complete_book(db: Session, book_id: str) -> DrillBook:
    """Complete a book — only if all steps are in terminal state."""
    book = db.get(DrillBook, book_id)
    if book is None:
        raise ValueError(f"Book {book_id} not found")

    # Check all steps are done
    for step in book.steps:
        if step.status not in TERMINAL_STEP_STATUSES:
            raise InvalidBookTransition(
                f"Cannot complete book: step {step.id} is still {step.status.value}"
            )

    return _transition_book(db, book, BookStatus.COMPLETED)


def fail_book(db: Session, book_id: str, error: str = "") -> DrillBook:
    """Mark a book as failed."""
    book = db.get(DrillBook, book_id)
    if book is None:
        raise ValueError(f"Book {book_id} not found")
    book.context_summary = f"Failed: {error}" if error else "Failed"
    return _transition_book(db, book, BookStatus.FAILED)


def abandon_book(db: Session, book_id: str, reason: str = "") -> DrillBook:
    """Abandon a book."""
    book = db.get(DrillBook, book_id)
    if book is None:
        raise ValueError(f"Book {book_id} not found")
    book.context_summary = f"Abandoned: {reason}" if reason else "Abandoned"
    return _transition_book(db, book, BookStatus.ABANDONED)


# ---------------------------------------------------------------------------
# Step state machine
# ---------------------------------------------------------------------------


def _transition_step(db: Session, step: DrillStep, new_status: StepStatus) -> DrillStep:
    """Transition a step to a new status with validation."""
    allowed = STEP_TRANSITIONS.get(step.status, set())
    if new_status not in allowed:
        raise InvalidStepTransition(
            f"Cannot transition step from {step.status.value} to {new_status.value}"
        )
    step.status = new_status
    if new_status in TERMINAL_STEP_STATUSES:
        step.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(step)
    return step


def start_step(db: Session, step_id: str, session_id: Optional[str] = None) -> DrillStep:
    """Start working on a step."""
    step = db.get(DrillStep, step_id)
    if step is None:
        raise ValueError(f"Step {step_id} not found")

    if session_id:
        step.assigned_session_id = session_id
    step.started_at = datetime.now(timezone.utc)
    return _transition_step(db, step, StepStatus.IN_PROGRESS)


def complete_step(
    db: Session,
    step_id: str,
    result: Optional[dict] = None,
    evidence_content: Optional[str] = None,
    evidence_type: str = "command_output",
) -> DrillStep:
    """Complete a step with optional result and evidence."""
    step = db.get(DrillStep, step_id)
    if step is None:
        raise ValueError(f"Step {step_id} not found")

    if result:
        step.result = result

    step = _transition_step(db, step, StepStatus.COMPLETED)

    # Auto-add evidence if provided
    if evidence_content:
        add_evidence(db, step.book_id, step_id=step.id,
                     evidence_type=evidence_type, content=evidence_content)

    return step


def fail_step(db: Session, step_id: str, error: str = "") -> DrillStep:
    """Fail a step."""
    step = db.get(DrillStep, step_id)
    if step is None:
        raise ValueError(f"Step {step_id} not found")
    step.error = error
    return _transition_step(db, step, StepStatus.FAILED)


def skip_step(db: Session, step_id: str) -> DrillStep:
    """Skip a step."""
    step = db.get(DrillStep, step_id)
    if step is None:
        raise ValueError(f"Step {step_id} not found")
    return _transition_step(db, step, StepStatus.SKIPPED)


# ---------------------------------------------------------------------------
# DAG-aware navigation
# ---------------------------------------------------------------------------


def get_next_steps(db: Session, book_id: str) -> list[DrillStep]:
    """Get steps that are ready to execute (all dependencies met).

    For LINEAR books: returns the first pending step.
    For DAG books: returns all pending steps whose depends_on are all completed.
    """
    book = db.get(DrillBook, book_id)
    if book is None:
        raise ValueError(f"Book {book_id} not found")

    completed_ids = {s.id for s in book.steps if s.status in TERMINAL_STEP_STATUSES}
    ready = []

    for step in book.steps:
        if step.status != StepStatus.PENDING:
            continue

        deps = step.depends_on or []
        if all(dep_id in completed_ids for dep_id in deps):
            ready.append(step)

        # For LINEAR books, only return the first ready step
        if book.book_type == BookType.LINEAR.value and ready:
            break

    return ready


# ---------------------------------------------------------------------------
# Cold-resume context
# ---------------------------------------------------------------------------


def get_resumption_context(db: Session, book_id: str) -> dict:
    """Build context for a new agent picking up this book cold.

    Returns everything needed to understand and continue the work.
    """
    book = db.get(DrillBook, book_id)
    if book is None:
        raise ValueError(f"Book {book_id} not found")

    steps_summary = []
    for step in book.steps:
        step_info = {
            "id": step.id,
            "sequence": step.sequence,
            "action_type": step.action_type,
            "description": step.description,
            "status": step.status.value,
        }
        if step.result:
            step_info["result"] = step.result
        if step.error:
            step_info["error"] = step.error
        steps_summary.append(step_info)

    next_steps = get_next_steps(db, book_id)

    return {
        "book_id": book.id,
        "title": book.title,
        "description": book.description,
        "status": book.status.value,
        "book_type": book.book_type,
        "context_summary": book.context_summary,
        "context_snapshot": book.context_snapshot,
        "steps": steps_summary,
        "next_step_ids": [s.id for s in next_steps],
        "progress": {
            "total": len(book.steps),
            "completed": sum(1 for s in book.steps if s.status in TERMINAL_STEP_STATUSES),
            "pending": sum(1 for s in book.steps if s.status == StepStatus.PENDING),
            "in_progress": sum(1 for s in book.steps if s.status == StepStatus.IN_PROGRESS),
        },
    }


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


def add_evidence(
    db: Session,
    book_id: str,
    evidence_type: str,
    content: str = "",
    step_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> DrillEvidence:
    """Add evidence to a drill book or step."""
    ev = DrillEvidence(
        book_id=book_id,
        step_id=step_id,
        evidence_type=evidence_type,
        content=content,
        metadata_json=metadata,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


# ---------------------------------------------------------------------------
# Child books
# ---------------------------------------------------------------------------


def spawn_child_book(
    db: Session,
    parent_id: str,
    title: str,
    role: Optional[str] = None,
    steps: Optional[list[dict]] = None,
) -> DrillBook:
    """Create a child book under a parent, optionally with pre-defined steps.

    Args:
        steps: list of {"action_type": str, "description": str}
    """
    parent = db.get(DrillBook, parent_id)
    if parent is None:
        raise ValueError(f"Parent book {parent_id} not found")

    child = create_book(
        db,
        title=title,
        description=f"Child of: {parent.title}",
        book_type=parent.book_type,
        parent_id=parent_id,
        corps_id=parent.corps_id,
        role=role or parent.assigned_role,
    )

    if steps:
        for i, step_def in enumerate(steps):
            add_step(
                db,
                book_id=child.id,
                action_type=step_def["action_type"],
                description=step_def.get("description", ""),
                depends_on=step_def.get("depends_on"),
                sequence=i,
            )

    return child
