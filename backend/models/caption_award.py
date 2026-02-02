"""Caption Awards model — achievement system for corps, performers, and staff.

Awards humorous achievements at significant activity milestones.
12 categories, each with multiple tiers of achievement.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AwardCategory(str, enum.Enum):
    """12 caption award categories."""
    BRASS_EXCELLENCE = "brass_excellence"
    PERCUSSION_MASTERY = "percussion_mastery"
    GUARD_ARTISTRY = "guard_artistry"
    VISUAL_INNOVATION = "visual_innovation"
    GENERAL_EFFECT = "general_effect"
    ENDURANCE = "endurance"           # sustained activity
    VELOCITY = "velocity"             # speed of completion
    COLLABORATION = "collaboration"    # cross-role handoffs
    RELIABILITY = "reliability"        # low failure rate
    CREATIVITY = "creativity"          # novel approaches
    MENTORSHIP = "mentorship"          # helping other agents improve
    COMEBACK = "comeback"              # recovery from failure


class AwardTier(str, enum.Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class AwardRecipientType(str, enum.Enum):
    CORPS = "corps"
    PERFORMER = "performer"
    STAFF = "staff"


class CaptionAward(Base):
    __tablename__ = "caption_awards"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    category: Mapped[AwardCategory] = mapped_column(
        Enum(AwardCategory, values_callable=lambda x: [e.value for e in x])
    )
    tier: Mapped[AwardTier] = mapped_column(
        Enum(AwardTier, values_callable=lambda x: [e.value for e in x])
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    recipient_type: Mapped[AwardRecipientType] = mapped_column(
        Enum(AwardRecipientType, values_callable=lambda x: [e.value for e in x])
    )
    recipient_id: Mapped[str] = mapped_column(String(36), index=True)
    recipient_name: Mapped[str] = mapped_column(String(200))
    corps_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    season_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    milestone_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<CaptionAward({self.name}, {self.tier.value}, {self.recipient_name})>"
