"""Capability ledger — permanent record of agent completions and failures.

Every rep completion, session completion, and failure is logged here.
Feeds trust score calculations and audition decisions.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class LedgerEntryType(str, enum.Enum):
    REP_COMPLETED = "rep_completed"
    REP_FAILED = "rep_failed"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"
    TRUST_CHANGE = "trust_change"
    RETIREMENT = "retirement"
    GUPP_VIOLATION = "gupp_violation"


class CapabilityLedgerEntry(Base):
    """Permanent record of an agent capability event."""

    __tablename__ = "capability_ledger"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    performer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    performer_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    role_type: Mapped[str] = mapped_column(String(50))
    entry_type: Mapped[LedgerEntryType] = mapped_column(Enum(LedgerEntryType))
    corps_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    rep_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trust_before: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trust_after: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
