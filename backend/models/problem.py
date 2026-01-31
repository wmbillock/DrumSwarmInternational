import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ProblemStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class ProblemSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Problem(Base):
    """A persistent issue logged against a segment that survives agent death.

    When an ephemeral performer hits an issue it can't resolve, it posts a Problem
    linked to the segment, then dies. The problem persists for the next agent
    or supervising staff to act on.
    """

    __tablename__ = "problems"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id"))
    corps_id: Mapped[str] = mapped_column(String(36))
    reported_by_role: Mapped[str] = mapped_column(String(50))
    reported_by_session_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )
    severity: Mapped[ProblemSeverity] = mapped_column(
        Enum(ProblemSeverity), default=ProblemSeverity.MEDIUM
    )
    status: Mapped[ProblemStatus] = mapped_column(
        Enum(ProblemStatus), default=ProblemStatus.OPEN
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Problem({self.status.value}: {self.title})>"
