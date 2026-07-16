import enum
import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _enum_values(enum_cls):
    return [item.value for item in enum_cls]


class RehearsalBlockType(str, enum.Enum):
    WINTER_CAMP = "winter_camp"
    BASICS = "basics"
    VISUAL_BLOCK = "visual_block"
    MUSIC_BLOCK = "music_block"
    SECTIONAL = "sectional"
    FULL_ENSEMBLE = "full_ensemble"
    RUN_THROUGH = "run_through"


class RehearsalBlockStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class RehearsalBlock(Base):
    __tablename__ = "rehearsal_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    season_run_id: Mapped[str] = mapped_column(
        ForeignKey("season_runs.id"), nullable=False, index=True
    )
    season_event_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("season_events.id"), nullable=True, index=True
    )
    corps_id: Mapped[str] = mapped_column(ForeignKey("corps.id"), nullable=False, index=True)
    block_type: Mapped[RehearsalBlockType] = mapped_column(
        Enum(RehearsalBlockType, values_callable=_enum_values), nullable=False
    )
    status: Mapped[RehearsalBlockStatus] = mapped_column(
        Enum(RehearsalBlockStatus, values_callable=_enum_values),
        default=RehearsalBlockStatus.SCHEDULED,
    )
    sequence_index: Mapped[int] = mapped_column(Integer, default=1)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
