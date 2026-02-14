"""ModelSpecPerformance — tracks how well each ModelSpec performs per task category.

Accumulates outcome data (attempts, scores) so the system can pick the
best-performing model for a given task type, optionally scoped to a corps.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ModelSpecPerformance(Base):
    """Aggregate performance record for a model spec in a task category.

    One row per (model_spec_id, task_category, corps_id) triple.
    corps_id=NULL means global (cross-corps) stats.
    """

    __tablename__ = "model_spec_performances"
    __table_args__ = (
        UniqueConstraint(
            "model_spec_id", "task_category", "corps_id",
            name="uq_msp_spec_category_corps",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    model_spec_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_specs.id"), nullable=False
    )
    task_category: Mapped[str] = mapped_column(String(50), nullable=False)
    corps_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("corps.id"), nullable=True
    )
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    successful_attempts: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_score: Mapped[float] = mapped_column(Float, default=0.0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<ModelSpecPerformance(spec={self.model_spec_id[:8]}, "
            f"cat={self.task_category}, avg={self.avg_score:.1f}, "
            f"n={self.total_attempts})>"
        )
