"""Performer service — CRUD, trust management, retirement, and auditions.

Performers are persistent agent identities that accumulate reputation across
shows. Trust scores drive audition selection and retirement decisions.
"""

import logging
import random
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.performer import Performer, PerformerStatus
from backend.services.memory_bank import get_memory_bank

logger = logging.getLogger(__name__)

# Trust thresholds
TRUST_RETIREMENT_THRESHOLD = 20.0
TRUST_PROBATION_THRESHOLD = 30.0
TRUST_INITIAL = 50.0
TRUST_MAX = 100.0
TRUST_MIN = 0.0

# Trust adjustments
TRUST_SESSION_SUCCESS = 3.0
TRUST_SESSION_SUCCESS_HIGH_SCORE = 5.0
TRUST_SESSION_FAILURE = -10.0
TRUST_SESSION_FAILURE_MILD = -5.0
TRUST_PENALTY_RECEIVED = -3.0

# Name generation components
_FIRST_NAMES = [
    "Apollo", "Atlas", "Blaze", "Cadence", "Dash", "Echo", "Forte",
    "Harmony", "Jazz", "Kai", "Lyric", "Maven", "Nova", "Opus",
    "Phoenix", "Quinn", "Rhythm", "Sax", "Tempo", "Vibe", "Wren", "Zephyr",
    "Aria", "Brio", "Coda", "Dulcet", "Ember", "Flint", "Grove",
    "Herald", "Ivory", "Jubilee", "Kindle", "Lumen", "Meridian",
]
_LAST_NAMES = [
    "Brass", "Clearwater", "Drummond", "Fieldman", "Gale", "Highstep",
    "Ironside", "Jett", "Keane", "Marchand", "Overture", "Picard",
    "Reed", "Sterling", "Vanguard", "Wynne", "Ashford", "Bellows",
    "Copeland", "Denning", "Forester", "Garrison", "Holden",
    "Langley", "Mercer", "Northwind", "Prescott", "Redmond",
]


def _generate_name(db: Session) -> str:
    """Generate a unique performer name."""
    for _ in range(100):
        name = f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"
        existing = db.query(Performer).filter(Performer.name == name).first()
        if not existing:
            return name
    # Fallback with number suffix
    import uuid
    return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}-{uuid.uuid4().hex[:4]}"


def create_performer(
    db: Session,
    role_type: str,
    name: Optional[str] = None,
) -> Performer:
    """Create a new performer with initial trust score."""
    if name is None:
        name = _generate_name(db)

    performer = Performer(
        name=name,
        role_type=role_type,
        trust_score=TRUST_INITIAL,
    )
    db.add(performer)
    db.commit()
    db.refresh(performer)
    logger.info("Created performer %s (%s) for role %s", performer.id, name, role_type)
    return performer


def get_performer(db: Session, performer_id: str) -> Optional[Performer]:
    return db.get(Performer, performer_id)


def get_performers_by_role(
    db: Session,
    role_type: str,
    status: Optional[PerformerStatus] = None,
) -> list[Performer]:
    """Get all performers of a given role type."""
    q = db.query(Performer).filter(Performer.role_type == role_type)
    if status:
        q = q.filter(Performer.status == status)
    return q.order_by(Performer.trust_score.desc()).all()


def list_performers(
    db: Session,
    status: Optional[PerformerStatus] = None,
) -> list[Performer]:
    """List all performers, optionally filtered by status."""
    q = db.query(Performer)
    if status:
        q = q.filter(Performer.status == status)
    return q.order_by(Performer.trust_score.desc()).all()


