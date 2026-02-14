"""PerformanceRecord — durable archive of competition results.

These records persist independently of corps lifecycle. When a corps is
disbanded or deleted, its performance records remain as historical evidence.
This is the immutable "action of record" for the scoring system.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class PerformanceRecord(Base):
    """Immutable record of a corps' performance in a competition round.

    Written when standings are finalized. Never updated or deleted.
    Designed to survive corps cleanup — stores corps_name alongside
    corps_id so the record remains human-readable even if the corps
    is deleted from the DB.
    """

    __tablename__ = "performance_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Corps identity (denormalized for durability)
    corps_id: Mapped[str] = mapped_column(String(36), index=True)
    corps_name: Mapped[str] = mapped_column(String(255))

    # Competition context
    season_id: Mapped[str] = mapped_column(String(100), index=True)
    competition_id: Mapped[str] = mapped_column(String(200), index=True)
    show_slug: Mapped[str] = mapped_column(String(255))
    round_number: Mapped[int] = mapped_column(Integer)

    # Results
    placement: Mapped[int] = mapped_column(Integer)
    field_size: Mapped[int] = mapped_column(Integer, default=0)
    final_score: Mapped[float] = mapped_column(Float)
    raw_score: Mapped[float] = mapped_column(Float)

    # Caption scores stored as JSON string
    caption_scores_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp from when the competition was completed
    competed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # When this record was created
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def to_dict(self) -> dict:
        import json
        caption_scores = {}
        if self.caption_scores_json:
            try:
                caption_scores = json.loads(self.caption_scores_json)
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "id": self.id,
            "corps_id": self.corps_id,
            "corps_name": self.corps_name,
            "season_id": self.season_id,
            "competition_id": self.competition_id,
            "show_slug": self.show_slug,
            "round_number": self.round_number,
            "placement": self.placement,
            "field_size": self.field_size,
            "final_score": self.final_score,
            "raw_score": self.raw_score,
            "caption_scores": caption_scores,
            "competed_at": self.competed_at.isoformat() if self.competed_at else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
