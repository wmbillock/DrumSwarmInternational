import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class EventType(str, enum.Enum):
    REP_COMPLETED = "rep_completed"
    REP_FAILED = "rep_failed"
    REP_ASSIGNED = "rep_assigned"
    SEGMENT_COMPLETED = "segment_completed"
    SEGMENT_FAILED = "segment_failed"
    PROBLEM_POSTED = "problem_posted"
    PROBLEM_RESOLVED = "problem_resolved"


class Subscription(Base):
    """An agent's subscription to events on a segment or set.

    When a subscribed event fires, a notification Message is created
    and delivered to the subscriber.
    """

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    segment_id: Mapped[str] = mapped_column(ForeignKey("segments.id"))
    subscriber_role: Mapped[str] = mapped_column(String(50))
    subscriber_session_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )
    corps_id: Mapped[str] = mapped_column(String(36))
    event_type: Mapped[EventType] = mapped_column(Enum(EventType, values_callable=lambda x: [e.value for e in x]))
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Subscription({self.subscriber_role} on {self.event_type.value})>"
