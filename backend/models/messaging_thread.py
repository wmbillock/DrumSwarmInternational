import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ThreadStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class OriginatorRole(str, enum.Enum):
    EXECUTIVE_DIRECTOR = "executive_director"
    PROGRAM_COORDINATOR = "program_coordinator"
    CAPTION_HEAD = "caption_head"
    TECH = "tech"
    MUSIC_WRITER = "music_writer"


class SenderType(str, enum.Enum):
    USER = "user"
    AGENT = "agent"


class Thread(Base):
    __tablename__ = "messaging_threads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    originator_role: Mapped[OriginatorRole] = mapped_column(
        Enum(OriginatorRole, values_callable=lambda x: [e.value for e in x])
    )
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[ThreadStatus] = mapped_column(
        Enum(ThreadStatus, values_callable=lambda x: [e.value for e in x]),
        default=ThreadStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    archive_candidate_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    messages: Mapped[list["ThreadMessage"]] = relationship(
        "ThreadMessage", back_populates="thread", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Thread(subject={self.subject}, status={self.status.value})>"


class ThreadMessage(Base):
    __tablename__ = "thread_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    thread_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("messaging_threads.id", ondelete="CASCADE")
    )
    sender_type: Mapped[SenderType] = mapped_column(
        Enum(SenderType, values_callable=lambda x: [e.value for e in x])
    )
    sender_role: Mapped[str] = mapped_column(String(50))
    sender_name: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    thread: Mapped["Thread"] = relationship("Thread", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ThreadMessage(sender={self.sender_name}, created_at={self.created_at})>"


class ArchivedThread(Base):
    __tablename__ = "archived_threads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    original_thread_id: Mapped[str] = mapped_column(String(36))
    originator_role: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    message_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    archived_by: Mapped[str] = mapped_column(String(36))
    full_text: Mapped[str] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # CSV or JSON string
    decision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ArchivedThread(subject={self.subject}, archived_at={self.archived_at})>"
