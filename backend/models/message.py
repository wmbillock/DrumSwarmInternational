import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class MessageType(str, enum.Enum):
    HANDOFF = "handoff"
    ESCALATION = "escalation"
    FLAG = "flag"
    STATUS = "status"
    DIRECTIVE = "directive"
    FEEDBACK = "feedback"
    QUESTION = "question"
    REQUEST = "request"
    TEN_HUT = "ten_hut"        # System heartbeat wake command
    RESUME_HUT = "resume_hut"  # System command to resume stalled work


class MessagePriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# Priority ordering for queue sorting (lower number = higher priority)
PRIORITY_ORDER = {
    MessagePriority.CRITICAL: 0,
    MessagePriority.HIGH: 1,
    MessagePriority.NORMAL: 2,
    MessagePriority.LOW: 3,
}


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    corps_id: Mapped[str] = mapped_column(String(36))
    from_role: Mapped[str] = mapped_column(String(50))
    from_session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    to_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    type: Mapped[MessageType] = mapped_column(Enum(MessageType, values_callable=lambda x: [e.value for e in x]))
    priority: Mapped[MessagePriority] = mapped_column(
        Enum(MessagePriority, values_callable=lambda x: [e.value for e in x]), default=MessagePriority.NORMAL
    )
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    segment_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("segments.id"), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Message({self.type.value}: {self.subject})>"
