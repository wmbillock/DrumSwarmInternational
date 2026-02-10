"""Drill Book models — persistent, resumable work units.

A drill book tracks a unit of work from inception to verified completion.
It survives agent session death, context loss, and system restarts.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class BookStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    VERIFIED = "verified"
    FAILED = "failed"
    ABANDONED = "abandoned"


TERMINAL_BOOK_STATUSES = {BookStatus.COMPLETED, BookStatus.VERIFIED, BookStatus.FAILED, BookStatus.ABANDONED}


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"


TERMINAL_STEP_STATUSES = {StepStatus.COMPLETED, StepStatus.VERIFIED, StepStatus.FAILED, StepStatus.SKIPPED}


class BookType(str, enum.Enum):
    LINEAR = "linear"
    BRANCHING = "branching"
    DAG = "dag"


class EvidenceType(str, enum.Enum):
    FILE_DIFF = "file_diff"
    COMMAND_OUTPUT = "command_output"
    TEST_RESULT = "test_result"
    EVALUATION = "evaluation"
    SCREENSHOT = "screenshot"
    GENERATED_IMAGE = "generated_image"


class DrillBook(Base):
    """A persistent, resumable unit of work.

    Hierarchical: parent books spawn child books.
    Auditable: every step links to evidence.
    Cold-resumable: context_summary + context_snapshot let a new agent pick up.
    """

    __tablename__ = "drill_books"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("drill_books.id"), nullable=True
    )
    corps_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("corps.id"), nullable=True
    )
    assigned_performer_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("performers.id"), nullable=True
    )
    assigned_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    book_type: Mapped[str] = mapped_column(
        String(20), default=BookType.LINEAR.value
    )
    status: Mapped[BookStatus] = mapped_column(
        Enum(BookStatus, values_callable=lambda x: [e.value for e in x]),
        default=BookStatus.PENDING,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Context for cold pickup
    context_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    steps: Mapped[list["DrillStep"]] = relationship(
        "DrillStep", back_populates="book", order_by="DrillStep.sequence",
        cascade="all, delete-orphan",
    )
    children: Mapped[list["DrillBook"]] = relationship(
        "DrillBook", back_populates="parent",
    )
    parent: Mapped[Optional["DrillBook"]] = relationship(
        "DrillBook", remote_side=[id], back_populates="children",
    )
    evidence: Mapped[list["DrillEvidence"]] = relationship(
        "DrillEvidence",
        back_populates="book",
        primaryjoin="DrillEvidence.book_id == DrillBook.id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DrillBook({self.title!r} [{self.status.value}])>"


class DrillStep(Base):
    """A single step within a drill book."""

    __tablename__ = "drill_steps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    book_id: Mapped[str] = mapped_column(
        ForeignKey("drill_books.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[StepStatus] = mapped_column(
        Enum(StepStatus, values_callable=lambda x: [e.value for e in x]),
        default=StepStatus.PENDING,
    )

    # DAG/branching support
    depends_on: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    next_steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Execution tracking
    assigned_session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("agent_sessions.id"), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    book: Mapped["DrillBook"] = relationship("DrillBook", back_populates="steps")
    evidence_items: Mapped[list["DrillEvidence"]] = relationship(
        "DrillEvidence", back_populates="step",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DrillStep(#{self.sequence} {self.action_type} [{self.status.value}])>"


class DrillEvidence(Base):
    """Evidence attached to a drill book or step."""

    __tablename__ = "drill_evidence"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    book_id: Mapped[str] = mapped_column(
        ForeignKey("drill_books.id"), nullable=False
    )
    step_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("drill_steps.id"), nullable=True
    )
    evidence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    book: Mapped["DrillBook"] = relationship(
        "DrillBook", back_populates="evidence",
        primaryjoin="DrillEvidence.book_id == DrillBook.id",
    )
    step: Mapped[Optional["DrillStep"]] = relationship(
        "DrillStep", back_populates="evidence_items",
    )

    def __repr__(self) -> str:
        return f"<DrillEvidence({self.evidence_type} for book={self.book_id[:8]})>"
