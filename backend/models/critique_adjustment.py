import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CritiqueAdjustment(Base):
    __tablename__ = "critique_adjustments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    season_event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    corps_id: Mapped[str] = mapped_column(ForeignKey("corps.id"), nullable=False, index=True)
    corps_event_state_id: Mapped[str] = mapped_column(
        ForeignKey("corps_event_states.id"), nullable=False, index=True
    )
    caption: Mapped[str] = mapped_column(String(50), nullable=False)
    source_tape_id: Mapped[str] = mapped_column(
        ForeignKey("judging_tapes.id"), nullable=False, index=True
    )
    action_summary: Mapped[str] = mapped_column(Text, nullable=False)

    event_state = relationship("CorpsEventState")