def update_trust(
    db: Session,
    performer_id: str,
    delta: float,
    reason: str = "",
) -> Performer:
    """Adjust a performer's trust score and handle threshold transitions."""
    performer = db.get(Performer, performer_id)
    if performer is None:
        raise ValueError(f"Performer {performer_id} not found")

    old_trust = performer.trust_score
    performer.trust_score = max(TRUST_MIN, min(TRUST_MAX, performer.trust_score + delta))

    logger.info(
        "Trust update for %s: %.1f -> %.1f (%+.1f) reason=%s",
        performer.name, old_trust, performer.trust_score, delta, reason,
    )

    # Record in capability ledger
    try:
        from backend.models.capability_ledger import LedgerEntryType
        from backend.services.capability_ledger_service import record_entry
        record_entry(
            db, role_type=performer.role_type,
            entry_type=LedgerEntryType.TRUST_CHANGE,
            performer_id=performer.id, performer_name=performer.name,
            trust_before=old_trust, trust_after=performer.trust_score,
            details=reason,
        )
    except Exception:
        pass  # Ledger recording is best-effort

    # Check thresholds
    if performer.trust_score <= TRUST_RETIREMENT_THRESHOLD and performer.status != PerformerStatus.RETIRED:
        retire_performer(db, performer_id, reason=f"Trust dropped to {performer.trust_score:.1f}: {reason}")
    elif performer.trust_score <= TRUST_PROBATION_THRESHOLD and performer.status == PerformerStatus.ACTIVE:
        performer.status = PerformerStatus.PROBATION
        logger.info("Performer %s placed on probation (trust=%.1f)", performer.name, performer.trust_score)

    db.commit()
    db.refresh(performer)
    return performer


def record_session_completion(
    db: Session,
    performer_id: str,
    success: bool,
    score: Optional[float] = None,
) -> Performer:
    """Record a session outcome and update trust accordingly."""
    performer = db.get(Performer, performer_id)
    if performer is None:
        raise ValueError(f"Performer {performer_id} not found")

    performer.total_sessions += 1

    if success:
        performer.successful_sessions += 1
        delta = TRUST_SESSION_SUCCESS_HIGH_SCORE if (score and score >= 80) else TRUST_SESSION_SUCCESS
        reason = f"session_success (score={score})" if score else "session_success"
    else:
        performer.failed_sessions += 1
        delta = TRUST_SESSION_FAILURE_MILD if performer.total_sessions > 10 else TRUST_SESSION_FAILURE
        reason = "session_failure"

    db.commit()
    return update_trust(db, performer_id, delta, reason)


def retire_performer(
    db: Session,
    performer_id: str,
    reason: str = "",
) -> Performer:
    """Retire a performer and store lessons in memory bank."""
    performer = db.get(Performer, performer_id)
    if performer is None:
        raise ValueError(f"Performer {performer_id} not found")

    performer.status = PerformerStatus.RETIRED
    performer.retirement_reason = reason
    db.commit()
    db.refresh(performer)

    logger.info("Retired performer %s (%s): %s", performer.name, performer.role_type, reason)

    # Store retirement lesson in memory bank
    memory_bank = get_memory_bank()
    if memory_bank.available:
        memory_bank.store(
            agent_identity=performer.role_type,
            text=(
                f"Performer {performer.name} was retired from role {performer.role_type}. "
                f"Reason: {reason}. "
                f"Stats: {performer.total_sessions} sessions, "
                f"{performer.successful_sessions} success, "
                f"{performer.failed_sessions} failures, "
                f"final trust: {performer.trust_score:.1f}"
            ),
            metadata={
                "type": "retirement_lesson",
                "performer_id": performer.id,
                "performer_name": performer.name,
                "role_type": performer.role_type,
            },
        )

    return performer


def audition_for_role(
    db: Session,
    role_type: str,
    pool_size: int = 5,
    trainee_ratio: float = 0.4,
) -> Optional[Performer]:
    """Select the best performer for a role from the pool.

    Picks a mix of high-trust veterans and low-session-count trainees
    to balance reliability with development.
    """
    active = get_performers_by_role(db, role_type, status=PerformerStatus.ACTIVE)

    # Also include probation performers (they can still audition)
    probation = get_performers_by_role(db, role_type, status=PerformerStatus.PROBATION)
    pool = active + probation

    if not pool:
        # No performers exist — create one
        return create_performer(db, role_type)

    if len(pool) == 1:
        return pool[0]

    # Split into veterans (sorted by trust) and trainees (sorted by low session count)
    n_trainees = max(1, int(pool_size * trainee_ratio))
    n_veterans = pool_size - n_trainees

    # Veterans: highest trust
    veterans = sorted(pool, key=lambda p: p.trust_score, reverse=True)[:n_veterans]
    # Trainees: lowest session count
    trainees = sorted(pool, key=lambda p: p.total_sessions)[:n_trainees]

    candidates = list({p.id: p for p in veterans + trainees}.values())

    if not candidates:
        return pool[0]

    # Pick the highest trust from candidates
    return max(candidates, key=lambda p: p.trust_score)
