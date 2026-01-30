import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


# Terminal statuses — no further transitions allowed
TERMINAL_STATUSES = {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.TIMED_OUT}


class AgentSession(Base):
    """A running instance of an AgentDefinition.

    Performers spawn per rep and die when done. Staff agents are longer-lived
    but still session-based. Context snapshots on completion allow successors
    to warm up without replaying full conversation history.
    """

    __tablename__ = "agent_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    definition_id: Mapped[str] = mapped_column(ForeignKey("agent_definitions.id"))
    corps_id: Mapped[str] = mapped_column(String(36))
    parent_session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("agent_sessions.id"), nullable=True
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.ACTIVE
    )
    context_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    definition: Mapped["AgentDefinition"] = relationship("AgentDefinition")
    parent: Mapped[Optional["AgentSession"]] = relationship(
        "AgentSession", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["AgentSession"]] = relationship(
        "AgentSession", back_populates="parent"
    )

    def __repr__(self) -> str:
        return f"<AgentSession({self.status.value} for {self.definition_id})>"


from backend.models.agent_definition import AgentDefinition  # noqa: E402, F401
