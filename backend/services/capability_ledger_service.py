"""Capability ledger service — record and query agent capability events."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.capability_ledger import CapabilityLedgerEntry, LedgerEntryType

logger = logging.getLogger(__name__)


def record_entry(
    db: Session,
    role_type: str,
    entry_type: LedgerEntryType,
    performer_id: Optional[str] = None,
    performer_name: Optional[str] = None,
    corps_id: Optional[str] = None,
    session_id: Optional[str] = None,
    rep_id: Optional[str] = None,
    score: Optional[float] = None,
    trust_before: Optional[float] = None,
    trust_after: Optional[float] = None,
    details: Optional[str] = None,
) -> CapabilityLedgerEntry:
    """Record a capability ledger entry."""
    entry = CapabilityLedgerEntry(
        performer_id=performer_id,
        performer_name=performer_name,
        role_type=role_type,
        entry_type=entry_type,
        corps_id=corps_id,
        session_id=session_id,
        rep_id=rep_id,
        score=score,
        trust_before=trust_before,
        trust_after=trust_after,
        details=details,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_entries_for_performer(
    db: Session,
    performer_id: str,
    entry_type: Optional[LedgerEntryType] = None,
    limit: int = 50,
) -> list[CapabilityLedgerEntry]:
    """Get ledger entries for a performer."""
    q = db.query(CapabilityLedgerEntry).filter(
        CapabilityLedgerEntry.performer_id == performer_id
    )
    if entry_type:
        q = q.filter(CapabilityLedgerEntry.entry_type == entry_type)
    return q.order_by(CapabilityLedgerEntry.created_at.desc()).limit(limit).all()


def get_entries_for_corps(
    db: Session,
    corps_id: str,
    limit: int = 100,
) -> list[CapabilityLedgerEntry]:
    """Get ledger entries for a corps."""
    return (
        db.query(CapabilityLedgerEntry)
        .filter(CapabilityLedgerEntry.corps_id == corps_id)
        .order_by(CapabilityLedgerEntry.created_at.desc())
        .limit(limit)
        .all()
    )


def get_performer_stats(db: Session, performer_id: str) -> dict:
    """Get aggregate stats from the capability ledger for a performer."""
    entries = get_entries_for_performer(db, performer_id, limit=1000)
    stats = {
        "total_entries": len(entries),
        "reps_completed": sum(1 for e in entries if e.entry_type == LedgerEntryType.REP_COMPLETED),
        "reps_failed": sum(1 for e in entries if e.entry_type == LedgerEntryType.REP_FAILED),
        "sessions_completed": sum(1 for e in entries if e.entry_type == LedgerEntryType.SESSION_COMPLETED),
        "sessions_failed": sum(1 for e in entries if e.entry_type == LedgerEntryType.SESSION_FAILED),
        "gupp_violations": sum(1 for e in entries if e.entry_type == LedgerEntryType.GUPP_VIOLATION),
    }
    scored = [e for e in entries if e.score is not None]
    stats["avg_score"] = sum(e.score for e in scored) / len(scored) if scored else None
    return stats
