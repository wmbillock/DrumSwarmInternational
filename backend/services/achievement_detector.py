"""Achievement detector — monitors activity milestones and awards caption awards.

Checks after key transitions (rep completion, session completion, contest scoring)
and awards achievements when thresholds are met.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.caption_award import (
    AwardCategory, AwardTier, AwardRecipientType, CaptionAward,
)

logger = logging.getLogger(__name__)


# Milestone definitions: (category, tier, threshold, name, description)
MILESTONES = [
    # Endurance — cumulative completed reps
    (AwardCategory.ENDURANCE, AwardTier.BRONZE, 10, "First Steps", "Completed 10 reps"),
    (AwardCategory.ENDURANCE, AwardTier.SILVER, 50, "Marathon Runner", "Completed 50 reps"),
    (AwardCategory.ENDURANCE, AwardTier.GOLD, 100, "Iron Will", "Completed 100 reps"),
    (AwardCategory.ENDURANCE, AwardTier.PLATINUM, 500, "Unstoppable Force", "Completed 500 reps"),
    (AwardCategory.ENDURANCE, AwardTier.DIAMOND, 1000, "Legend of the Field", "Completed 1000 reps"),

    # Velocity — reps completed in a single session
    (AwardCategory.VELOCITY, AwardTier.BRONZE, 3, "Quick Draw", "Completed 3 reps in one session"),
    (AwardCategory.VELOCITY, AwardTier.SILVER, 5, "Speed Demon", "Completed 5 reps in one session"),
    (AwardCategory.VELOCITY, AwardTier.GOLD, 10, "Blur", "Completed 10 reps in one session"),

    # Reliability — consecutive successes without failure
    (AwardCategory.RELIABILITY, AwardTier.BRONZE, 10, "Steady Hand", "10 consecutive successes"),
    (AwardCategory.RELIABILITY, AwardTier.SILVER, 25, "Rock Solid", "25 consecutive successes"),
    (AwardCategory.RELIABILITY, AwardTier.GOLD, 50, "Flawless", "50 consecutive successes"),
    (AwardCategory.RELIABILITY, AwardTier.PLATINUM, 100, "Perfectionist", "100 consecutive successes"),

    # Collaboration — handoff messages sent
    (AwardCategory.COLLABORATION, AwardTier.BRONZE, 5, "Team Player", "Sent 5 handoff messages"),
    (AwardCategory.COLLABORATION, AwardTier.SILVER, 20, "Bridge Builder", "Sent 20 handoff messages"),
    (AwardCategory.COLLABORATION, AwardTier.GOLD, 50, "Master Coordinator", "Sent 50 handoff messages"),

    # Comeback — recovered from failed state
    (AwardCategory.COMEBACK, AwardTier.BRONZE, 1, "Bounce Back", "Recovered from first failure"),
    (AwardCategory.COMEBACK, AwardTier.SILVER, 5, "Resilient", "Recovered from 5 failures"),
    (AwardCategory.COMEBACK, AwardTier.GOLD, 10, "Phoenix", "Recovered from 10 failures"),

    # Caption-specific awards for corps
    (AwardCategory.BRASS_EXCELLENCE, AwardTier.GOLD, 85, "Fanfare Master", "Brass score above 85"),
    (AwardCategory.PERCUSSION_MASTERY, AwardTier.GOLD, 85, "Rhythm King", "Percussion score above 85"),
    (AwardCategory.GUARD_ARTISTRY, AwardTier.GOLD, 85, "Silk Spinner", "Guard score above 85"),
    (AwardCategory.VISUAL_INNOVATION, AwardTier.GOLD, 85, "Field Painter", "Visual score above 85"),
    (AwardCategory.GENERAL_EFFECT, AwardTier.GOLD, 85, "Showstopper", "GE score above 85"),

    # Creativity — unique segment types created
    (AwardCategory.CREATIVITY, AwardTier.BRONZE, 5, "Tinkerer", "Created 5 unique segment types"),
    (AwardCategory.CREATIVITY, AwardTier.SILVER, 15, "Innovator", "Created 15 unique segment types"),
]


def _already_awarded(db: Session, recipient_id: str, category: AwardCategory, tier: AwardTier) -> bool:
    """Check if this exact award has already been given."""
    return db.query(CaptionAward).filter(
        CaptionAward.recipient_id == recipient_id,
        CaptionAward.category == category,
        CaptionAward.tier == tier,
    ).count() > 0


def check_performer_achievements(
    db: Session,
    performer_id: str,
    performer_name: str,
    corps_id: Optional[str] = None,
) -> list[CaptionAward]:
    """Check and award achievements for a performer based on current stats."""
    from backend.models.performer import Performer
    from backend.models.agent_session import AgentSession, SessionStatus

    performer = db.get(Performer, performer_id)
    if not performer:
        return []

    awarded = []
    total = performer.total_sessions
    successes = performer.successful_sessions
    failures = performer.failed_sessions

    for category, tier, threshold, name, description in MILESTONES:
        if _already_awarded(db, performer_id, category, tier):
            continue

        hit = False
        if category == AwardCategory.ENDURANCE and total >= threshold:
            hit = True
        elif category == AwardCategory.RELIABILITY and successes >= threshold:
            # Check consecutive (simplified: use success ratio as proxy)
            if failures == 0 or (successes / max(total, 1)) > 0.9:
                hit = True
        elif category == AwardCategory.COMEBACK and failures >= threshold and successes > failures:
            hit = True

        if hit:
            award = CaptionAward(
                category=category,
                tier=tier,
                name=name,
                description=description,
                recipient_type=AwardRecipientType.PERFORMER,
                recipient_id=performer_id,
                recipient_name=performer_name,
                corps_id=corps_id,
                milestone_value=threshold,
            )
            db.add(award)
            awarded.append(award)
            logger.info("Achievement unlocked: %s -> %s (%s)", performer_name, name, tier.value)

    if awarded:
        db.commit()
    return awarded


def check_corps_achievements(
    db: Session,
    corps_id: str,
    corps_name: str,
    caption_scores: Optional[dict] = None,
) -> list[CaptionAward]:
    """Check and award achievements for a corps."""
    from backend.models.score import JudgeType

    awarded = []

    if caption_scores:
        score_category_map = {
            JudgeType.BRASS: AwardCategory.BRASS_EXCELLENCE,
            JudgeType.PERCUSSION: AwardCategory.PERCUSSION_MASTERY,
            JudgeType.GUARD: AwardCategory.GUARD_ARTISTRY,
            JudgeType.VISUAL: AwardCategory.VISUAL_INNOVATION,
            JudgeType.GENERAL_EFFECT: AwardCategory.GENERAL_EFFECT,
        }
        for jtype, score in caption_scores.items():
            category = score_category_map.get(jtype)
            if not category:
                continue
            for _, tier, threshold, name, description in MILESTONES:
                if tier != AwardTier.GOLD:
                    continue
                if _already_awarded(db, corps_id, category, tier):
                    continue
                if category in score_category_map.values() and score >= threshold:
                    award = CaptionAward(
                        category=category,
                        tier=tier,
                        name=name,
                        description=description,
                        recipient_type=AwardRecipientType.CORPS,
                        recipient_id=corps_id,
                        recipient_name=corps_name,
                        milestone_value=score,
                    )
                    db.add(award)
                    awarded.append(award)
                    logger.info("Corps achievement: %s -> %s", corps_name, name)

    if awarded:
        db.commit()
    return awarded
