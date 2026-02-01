"""WorkLog model — persistent audit trail for agent activity."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class WorkLogEventType:
    """Standard event type constants for structured work logging."""
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    AGENT_FAIL = "agent_fail"
    TOOL_CALL = "tool_call"
    TOOL_SUCCESS = "tool_success"
    TOOL_ERROR = "tool_error"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    HANDOFF_SENT = "handoff_sent"
    HANDOFF_RECEIVED = "handoff_received"
    DECISION_POINT = "decision_point"


class WorkLog(Base):
    __tablename__ = "work_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    corps_id: Mapped[str] = mapped_column(String(36), index=True)
    role: Mapped[str] = mapped_column(String(100))
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    phase: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<WorkLog({self.event_type} by {self.role} at {self.timestamp})>"
