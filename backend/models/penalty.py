import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class PenaltyType(str, enum.Enum):
    TIMING = "timing"  # Deadline violation
    BUDGET = "budget"  # Token/cost overrun
    RULE = "rule"  # Rule violation


class Penalty(Base):
    """Deduction for a rule violation against a corps.

    Applied by timing officials or judges. Reduces composite score.
    """

    __tablename__ = "penalties"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    corps_id: Mapped[str] = mapped_column(String(36))
    rep_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("reps.id"), nullable=True
    )
    segment_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("segments.id"), nullable=True
    )
    type: Mapped[PenaltyType] = mapped_column(Enum(PenaltyType, values_callable=lambda x: [e.value for e in x]))
    amount: Mapped[float] = mapped_column(Float)  # Points deducted
    reason: Mapped[str] = mapped_column(Text)
    issued_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Penalty({self.type.value}: -{self.amount})>"
