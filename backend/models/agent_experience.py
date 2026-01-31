"""Agent experience — tracks what performers learn across shows."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AgentExperience(Base):
    __tablename__ = "agent_experience"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    performer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("performers.id"), nullable=False
    )
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    show_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    corps_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    learned_skills: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    achievements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<AgentExperience({self.performer_id}, {self.activity_type})>"
