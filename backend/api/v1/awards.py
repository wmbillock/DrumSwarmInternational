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
