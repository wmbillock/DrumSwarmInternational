import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class JudgeType(str, enum.Enum):
    BRASS = "brass"
    PERCUSSION = "percussion"
    GUARD = "guard"
    VISUAL = "visual"
    GENERAL_EFFECT = "general_effect"
    TIMING = "timing"


class Score(Base):
    """Evaluation of a rep or segment by a judge.

    Scores are 0-100 with a box rating (1-5) for quick triage.
    Judges live at the DCI layer, external to any corps.
    """

    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rep_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("reps.id"), nullable=True
    )
    segment_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("segments.id"), nullable=True
    )
    corps_id: Mapped[str] = mapped_column(String(36))
    judge_type: Mapped[JudgeType] = mapped_column(Enum(JudgeType, values_callable=lambda x: [e.value for e in x]))
    value: Mapped[float] = mapped_column(Float)  # 0-100
    box: Mapped[int] = mapped_column(Integer)  # 1-5 quick triage
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Score({self.judge_type.value}: {self.value}, box {self.box})>"
