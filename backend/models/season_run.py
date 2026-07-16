import enum
import uuid
from typing import Optional

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _enum_values(enum_cls):
    return [item.value for item in enum_cls]


class SeasonRunStatus(str, enum.Enum):
    PLANNING = "planning"
    OFFSEASON = "offseason"
    DESIGN = "design"
    RECRUITING = "recruiting"
    WINTER_CAMPS = "winter_camps"
    ON_TOUR = "on_tour"
    FINALS = "finals"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class SeasonEventType(str, enum.Enum):
    REGULAR = "regular"
    FINALS = "finals"


class SeasonEventStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    REHEARSING = "rehearsing"
    COMPETING = "competing"
    CRITIQUE = "critique"
    CLOSED = "closed"
    BLOCKED = "blocked"


class CorpsSeasonPhase(str, enum.Enum):
    STAFFING = "staffing"
    OFFSEASON_TRAINING = "offseason_training"
    DESIGNING_SHOW = "designing_show"
    RECRUITING = "recruiting"
    WINTER_CAMPS = "winter_camps"
    ON_TOUR = "on_tour"
    FINALS = "finals"
    SEASON_COMPLETE = "season_complete"
    BLOCKED = "blocked"


class CorpsEventPhase(str, enum.Enum):
    NOT_STARTED = "not_started"
    BASICS = "basics"
    VISUAL_BLOCK = "visual_block"
    MUSIC_BLOCK = "music_block"
    FULL_ENSEMBLE = "full_ensemble"
    RUN_THROUGH = "run_through"
    COMPETING = "competing"
    SCORED = "scored"
    CRITIQUE = "critique"
    ADJUSTED = "adjusted"
    CLOSED = "closed"
    BLOCKED = "blocked"


class SeasonRun(Base):
    __tablename__ = "season_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[SeasonRunStatus] = mapped_column(
        Enum(SeasonRunStatus, values_callable=_enum_values),
        default=SeasonRunStatus.PLANNING,
    )
    regular_show_count: Mapped[int] = mapped_column(Integer, default=3)
    winter_camp_count: Mapped[int] = mapped_column(Integer, default=7)
    current_event_index: Mapped[int] = mapped_column(Integer, default=0)
    blocker_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    events: Mapped[list["SeasonEvent"]] = relationship(
        "SeasonEvent",
        cascade="all, delete-orphan",
        back_populates="season_run",
    )
    corps_states: Mapped[list["CorpsSeasonState"]] = relationship(
        "CorpsSeasonState",
        cascade="all, delete-orphan",
        back_populates="season_run",
    )


class SeasonEvent(Base):
    __tablename__ = "season_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    season_run_id: Mapped[str] = mapped_column(
        ForeignKey("season_runs.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[SeasonEventType] = mapped_column(
        Enum(SeasonEventType, values_callable=_enum_values),
        nullable=False,
    )
    status: Mapped[SeasonEventStatus] = mapped_column(
        Enum(SeasonEventStatus, values_callable=_enum_values),
        default=SeasonEventStatus.SCHEDULED,
    )
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    blocker_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    season_run: Mapped["SeasonRun"] = relationship("SeasonRun", back_populates="events")
    corps_event_states: Mapped[list["CorpsEventState"]] = relationship(
        "CorpsEventState",
        cascade="all, delete-orphan",
        back_populates="season_event",
    )


class CorpsSeasonState(Base):
    __tablename__ = "corps_season_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    season_run_id: Mapped[str] = mapped_column(
        ForeignKey("season_runs.id"), nullable=False, index=True
    )
    corps_id: Mapped[str] = mapped_column(ForeignKey("corps.id"), nullable=False, index=True)
    phase: Mapped[CorpsSeasonPhase] = mapped_column(
        Enum(CorpsSeasonPhase, values_callable=_enum_values),
        default=CorpsSeasonPhase.STAFFING,
    )
    prestige_snapshot: Mapped[float] = mapped_column(Float, default=0.0)
    cachet_snapshot: Mapped[float] = mapped_column(Float, default=0.0)
    blocker_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    season_run: Mapped["SeasonRun"] = relationship(
        "SeasonRun", back_populates="corps_states"
    )


class CorpsEventState(Base):
    __tablename__ = "corps_event_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    season_event_id: Mapped[str] = mapped_column(
        ForeignKey("season_events.id"), nullable=False, index=True
    )
    corps_id: Mapped[str] = mapped_column(ForeignKey("corps.id"), nullable=False, index=True)
    phase: Mapped[CorpsEventPhase] = mapped_column(
        Enum(CorpsEventPhase, values_callable=_enum_values),
        default=CorpsEventPhase.NOT_STARTED,
    )
    blocker_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    season_event: Mapped["SeasonEvent"] = relationship(
        "SeasonEvent", back_populates="corps_event_states"
    )
