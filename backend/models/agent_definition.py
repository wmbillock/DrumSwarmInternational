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


class AgentClassification(str, enum.Enum):
    PERFORMING_MEMBER = "performing_member"
    INSTRUCTIONAL_STAFF = "instructional_staff"
    ADMINISTRATIVE_STAFF = "administrative_staff"
    LOGISTICS = "logistics"
    DCI_ASSIGNED = "dci_assigned"


# Map roles to their classification
ROLE_CLASSIFICATIONS: dict[str, AgentClassification] = {
    "executive_director": AgentClassification.ADMINISTRATIVE_STAFF,
    "program_coordinator": AgentClassification.ADMINISTRATIVE_STAFF,
    "drum_major": AgentClassification.ADMINISTRATIVE_STAFF,
    "drill_writer": AgentClassification.INSTRUCTIONAL_STAFF,
    "music_writer": AgentClassification.INSTRUCTIONAL_STAFF,
    "choreographer": AgentClassification.INSTRUCTIONAL_STAFF,
    "brass_caption_head": AgentClassification.INSTRUCTIONAL_STAFF,
    "percussion_caption_head": AgentClassification.INSTRUCTIONAL_STAFF,
    "guard_caption_head": AgentClassification.INSTRUCTIONAL_STAFF,
    "visual_caption_head": AgentClassification.INSTRUCTIONAL_STAFF,
    "brass_tech": AgentClassification.INSTRUCTIONAL_STAFF,
    "percussion_tech": AgentClassification.INSTRUCTIONAL_STAFF,
    "front_ensemble_tech": AgentClassification.INSTRUCTIONAL_STAFF,
    "guard_tech": AgentClassification.INSTRUCTIONAL_STAFF,
    "visual_tech": AgentClassification.INSTRUCTIONAL_STAFF,
    "timing_judge": AgentClassification.DCI_ASSIGNED,
    "performer": AgentClassification.PERFORMING_MEMBER,
}


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
    classification: Mapped[Optional[AgentClassification]] = mapped_column(
        Enum(AgentClassification, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
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
