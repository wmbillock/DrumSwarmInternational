import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class JudgingTape(Base):
    __tablename__ = "judging_tapes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    season_event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    corps_id: Mapped[str] = mapped_column(ForeignKey("corps.id"), nullable=False, index=True)
    rep_id: Mapped[str | None] = mapped_column(ForeignKey("reps.id"), nullable=True, index=True)
    artifact_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    caption: Mapped[str] = mapped_column(String(50), nullable=False)
    tape_text: Mapped[str] = mapped_column(Text, nullable=False)
