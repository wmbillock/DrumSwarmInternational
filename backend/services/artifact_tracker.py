"""Artifact tracking service.

Records generated files in the artifact table, linking them to their
source context (corps, operation, season, show, competition).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.artifact import Artifact, ArtifactType
from backend.models.corps import Corps
from backend.models.performance_record import PerformanceRecord

logger = logging.getLogger(__name__)


def record_artifact(
    db: Session,
    file_path: str,
    artifact_type: ArtifactType,
    *,
    label: Optional[str] = None,
    corps_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    season_id: Optional[str] = None,
    show_slug: Optional[str] = None,
    competition_id: Optional[str] = None,
    size_bytes: Optional[int] = None,
) -> Artifact:
    """Record an artifact in the database.

    If corps_id is provided, automatically resolves corps_name from the DB.
    """
    corps_name = None
    if corps_id:
        corps = db.query(Corps).filter(Corps.id == corps_id).first()
        if corps:
            corps_name = corps.name

    artifact = Artifact(
        artifact_type=artifact_type,
        file_path=file_path,
        label=label,
        corps_id=corps_id,
        corps_name=corps_name,
        operation_id=operation_id,
        season_id=season_id,
        show_slug=show_slug,
        competition_id=competition_id,
        size_bytes=size_bytes,
    )
    db.add(artifact)
    db.commit()
    logger.info(f"Recorded artifact: {artifact_type.value} at {file_path}")
    return artifact


def record_performance(
    db: Session,
    *,
    corps_id: str,
    season_id: str,
    competition_id: str,
    show_slug: str,
    round_number: int,
    placement: int,
    field_size: int,
    final_score: float,
    raw_score: float,
    caption_scores: dict,
    competed_at: Optional[datetime] = None,
) -> PerformanceRecord:
    """Record a competition performance in the durable archive.

    Checks for duplicates (same corps_id + competition_id) before inserting.
    """
    # Check for existing record
    existing = (
        db.query(PerformanceRecord)
        .filter(
            PerformanceRecord.corps_id == corps_id,
            PerformanceRecord.competition_id == competition_id,
        )
        .first()
    )
    if existing:
        logger.debug(
            f"Performance record already exists for {corps_id} in {competition_id}"
        )
        return existing

    # Resolve corps name
    corps_name = corps_id
    corps = db.query(Corps).filter(Corps.id == corps_id).first()
    if corps:
        corps_name = corps.name

    record = PerformanceRecord(
        corps_id=corps_id,
        corps_name=corps_name,
        season_id=season_id,
        competition_id=competition_id,
        show_slug=show_slug,
        round_number=round_number,
        placement=placement,
        field_size=field_size,
        final_score=final_score,
        raw_score=raw_score,
        caption_scores_json=json.dumps(caption_scores) if caption_scores else None,
        competed_at=competed_at,
    )
    db.add(record)
    db.commit()
    logger.info(
        f"Recorded performance: {corps_name} placed #{placement} in {competition_id}"
    )
    return record


def record_standings(
    db: Session,
    season_id: str,
    competition_id: str,
    show_slug: str,
    round_number: int,
    standings: list[dict],
    completed_at: Optional[str] = None,
) -> list[PerformanceRecord]:
    """Record all results from a competition round.

    Called after scoring is finalized. Creates PerformanceRecord entries
    for each corps in the standings.
    """
    competed_dt = None
    if completed_at:
        try:
            competed_dt = datetime.fromisoformat(completed_at)
        except (ValueError, TypeError):
            competed_dt = datetime.now(timezone.utc)

    field_size = len(standings)
    records = []

    for standing in standings:
        corps_id = standing.get("corps_id", "")
        if not corps_id:
            continue

        record = record_performance(
            db,
            corps_id=corps_id,
            season_id=season_id,
            competition_id=competition_id,
            show_slug=show_slug,
            round_number=round_number,
            placement=standing.get("rank", 0),
            field_size=field_size,
            final_score=standing.get("final_score", 0.0),
            raw_score=standing.get("raw_score", 0.0),
            caption_scores=standing.get("caption_scores", {}),
            competed_at=competed_dt,
        )
        records.append(record)

    return records


def get_corps_performance_history(
    db: Session, corps_id: str
) -> list[dict]:
    """Get all performance records for a corps, sorted by most recent first."""
    records = (
        db.query(PerformanceRecord)
        .filter(PerformanceRecord.corps_id == corps_id)
        .order_by(PerformanceRecord.competed_at.desc())
        .all()
    )
    return [r.to_dict() for r in records]


def get_corps_artifacts(
    db: Session, corps_id: str
) -> list[dict]:
    """Get all artifacts linked to a corps."""
    artifacts = (
        db.query(Artifact)
        .filter(Artifact.corps_id == corps_id)
        .order_by(Artifact.created_at.desc())
        .all()
    )
    return [a.to_dict() for a in artifacts]
