"""Persistent operation tracking for long-running async tasks.

Operations are created when the user kicks off an action (advance round,
generate logo, etc.) and polled until completion. State persists across
server restarts via the DB.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class OperationStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Operation(Base):
    __tablename__ = "operations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    operation_type: Mapped[str] = mapped_column(String(100))
    # e.g., "advance_round", "generate_logo", "finalize_draft"
    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus, values_callable=lambda x: [e.value for e in x]),
        default=OperationStatus.PENDING,
    )
    # Context: what entity is this operating on
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # e.g., "season", "corps", "show"
    target_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Human-readable label
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # JSON result or error details
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "operation_type": self.operation_type,
            "status": self.status.value,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "label": self.label,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
