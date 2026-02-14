"""V1 API — Caption Awards/Achievements routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _validate_id, _get_db_session

router = APIRouter(prefix="/api/v1")


@router.get("/awards")
def list_awards(
    recipient_id: Optional[str] = None,
    corps_id: Optional[str] = None,
    category: Optional[str] = None,
    recipient_type: Optional[str] = None,
):
    """List caption awards with optional filters."""
    from backend.models.caption_award import CaptionAward, AwardCategory, AwardRecipientType

    db = _get_db_session()
    try:
        q = db.query(CaptionAward)
        if recipient_id:
            q = q.filter(CaptionAward.recipient_id == recipient_id)
        if corps_id:
            q = q.filter(CaptionAward.corps_id == corps_id)
        if category:
            try:
                q = q.filter(CaptionAward.category == AwardCategory(category))
            except ValueError:
                raise HTTPException(400, f"Invalid category: {category}")
        if recipient_type:
            try:
                q = q.filter(CaptionAward.recipient_type == AwardRecipientType(recipient_type))
            except ValueError:
                raise HTTPException(400, f"Invalid recipient_type: {recipient_type}")
        awards = q.order_by(CaptionAward.awarded_at.desc()).limit(100).all()
        return [{
            "id": a.id,
            "category": a.category.value,
            "tier": a.tier.value,
            "name": a.name,
            "description": a.description,
            "recipient_type": a.recipient_type.value,
            "recipient_id": a.recipient_id,
            "recipient_name": a.recipient_name,
            "corps_id": a.corps_id,
            "milestone_value": a.milestone_value,
            "awarded_at": a.awarded_at.isoformat() if a.awarded_at else None,
        } for a in awards]
    finally:
        db.close()


@router.get("/awards/summary")
def awards_summary(corps_id: Optional[str] = None):
    """Aggregated awards summary: by category, by tier, recent unlocks, top recipients."""
    from backend.models.caption_award import CaptionAward, AwardCategory, AwardTier
    from sqlalchemy import func as sa_func

    TIER_ORDER = {t.value: i for i, t in enumerate(AwardTier)}

    db = _get_db_session()
    try:
        q = db.query(CaptionAward)
        if corps_id:
            q = q.filter(CaptionAward.corps_id == corps_id)
        awards = q.all()

        total_awards = len(awards)

        # by_category
        by_category: dict = {}
        for cat in AwardCategory:
            cat_awards = [a for a in awards if a.category == cat]
            tiers: dict = {}
            for a in cat_awards:
                tiers[a.tier.value] = tiers.get(a.tier.value, 0) + 1
            highest_tier = None
            if tiers:
                highest_tier = max(tiers.keys(), key=lambda t: TIER_ORDER.get(t, 0))
            by_category[cat.value] = {
                "total": len(cat_awards),
                "tiers": tiers,
                "highest_tier": highest_tier,
            }

        # by_tier
        by_tier: dict = {}
        for a in awards:
            by_tier[a.tier.value] = by_tier.get(a.tier.value, 0) + 1

        # recent_unlocks (last 20)
        sorted_awards = sorted(awards, key=lambda a: a.awarded_at or "", reverse=True)
        recent_unlocks = [{
            "name": a.name,
            "category": a.category.value,
            "tier": a.tier.value,
            "recipient_name": a.recipient_name,
            "awarded_at": a.awarded_at.isoformat() if a.awarded_at else None,
        } for a in sorted_awards[:20]]

        # top_recipients
        recipient_counts: dict = {}
        for a in awards:
            recipient_counts[a.recipient_name] = recipient_counts.get(a.recipient_name, 0) + 1
        top_recipients = sorted(
            [{"name": name, "count": count} for name, count in recipient_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        return {
            "total_awards": total_awards,
            "by_category": by_category,
            "by_tier": by_tier,
            "recent_unlocks": recent_unlocks,
            "top_recipients": top_recipients,
        }
    finally:
        db.close()


@router.post("/awards/check/{corps_id}")
def check_awards(corps_id: str):
    """Manually trigger achievement check for all performers in a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.models.agent_session import AgentSession
    from backend.models.performer import Performer
    from backend.services.achievement_detector import check_performer_achievements, check_corps_achievements
    from backend.models.corps import Corps

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if corps:
            check_corps_achievements(db, corps.id, corps.name)

        sessions = db.query(AgentSession).filter(
            AgentSession.corps_id == corps_id,
            AgentSession.performer_id.isnot(None),
        ).all()
        total_awarded = 0
        for s in sessions:
            performer = db.get(Performer, s.performer_id)
            if performer:
                awards = check_performer_achievements(
                    db,
                    performer.id,
                    performer.name,
                    corps_id,
                    role_type=performer.role_type,
                )
                total_awarded += len(awards)
        return {"checked": len(sessions), "awards_granted": total_awarded}
    finally:
        db.close()
