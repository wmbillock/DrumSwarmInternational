"""Experiment result model — comparative data from corps running the same show."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ExperimentResult(Base):
    """Stores the result of a corps running a show, for cross-corps comparison."""

    __tablename__ = "experiment_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    corps_id: Mapped[str] = mapped_column(
        ForeignKey("corps.id"), nullable=False
    )
    show_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("shows.id"), nullable=True
    )
    competition_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    season_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # Config snapshot at time of experiment
    llm_provider: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    methodology: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Results
    total_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    caption_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    iterations_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tool_calls_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sessions_spawned: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    failures_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wall_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Qualitative notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Full metrics as JSON
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ExperimentResult(corps={self.corps_id}, score={self.total_score})>"
