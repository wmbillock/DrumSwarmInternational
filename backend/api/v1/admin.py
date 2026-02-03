"""V1 API — Admin routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select, exists

from backend.api.v1.helpers import _get_db_session

router = APIRouter(prefix="/api/v1")


@router.post("/admin/cleanup")
def v1_admin_cleanup():
    """Clean up stale agent sessions and orphan corps."""
    from backend.models.corps import Corps, CorpsStatus
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.work_log import WorkLog

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        two_hours_ago = now - timedelta(hours=2)
        four_hours_ago = now - timedelta(hours=4)

        stale_sessions = db.query(AgentSession).filter(
            AgentSession.status == SessionStatus.ACTIVE,
            AgentSession.started_at < two_hours_ago,
            ~exists(
                select(WorkLog.id).where(
                    WorkLog.session_id == AgentSession.id,
                    WorkLog.timestamp > two_hours_ago
                ).correlate(AgentSession)
            )
        ).all()

        for s in stale_sessions:
            s.status = SessionStatus.TIMED_OUT
            s.ended_at = now

        orphan_corps = db.query(Corps).filter(
            Corps.status == CorpsStatus.INITIALIZING,
            Corps.founding_definition.is_(None),
            ~exists(
                select(AgentSession.id).where(
                    AgentSession.corps_id == Corps.id,
                    AgentSession.status == SessionStatus.ACTIVE
                ).correlate(Corps)
            ),
            ~exists(
                select(WorkLog.id).where(
                    WorkLog.corps_id == Corps.id,
                    WorkLog.timestamp > four_hours_ago
                ).correlate(Corps)
            )
        ).all()

        for c in orphan_corps:
            c.status = CorpsStatus.DISBANDED

        db.commit()
        return {
            "timed_out_sessions": len(stale_sessions),
            "disbanded_corps": len(orphan_corps),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Cleanup failed: {e}")
    finally:
        db.close()


@router.get("/admin/corps")
def v1_admin_list_corps():
    """Admin view of all corps with full DB details."""
    from backend.models.corps import Corps
    db = _get_db_session()
    try:
        corps_list = db.query(Corps).all()
        return [{
            "id": c.id,
            "name": c.name,
            "status": c.status.value if c.status else None,
            "mode": c.mode.value if c.mode else None,
            "theme_id": c.theme_id,
            "mascot": c.mascot,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        } for c in corps_list]
    finally:
        db.close()


@router.get("/admin/admin-corps")
def v1_get_admin_corps():
    """Get the admin/bar corps with its roster."""
    from backend.models.corps import Corps
    from backend.models.agent_definition import AgentDefinition
    db = _get_db_session()
    try:
        admin = db.query(Corps).filter(Corps.id == "the-bar").first()
        if not admin:
            admin = db.query(Corps).first()
        if not admin:
            raise HTTPException(404, "No admin corps found")
        agents = db.query(AgentDefinition).filter(
            AgentDefinition.corps_id == admin.id
        ).all()
        return {
            "id": admin.id,
            "name": admin.name,
            "status": admin.status.value if admin.status else None,
            "mode": admin.mode.value if admin.mode else None,
            "roster": [{
                "id": a.id,
                "role": a.role,
                "name": a.nickname or a.role,
            } for a in agents],
        }
    finally:
        db.close()


@router.get("/admin/llm-batch")
def v1_admin_llm_batch_status():
    """Expose LLM batch queue and job metrics."""
    try:
        from backend.api.app import get_task_manager
        tm = get_task_manager()
        llm_client = tm.llm_client if tm else None
        if not llm_client or not hasattr(llm_client, "get_batch_status"):
            return {"status": "unavailable"}
        return llm_client.get_batch_status()
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch batch status: {e}")
