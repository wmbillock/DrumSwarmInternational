import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class CorpsStatus(str, enum.Enum):
    INITIALIZING = "initializing"
    WINTER_CAMPS = "winter_camps"  # Planning phase (replaces REHEARSAL)
    ON_TOUR = "on_tour"  # Autonomous execution (replaces TOUR)
    COMPLETED = "completed"
    DISBANDED = "disbanded"


class RehearsalMode(str, enum.Enum):
    BASICS = "basics"  # Self-improvement: understand role, tools, show structure
    SECTIONALS = "sectionals"  # Section coordination: work within caption
    FULL_ENSEMBLE = "full_ensemble"  # Cross-section coordination via PC
    RUN_THROUGH = "run_through"  # Red-green-refactor: implement, test, deliver


class Corps(Base):
    """The agent swarm instantiated for a show.

    Owns all agents, reps, and messages. Status is WINTER_CAMPS (planning)
    or ON_TOUR (autonomous execution). Rehearsal mode tracks progression
    through BASICS → SECTIONALS → FULL_ENSEMBLE → RUN_THROUGH.
    """

    __tablename__ = "corps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    show_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[CorpsStatus] = mapped_column(
        Enum(CorpsStatus, values_callable=lambda x: [e.value for e in x]), default=CorpsStatus.INITIALIZING
    )
    rehearsal_mode: Mapped[Optional[RehearsalMode]] = mapped_column(
        Enum(RehearsalMode, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Corps({self.name}, {self.status.value})>"
