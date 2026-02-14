"""ModelSpec — a concrete LLM configuration that can be assigned to agents.

Decouples agent definitions from hard-coded ModelTier by allowing
fine-grained model selection: provider, model_id, optional LoRA adapter,
and task-category tagging.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ModelSpecCapability(str, enum.Enum):
    GENERAL = "general"
    FRONTEND = "frontend"
    BACKEND = "backend"
    ARCHITECTURE = "architecture"
    IMAGE_GEN = "image_gen"
    TESTING = "testing"
    DOCUMENTATION = "documentation"


class ModelSpec(Base):
    """A concrete LLM model configuration.

    Captures provider + model_id + optional LoRA adapter so that
    corps strategies can reference specific models by id rather than
    relying on the coarse OPUS/SONNET/HAIKU tier system.
    """

    __tablename__ = "model_specs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[str] = mapped_column(String(200), nullable=False)
    lora_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    adapter_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_categories: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # comma-separated, e.g. "frontend,react,css"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def categories_list(self) -> list[str]:
        if not self.task_categories:
            return []
        return [c.strip() for c in self.task_categories.split(",") if c.strip()]

    def __repr__(self) -> str:
        return f"<ModelSpec({self.name!r} provider={self.provider} model={self.model_id})>"
