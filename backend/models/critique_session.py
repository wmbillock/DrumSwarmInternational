"""Critique Session — multi-turn judge-to-staff conversation for post-competition feedback."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class CritiqueStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class CritiqueSession(Base):
    """Multi-turn critique conversation between a judge and staff member."""

    __tablename__ = "critique_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    competition_id: Mapped[str] = mapped_column(String(100))
    corps_id: Mapped[str] = mapped_column(String(36))
    judge_type: Mapped[str] = mapped_column(String(50))
    staff_role: Mapped[str] = mapped_column(String(50))
    status: Mapped[CritiqueStatus] = mapped_column(
        Enum(CritiqueStatus, values_callable=lambda x: [e.value for e in x]),
        default=CritiqueStatus.ACTIVE,
    )
    conversation: Mapped[list] = mapped_column(JSON, default=list)
    action_items: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<CritiqueSession({self.judge_type} → {self.staff_role}, {self.status.value})>"
