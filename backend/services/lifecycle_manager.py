"""Agent lifecycle management — ageouts, auditions, hiring/firing, self-improvement."""

import json
import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_definition import AgentDefinition, ROLE_CLASSIFICATIONS
from backend.models.agent_experience import AgentExperience
from backend.models.performer import Performer, PerformerStatus
from backend.models.self_improvement_log import SelfImprovementLog, ImprovementStatus

logger = logging.getLogger(__name__)

# DCI age limits for performing members
MIN_PERFORMER_AGE = 12
MAX_PERFORMER_AGE = 22


def age_performer(db: Session, performer_id: str) -> Performer:
    """Increment performer age by 1 season. Auto-retire at age limit."""
    performer = db.get(Performer, performer_id)
    if performer is None:
        raise ValueError(f"Performer {performer_id} not found")

    performer.age += 1
    performer.experience_seasons += 1

    if performer.age > MAX_PERFORMER_AGE:
        performer.status = PerformerStatus.RETIRED
        performer.retirement_reason = f"Aged out at {performer.age}"
        logger.info("Performer %s aged out at %d", performer.name, performer.age)

    db.commit()
    db.refresh(performer)
    return performer


def check_ageouts(db: Session) -> list[Performer]:
    """Find all active performers who will age out this season."""
    return (
        db.query(Performer)
        .filter(
            Performer.status == PerformerStatus.ACTIVE,
            Performer.age >= MAX_PERFORMER_AGE,
        )
        .all()
    )


def conduct_auditions(
    db: Session, role_type: str, n_spots: int = 1
) -> list[Performer]:
    """Run auditions — select top performers by trust score for a role."""
    candidates = (
        db.query(Performer)
        .filter(
            Performer.status == PerformerStatus.ACTIVE,
            Performer.role_type == role_type,
            Performer.age <= MAX_PERFORMER_AGE,
        )
        .order_by(Performer.trust_score.desc())
        .limit(n_spots)
        .all()
    )
    logger.info(
        "Auditions for %s: %d candidates, %d selected",
        role_type, len(candidates), min(n_spots, len(candidates)),
    )
    return candidates


def hire_staff(
    db: Session, role: str, corps_id: str, system_prompt: str, **kwargs
) -> AgentDefinition:
    """Create a new staff agent definition."""
    from backend.services.agent_lifecycle import create_definition
    from backend.models.agent_definition import ModelTier

    classification = ROLE_CLASSIFICATIONS.get(role)
    tier = kwargs.pop("model_tier", ModelTier.SONNET)

    defn = create_definition(
        db,
        role=role,
        system_prompt=system_prompt,
        model_tier=tier,
        corps_id=corps_id,
        **kwargs,
    )
    if classification:
        defn.classification = classification
        db.commit()

    logger.info("Hired %s for corps %s", role, corps_id)
    return defn


def fire_staff(db: Session, definition_id: str, reason: str) -> None:
    """Retire a staff definition."""
    defn = db.get(AgentDefinition, definition_id)
    if defn is None:
        raise ValueError(f"Definition {definition_id} not found")

    # We don't delete — mark via a convention (version = -1 means retired)
    defn.version = -1
    db.commit()
    logger.info("Fired %s (%s): %s", defn.role, defn.nickname, reason)


def record_agent_learning(
    db: Session,
    performer_id: str,
    activity_type: str,
    learned_skills: list[str],
    achievements: list[str] | None = None,
    show_id: str | None = None,
    corps_id: str | None = None,
) -> AgentExperience:
    """Record what a performer learned during a session."""
    exp = AgentExperience(
        performer_id=performer_id,
        activity_type=activity_type,
        show_id=show_id,
        corps_id=corps_id,
        learned_skills=json.dumps(learned_skills),
        achievements=json.dumps(achievements or []),
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def propose_self_improvement(
    db: Session,
    definition_id: str,
    changes: dict,
    reason: str,
) -> SelfImprovementLog:
    """Agent proposes a change to its own definition (requires approval)."""
    defn = db.get(AgentDefinition, definition_id)
    if defn is None:
        raise ValueError(f"Definition {definition_id} not found")

    log = SelfImprovementLog(
        agent_definition_id=definition_id,
        old_version=defn.version,
        new_version=defn.version + 1,
        changes=json.dumps(changes),
        reason=reason,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    logger.info("Self-improvement proposed for %s: %s", defn.role, reason[:100])
    return log


def approve_self_improvement(
    db: Session,
    improvement_id: str,
    approver_session_id: str,
) -> AgentDefinition:
    """Caption head approves a self-improvement request."""
    log = db.get(SelfImprovementLog, improvement_id)
    if log is None:
        raise ValueError(f"Improvement {improvement_id} not found")
    if log.status != ImprovementStatus.PENDING:
        raise ValueError(f"Improvement {improvement_id} is {log.status.value}, not pending")

    defn = db.get(AgentDefinition, log.agent_definition_id)
    if defn is None:
        raise ValueError(f"Definition {log.agent_definition_id} not found")

    changes = json.loads(log.changes)

    # Apply changes
    if "system_prompt" in changes:
        defn.system_prompt = changes["system_prompt"]
    if "tools_allowed" in changes:
        defn.tools_allowed = changes["tools_allowed"]

    defn.version = log.new_version
    defn.modified_by = approver_session_id
    log.approved_by = approver_session_id
    log.status = ImprovementStatus.APPROVED

    db.commit()
    db.refresh(defn)
    logger.info("Self-improvement approved for %s v%d", defn.role, defn.version)
    return defn


def reject_self_improvement(
    db: Session,
    improvement_id: str,
    approver_session_id: str,
) -> SelfImprovementLog:
    """Reject a self-improvement request."""
    log = db.get(SelfImprovementLog, improvement_id)
    if log is None:
        raise ValueError(f"Improvement {improvement_id} not found")

    log.approved_by = approver_session_id
    log.status = ImprovementStatus.REJECTED
    db.commit()
    db.refresh(log)
    return log


def conduct_season_transition(db: Session, corps_id: str) -> dict:
    """Run end-of-season lifecycle: age performers, check ageouts, update experience."""
    from backend.models.agent_session import AgentSession, SessionStatus

    results = {"aged": 0, "aged_out": 0, "experience_recorded": 0}

    # Find all performers linked to this corps' sessions
    sessions = (
        db.query(AgentSession)
        .filter(AgentSession.corps_id == corps_id)
        .all()
    )

    performer_ids = {s.performer_id for s in sessions if s.performer_id}

    for pid in performer_ids:
        performer = db.get(Performer, pid)
        if performer and performer.status == PerformerStatus.ACTIVE:
            old_age = performer.age
            age_performer(db, pid)
            results["aged"] += 1
            if performer.age > MAX_PERFORMER_AGE:
                results["aged_out"] += 1

            # Record experience
            record_agent_learning(
                db,
                performer_id=pid,
                activity_type="season_completion",
                learned_skills=[performer.role_type],
                corps_id=corps_id,
            )
            results["experience_recorded"] += 1

    logger.info("Season transition for corps %s: %s", corps_id, results)
    return results
