"""Judges Tape — consolidated post-competition evaluation artifact."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class JudgesTape(Base):
    """Consolidated judge feedback for one corps in one competition.

    Contains per-caption feedback and an LLM-generated overall assessment.
    """

    __tablename__ = "judges_tapes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    competition_id: Mapped[str] = mapped_column(String(100))
    corps_id: Mapped[str] = mapped_column(String(36))
    caption_feedbacks: Mapped[dict] = mapped_column(JSON, default=dict)
    overall_assessment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<JudgesTape({self.competition_id}, {self.corps_id})>"
