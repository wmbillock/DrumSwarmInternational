"""Performer model — persistent agent identity with trust scoring.

Performers persist across shows, accumulate reputation through trust scores,
and can be retired/replaced when trust drops too low.

Staff vs. Performers:
- Staff (is_verified=True): Trusted individuals with demonstrated expertise.
  They hold instructional/admin roles and are hired directly, not drafted.
- Performers (is_verified=False): Unverified until auditioned or deemed
  good enough. They are drafted from the talent pool into corps rosters.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class PerformerStatus(str, enum.Enum):
    ACTIVE = "active"
    PROBATION = "probation"
    RETIRED = "retired"


class AgentCategory(str, enum.Enum):
    PERFORMER = "performer"
    INSTRUCTIONAL_STAFF = "instructional_staff"
    ADMINISTRATIVE_STAFF = "administrative_staff"


class Performer(Base):
    __tablename__ = "performers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), unique=True)
    role_type: Mapped[str] = mapped_column(String(50), index=True)
    corps_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    trust_score: Mapped[float] = mapped_column(Float, default=50.0)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    successful_sessions: Mapped[int] = mapped_column(Integer, default=0)
    failed_sessions: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[PerformerStatus] = mapped_column(
        Enum(PerformerStatus, values_callable=lambda x: [e.value for e in x]), default=PerformerStatus.ACTIVE
    )
    age: Mapped[int] = mapped_column(Integer, default=16)
    experience_seasons: Mapped[int] = mapped_column(Integer, default=0)
    specialties: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retirement_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Staff vs. performer differentiation
    agent_category: Mapped[str] = mapped_column(
        String(30), default=AgentCategory.PERFORMER.value, index=True
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def is_staff(self) -> bool:
        return self.agent_category != AgentCategory.PERFORMER.value

    def __repr__(self) -> str:
        cat = "staff" if self.is_staff else "performer"
        return f"<Performer({self.name}, {self.role_type}, {cat}, trust={self.trust_score:.1f})>"
