"""Agent memory models — structured episodic and semantic memory storage."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class MemoryType(str, enum.Enum):
    DECISION = "decision"
    PROFILE = "profile"
    SUMMARY = "summary"
    PREFERENCE = "preference"
    LESSON = "lesson"


class AgentMemory(Base):
    """Structured episodic memory — explicit, inspectable, editable."""

    __tablename__ = "agent_memory"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_identity: Mapped[str] = mapped_column(String(100), index=True)
    memory_type: Mapped[MemoryType] = mapped_column(
        String(30), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    source_task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<AgentMemory({self.agent_identity}, {self.memory_type}, {self.title[:30]})>"


class TaskMemory(Base):
    """Episodic memory of task executions — checkpoints, outcomes."""

    __tablename__ = "task_memory"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    agent_identity: Mapped[str] = mapped_column(String(100), index=True)
    task_hash: Mapped[str] = mapped_column(String(64), index=True)
    tool_calls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcomes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checkpoints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<TaskMemory({self.agent_identity}, success={self.success})>"
