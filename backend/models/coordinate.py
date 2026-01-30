import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class CoordinateType(str, enum.Enum):
    SHOW = "show"
    MOVEMENT = "movement"
    SET = "set"
    COORDINATE = "coordinate"


class CoordinateStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Coordinate(Base):
    __tablename__ = "coordinates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("coordinates.id"), nullable=True
    )
    type: Mapped[CoordinateType] = mapped_column(Enum(CoordinateType))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[CoordinateStatus] = mapped_column(
        Enum(CoordinateStatus), default=CoordinateStatus.PENDING
    )
    caption: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    parent: Mapped[Optional["Coordinate"]] = relationship(
        "Coordinate", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Coordinate"]] = relationship(
        "Coordinate", back_populates="parent"
    )
    reps: Mapped[list["Rep"]] = relationship("Rep", back_populates="coordinate")

    def __repr__(self) -> str:
        return f"<Coordinate({self.type.value}: {self.title})>"


# Import here to avoid circular imports but make relationship work
from backend.models.rep import Rep  # noqa: E402, F401
