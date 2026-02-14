"""CorpsStrategy — per-corps model selection and adaptation policy.

Each corps gets exactly one strategy that governs how it picks models
for its agents: stick with a single provider, mix best-of-breed,
specialize per section, or explore randomly.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ModelPolicy(str, enum.Enum):
    SINGLE_PROVIDER = "single_provider"
    BEST_OF_BREED = "best_of_breed"
    SECTION_SPECIALIZED = "section_specialized"
    RANDOM_EXPLORATION = "random_exploration"


class AdaptationStyle(str, enum.Enum):
    PROMPT_ONLY = "prompt_only"
    MODEL_SWAP = "model_swap"
    FULL = "full"


class CorpsStrategy(Base):
    """Model selection and adaptation strategy for a single corps.

    Exactly one strategy per corps (enforced by unique constraint on corps_id).
    Controls provider preference, risk/exploration rates, and per-section overrides.
    """

    __tablename__ = "corps_strategies"
    __table_args__ = (
        UniqueConstraint("corps_id", name="uq_corps_strategy_corps_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    corps_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("corps.id"), nullable=False
    )
    model_policy: Mapped[str] = mapped_column(String(30), nullable=False)
    preferred_provider: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    risk_tolerance: Mapped[float] = mapped_column(Float, default=0.5)
    exploration_rate: Mapped[float] = mapped_column(Float, default=0.1)
    adaptation_style: Mapped[str] = mapped_column(
        String(20), default=AdaptationStyle.PROMPT_ONLY.value
    )
    section_overrides: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON dict: caption/section → model_spec_id
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<CorpsStrategy(corps={self.corps_id}, policy={self.model_policy})>"
