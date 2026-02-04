"""Achievement detector — monitors activity milestones and awards caption awards."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.caption_award import (
    AwardCategory, AwardTier, AwardRecipientType, CaptionAward,
)
from backend.models.agent_definition import AgentClassification, ROLE_CLASSIFICATIONS
from backend.services.achievement_catalog import load_achievement_catalog, AchievementDefinition
from backend.services.event_bus import get_event_bus

logger = logging.getLogger(__name__)


def _recipient_type_for_performer(role_type: str) -> AwardRecipientType:
    classification = ROLE_CLASSIFICATIONS.get(role_type)
    if classification == AgentClassification.PERFORMING_MEMBER or role_type == "performer":
        return AwardRecipientType.PERFORMER
    return AwardRecipientType.STAFF


def _already_awarded(db: Session, recipient_id: str, award_name: str) -> bool:
    """Check if this exact award has already been given."""
    return db.query(CaptionAward).filter(
        CaptionAward.recipient_id == recipient_id,
        CaptionAward.name == award_name,
    ).count() > 0


def _compare(op: str, left: float, right: float) -> bool:
    if op == ">=":
        return left >= right
    if op == ">":
        return left > right
    if op == "==":
        return left == right
    if op == "<=":
        return left <= right
    if op == "<":
        return left < right
    return False


def _performer_metrics(db: Session, performer_id: str, corps_id: Optional[str], caption: Optional[str]) -> dict[str, float]:
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.performer import Performer
    from backend.models.rep import Rep, RepStatus
    from backend.models.score import Score, JudgeType
    from backend.models.segment import Segment
    from backend.models.message import Message, MessageType

    performer = db.get(Performer, performer_id)
    if not performer:
        return {}

    session_query = db.query(AgentSession).filter(AgentSession.performer_id == performer_id)
    if corps_id:
        session_query = session_query.filter(AgentSession.corps_id == corps_id)

    sessions_total = session_query.count()
    sessions_completed = session_query.filter(AgentSession.status == SessionStatus.COMPLETED).count()
    sessions_failed = session_query.filter(AgentSession.status == SessionStatus.FAILED).count()

    rep_query = db.query(Rep).join(
        AgentSession, Rep.assigned_to == AgentSession.id
    ).filter(AgentSession.performer_id == performer_id)
    if corps_id:
        rep_query = rep_query.filter(AgentSession.corps_id == corps_id)

    if caption:
        rep_query = rep_query.join(Segment, Segment.id == Rep.segment_id).filter(Segment.caption == caption)

    reps_completed = rep_query.filter(Rep.status == RepStatus.COMPLETED).count()
    reps_failed = rep_query.filter(Rep.status == RepStatus.FAILED).count()

    score_query = db.query(func.avg(Score.value)).join(
        Rep, Rep.id == Score.rep_id
    ).join(
        AgentSession, Rep.assigned_to == AgentSession.id
    ).filter(AgentSession.performer_id == performer_id)
    if corps_id:
        score_query = score_query.filter(AgentSession.corps_id == corps_id)
    if caption:
        try:
            score_query = score_query.filter(Score.judge_type == JudgeType(caption))
        except ValueError:
            pass
    avg_score = score_query.scalar() or 0.0

    max_reps_in_session = (
        db.query(func.count(Rep.id))
        .join(AgentSession, Rep.assigned_to == AgentSession.id)
        .filter(
            AgentSession.performer_id == performer_id,
            Rep.status == RepStatus.COMPLETED,
        )
        .group_by(Rep.assigned_to)
        .order_by(func.count(Rep.id).desc())
        .limit(1)
        .scalar()
    ) or 0

    unique_captions = (
        db.query(func.count(func.distinct(Segment.caption)))
        .join(Rep, Rep.segment_id == Segment.id)
        .join(AgentSession, Rep.assigned_to == AgentSession.id)
        .filter(
            AgentSession.performer_id == performer_id,
            Rep.status == RepStatus.COMPLETED,
        )
        .scalar()
    ) or 0

    handoffs_sent = (
        db.query(Message)
        .filter(
            Message.from_role == performer.role_type,
            Message.type == MessageType.HANDOFF,
        )
    )
    if corps_id:
        handoffs_sent = handoffs_sent.filter(Message.corps_id == corps_id)
    handoffs_sent = handoffs_sent.count()

    success_rate = sessions_completed / max(sessions_total, 1)
    comeback_count = min(reps_failed, reps_completed)

    return {
        "sessions_total": sessions_total,
        "sessions_completed": sessions_completed,
        "sessions_failed": sessions_failed,
        "success_rate": success_rate,
        "reps_completed": reps_completed,
        "reps_failed": reps_failed,
        "avg_score": avg_score,
        "caption_avg_score": avg_score,
        "max_reps_in_session": max_reps_in_session,
        "unique_captions": unique_captions,
        "handoffs_sent": handoffs_sent,
        "comeback_count": comeback_count,
        "trust_score": performer.trust_score,
    }


def _corps_metrics(db: Session, corps_id: str, caption: Optional[str]) -> dict[str, float]:
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.rep import Rep, RepStatus
    from backend.models.score import Score, JudgeType
    from backend.models.segment import Segment
    from backend.models.message import Message, MessageType
    from backend.models.agent_definition import AgentDefinition
    from backend.models.show import Show, ShowStatus

    sessions_total = db.query(AgentSession).filter(AgentSession.corps_id == corps_id).count()
    sessions_completed = db.query(AgentSession).filter(
        AgentSession.corps_id == corps_id,
        AgentSession.status == SessionStatus.COMPLETED,
    ).count()
    sessions_failed = db.query(AgentSession).filter(
        AgentSession.corps_id == corps_id,
        AgentSession.status == SessionStatus.FAILED,
    ).count()

    rep_query = db.query(Rep).join(
        AgentSession, Rep.assigned_to == AgentSession.id
    ).filter(AgentSession.corps_id == corps_id)
    if caption:
        rep_query = rep_query.join(Segment, Segment.id == Rep.segment_id).filter(Segment.caption == caption)
    reps_completed = rep_query.filter(Rep.status == RepStatus.COMPLETED).count()
    reps_failed = rep_query.filter(Rep.status == RepStatus.FAILED).count()

    score_query = db.query(func.avg(Score.value)).filter(Score.corps_id == corps_id)
    if caption:
        try:
            score_query = score_query.filter(Score.judge_type == JudgeType(caption))
        except ValueError:
            pass
    avg_score = score_query.scalar() or 0.0

    max_reps_in_session = (
        db.query(func.count(Rep.id))
        .join(AgentSession, Rep.assigned_to == AgentSession.id)
        .filter(
            AgentSession.corps_id == corps_id,
            Rep.status == RepStatus.COMPLETED,
        )
        .group_by(Rep.assigned_to)
        .order_by(func.count(Rep.id).desc())
        .limit(1)
        .scalar()
    ) or 0

    unique_segment_types = (
        db.query(func.count(func.distinct(Segment.type)))
        .join(Rep, Rep.segment_id == Segment.id)
        .join(AgentSession, Rep.assigned_to == AgentSession.id)
        .filter(AgentSession.corps_id == corps_id)
        .scalar()
    ) or 0

    unique_captions = (
        db.query(func.count(func.distinct(Segment.caption)))
        .join(Rep, Rep.segment_id == Segment.id)
        .join(AgentSession, Rep.assigned_to == AgentSession.id)
        .filter(AgentSession.corps_id == corps_id)
        .scalar()
    ) or 0

    handoffs_sent = db.query(Message).filter(
        Message.corps_id == corps_id,
        Message.type == MessageType.HANDOFF,
    ).count()

    unique_roles = db.query(func.count(func.distinct(AgentDefinition.role))).filter(
        AgentDefinition.corps_id == corps_id
    ).scalar() or 0

    shows_completed = db.query(Show).filter(
        Show.corps_id == corps_id,
        Show.status == ShowStatus.COMPLETED,
    ).count()

    success_rate = sessions_completed / max(sessions_total, 1)
    comeback_count = min(reps_failed, reps_completed)

    return {
        "sessions_total": sessions_total,
        "sessions_completed": sessions_completed,
        "sessions_failed": sessions_failed,
        "success_rate": success_rate,
        "reps_completed": reps_completed,
        "reps_failed": reps_failed,
        "avg_score": avg_score,
        "caption_avg_score": avg_score,
        "max_reps_in_session": max_reps_in_session,
        "unique_segment_types": unique_segment_types,
        "unique_captions": unique_captions,
        "handoffs_sent": handoffs_sent,
        "unique_roles": unique_roles,
        "shows_completed": shows_completed,
        "comeback_count": comeback_count,
    }


def _evaluate_award(
    db: Session,
    achievement: AchievementDefinition,
    recipient_type: AwardRecipientType,
    recipient_id: str,
    recipient_name: str,
    corps_id: Optional[str],
) -> Optional[CaptionAward]:
    if _already_awarded(db, recipient_id, achievement.name):
        return None

    trigger = achievement.trigger
    caption = trigger.caption
    if recipient_type == AwardRecipientType.CORPS:
        metrics = _corps_metrics(db, recipient_id, caption)
    else:
        metrics = _performer_metrics(db, recipient_id, corps_id, caption)

    if trigger.min_total_sessions is not None and metrics.get("sessions_total", 0) < trigger.min_total_sessions:
        return None
    if trigger.min_reps_completed is not None and metrics.get("reps_completed", 0) < trigger.min_reps_completed:
        return None
    if trigger.min_success_rate is not None and metrics.get("success_rate", 0) < trigger.min_success_rate:
        return None

    metric_value = metrics.get(trigger.metric)
    if metric_value is None:
        return None
    if not _compare(trigger.op, metric_value, trigger.value):
        return None

    milestone_value = None
    if isinstance(trigger.value, (int, float)):
        if isinstance(trigger.value, float) and trigger.value < 1:
            milestone_value = int(trigger.value * 100)
        else:
            milestone_value = int(trigger.value)

    award = CaptionAward(
        category=AwardCategory(achievement.category),
        tier=AwardTier(achievement.tier),
        name=achievement.name,
        description=achievement.description,
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        recipient_name=recipient_name,
        corps_id=corps_id if recipient_type != AwardRecipientType.CORPS else recipient_id,
        milestone_value=milestone_value,
    )
    db.add(award)
    logger.info("Achievement unlocked: %s -> %s", recipient_name, achievement.name)
    return award


def _award_for_scope(
    db: Session,
    scope: str,
    recipient_type: AwardRecipientType,
    recipient_id: str,
    recipient_name: str,
    corps_id: Optional[str],
) -> list[CaptionAward]:
    awarded: list[CaptionAward] = []
    for achievement in load_achievement_catalog():
        if achievement.scope != scope:
            continue
        try:
            award = _evaluate_award(db, achievement, recipient_type, recipient_id, recipient_name, corps_id)
        except Exception:
            logger.exception("Achievement evaluation failed for %s", achievement.name)
            continue
        if award:
            awarded.append(award)
    if awarded:
        db.commit()
        bus = get_event_bus()
        for award in awarded:
            bus.publish("award.unlocked", {
                "type": "award.unlocked",
                "corps_id": award.corps_id,
                "recipient_id": award.recipient_id,
                "recipient_name": award.recipient_name,
                "recipient_type": award.recipient_type.value,
                "category": award.category.value,
                "tier": award.tier.value,
                "name": award.name,
                "description": award.description,
                "milestone_value": award.milestone_value,
                "awarded_at": award.awarded_at.isoformat() if award.awarded_at else None,
            })
    return awarded


def check_performer_achievements(
    db: Session,
    performer_id: str,
    performer_name: str,
    corps_id: Optional[str] = None,
    role_type: Optional[str] = None,
) -> list[CaptionAward]:
    """Check and award achievements for a performer based on current stats."""
    from backend.models.performer import Performer

    performer = db.get(Performer, performer_id)
    if not performer:
        return []
    role_type = role_type or performer.role_type
    recipient_type = _recipient_type_for_performer(role_type)
    scope = "performer" if recipient_type == AwardRecipientType.PERFORMER else "staff"
    return _award_for_scope(db, scope, recipient_type, performer_id, performer_name, corps_id)


def check_staff_achievements(
    db: Session,
    performer_id: str,
    performer_name: str,
    corps_id: Optional[str] = None,
    role_type: Optional[str] = None,
) -> list[CaptionAward]:
    """Check and award achievements for staff."""
    return check_performer_achievements(db, performer_id, performer_name, corps_id, role_type)


def check_corps_achievements(
    db: Session,
    corps_id: str,
    corps_name: str,
) -> list[CaptionAward]:
    """Check and award achievements for a corps."""
    return _award_for_scope(db, "corps", AwardRecipientType.CORPS, corps_id, corps_name, corps_id)
