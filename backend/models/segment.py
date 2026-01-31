import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class SegmentType(str, enum.Enum):
    SHOW = "show"
    MOVEMENT = "movement"
    SET = "set"
    SEGMENT = "segment"


class SegmentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("segments.id"), nullable=True
    )
    type: Mapped[SegmentType] = mapped_column(Enum(SegmentType))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[SegmentStatus] = mapped_column(
        Enum(SegmentStatus), default=SegmentStatus.PENDING
    )
    caption: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    parent: Mapped[Optional["Segment"]] = relationship(
        "Segment", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Segment"]] = relationship(
        "Segment", back_populates="parent"
    )
    reps: Mapped[list["Rep"]] = relationship("Rep", back_populates="segment")

    def __repr__(self) -> str:
        return f"<Segment({self.type.value}: {self.title})>"


# Import here to avoid circular imports but make relationship work
from backend.models.rep import Rep  # noqa: E402, F401
