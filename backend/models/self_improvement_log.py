"""Self-improvement log — audit trail for agent self-modifications."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ImprovementStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SelfImprovementLog(Base):
    __tablename__ = "self_improvement_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_definition_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_definitions.id"), nullable=False
    )
    old_version: Mapped[int] = mapped_column(Integer, nullable=False)
    new_version: Mapped[int] = mapped_column(Integer, nullable=False)
    changes: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[ImprovementStatus] = mapped_column(
        Enum(ImprovementStatus, values_callable=lambda x: [e.value for e in x]),
        default=ImprovementStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<SelfImprovementLog({self.agent_definition_id}, v{self.old_version}→v{self.new_version}, {self.status.value})>"
