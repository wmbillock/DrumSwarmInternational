import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ModelTier(str, enum.Enum):
    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


# Fields that require caption head approval to modify
MAJOR_CHANGE_FIELDS = {"model_tier", "tools_allowed"}


class AgentDefinition(Base):
    """A versioned template defining an agent's role, capabilities, and constraints.

    Techs can modify definitions at runtime (self-improving system).
    Minor changes (system_prompt tweaks) are free.
    Major changes (tools_allowed, model_tier) require caption head approval.
    """

    __tablename__ = "agent_definitions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    role: Mapped[str] = mapped_column(String(50))
    system_prompt: Mapped[str] = mapped_column(Text)
    model_tier: Mapped[ModelTier] = mapped_column(
        Enum(ModelTier, values_callable=lambda x: [e.value for e in x]), default=ModelTier.SONNET
    )
    # Comma-separated list of allowed tool names
    tools_allowed: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    modified_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    corps_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def tools_allowed_list(self) -> list[str]:
        if not self.tools_allowed:
            return []
        return [t.strip() for t in self.tools_allowed.split(",") if t.strip()]

    def __repr__(self) -> str:
        return f"<AgentDefinition({self.role} v{self.version})>"
