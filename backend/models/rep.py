import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.segment import Segment


class RepStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


# Valid transitions for the rep state machine
VALID_TRANSITIONS: dict[RepStatus, set[RepStatus]] = {
    RepStatus.PENDING: {RepStatus.ASSIGNED},
    RepStatus.ASSIGNED: {RepStatus.IN_PROGRESS, RepStatus.PENDING},
    RepStatus.IN_PROGRESS: {RepStatus.REVIEW, RepStatus.FAILED},
    RepStatus.REVIEW: {RepStatus.COMPLETED, RepStatus.FAILED, RepStatus.IN_PROGRESS},
    RepStatus.COMPLETED: set(),
    RepStatus.FAILED: set(),
}


class Rep(Base):
    __tablename__ = "reps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id"))
    assigned_to: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[RepStatus] = mapped_column(
        Enum(RepStatus), default=RepStatus.PENDING
    )
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    segment: Mapped["Segment"] = relationship(
        "Segment", back_populates="reps"
    )

    def __repr__(self) -> str:
        return f"<Rep({self.status.value} for {self.segment_id})>"
