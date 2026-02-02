"""V1 API — Critique session routes."""

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_db_session
from backend.api.v1.schemas import CritiqueMessageRequest

router = APIRouter(prefix="/api/v1")


@router.get("/critique/{session_id}")
def v1_get_critique(session_id: str):
    """Get critique session conversation."""
    from backend.models.critique_session import CritiqueSession
    db = _get_db_session()
    try:
        session = db.get(CritiqueSession, session_id)
        if not session:
            raise HTTPException(404, "Critique session not found")
        return {
            "id": session.id,
            "competition_id": session.competition_id,
            "corps_id": session.corps_id,
            "judge_type": session.judge_type,
            "staff_role": session.staff_role,
            "status": session.status.value,
            "conversation": session.conversation,
            "action_items": session.action_items,
            "created_at": str(session.created_at),
            "is_automated": getattr(session, "is_automated", False),
        }
    finally:
        db.close()


@router.post("/critique/{session_id}/message")
def v1_send_critique_message(session_id: str, req: CritiqueMessageRequest):
    """Send a message in a critique session."""
    from backend.services.critique_service import send_message
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    db = _get_db_session()
    try:
        session = send_message(db, session_id, req.message, llm_client)
        return {
            "id": session.id,
            "competition_id": session.competition_id,
            "corps_id": session.corps_id,
            "judge_type": session.judge_type,
            "staff_role": session.staff_role,
            "status": session.status.value,
            "conversation": session.conversation,
            "action_items": session.action_items,
            "created_at": str(session.created_at),
            "is_automated": getattr(session, "is_automated", False),
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.post("/critique/{session_id}/complete")
def v1_complete_critique(session_id: str):
    """Complete a critique session — extract action items."""
    from backend.services.critique_service import complete_critique
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    db = _get_db_session()
    try:
        session = complete_critique(db, session_id, llm_client)
        return {
            "id": session.id,
            "competition_id": session.competition_id,
            "corps_id": session.corps_id,
            "judge_type": session.judge_type,
            "staff_role": session.staff_role,
            "status": session.status.value,
            "conversation": session.conversation,
            "action_items": session.action_items,
            "created_at": str(session.created_at),
            "completed_at": str(session.completed_at) if session.completed_at else None,
            "is_automated": getattr(session, "is_automated", False),
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()
