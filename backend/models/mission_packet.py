import uuid
from typing import Optional

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class MissionPacket(Base):
    __tablename__ = "mission_packets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.id"), nullable=False, unique=True, index=True
    )
    corps_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    allowed_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    forbidden_scope: Mapped[list[str]] = mapped_column(JSON, default=list)
    completion_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    handoff_target: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
