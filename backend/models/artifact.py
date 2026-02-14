"""Artifact model — tracks generated files and links them to their source.

Every file created by an operation, agent task, or tool call gets an Artifact
record. This survives corps cleanup and provides a queryable inventory of all
generated content.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ArtifactType(str, enum.Enum):
    LOGO = "logo"
    SPEC = "spec"
    DESIGN_NOTES = "design_notes"
    SHOW_PROMPT = "show_prompt"
    POST_MORTEM = "post_mortem"
    STANDINGS = "standings"
    SCORES = "scores"
    CRITIQUE = "critique"
    CODE = "code"
    DOCUMENT = "document"
    IMAGE = "image"
    OTHER = "other"


class Artifact(Base):
    """A generated file or output linked to its source context.

    Artifacts persist independently of corps lifecycle — deleting or
    disbanding a corps does NOT delete its artifact records.
    """

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # What kind of artifact
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType, values_callable=lambda x: [e.value for e in x]),
        default=ArtifactType.OTHER,
    )
    # Where it lives on disk (relative to project root)
    file_path: Mapped[str] = mapped_column(String(500))
    # Human-readable label
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Source context — what created this artifact
    corps_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    corps_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    operation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    season_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    show_slug: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    competition_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Size in bytes (optional, for inventory)
    size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "artifact_type": self.artifact_type.value,
            "file_path": self.file_path,
            "label": self.label,
            "corps_id": self.corps_id,
            "corps_name": self.corps_name,
            "operation_id": self.operation_id,
            "season_id": self.season_id,
            "show_slug": self.show_slug,
            "competition_id": self.competition_id,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
