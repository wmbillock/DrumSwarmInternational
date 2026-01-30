import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class CorpsStatus(str, enum.Enum):
    INITIALIZING = "initializing"
    REHEARSAL = "rehearsal"
    TOUR = "tour"
    COMPLETED = "completed"
    DISBANDED = "disbanded"


class RehearsalMode(str, enum.Enum):
    BASICS = "basics"  # Internal caption self-improvement
    SECTIONALS = "sectionals"  # Per-caption rehearsal
    FULL_ENSEMBLE = "full_ensemble"  # All captions together
    RUN_THROUGH = "run_through"  # Full show execution


class Corps(Base):
    """The agent swarm instantiated for a show.

    Owns all agents, reps, and messages. Can be in rehearsal mode
    (human-guided) or tour mode (autonomous).
    """

    __tablename__ = "corps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    show_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[CorpsStatus] = mapped_column(
        Enum(CorpsStatus), default=CorpsStatus.INITIALIZING
    )
    rehearsal_mode: Mapped[Optional[RehearsalMode]] = mapped_column(
        Enum(RehearsalMode), nullable=True
    )
    tour_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Corps({self.name}, {self.status.value})>"
