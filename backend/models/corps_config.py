"""Corps configuration model — locked-in LLM + methodology per corps.

Each corps gets a specific provider, model override, methodology, and
architecture style. Running the same show across differently-configured
corps produces comparative experiment data.
"""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class CorpsConfig(Base):
    """Configuration for a corps' LLM provider and development methodology."""

    __tablename__ = "corps_configs"

    corps_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("corps.id"), primary_key=True
    )

    # LLM Provider
    llm_provider: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # "claude", "openai", "ollama-local", "gemini", "mixed"

    llm_model_override: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g. "gpt-4o", "claude-sonnet-4-5", "llama3.1:70b"

    # Development Methodology
    methodology: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # "tdd", "bdd", "xp", "scrum", "kanban", "waterfall", "mob", "pair"

    # Architecture Style
    architecture_style: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # "monolith", "microservices", "event-driven", "layered"

    # Coding style preferences
    coding_style: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Free-form coding style guide

    # Extra configuration as JSON
    extra: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )

    def __repr__(self) -> str:
        return f"<CorpsConfig(corps={self.corps_id}, provider={self.llm_provider}, method={self.methodology})>"
