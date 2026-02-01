"""Legacy show endpoints extracted from app.py."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.app import get_db, get_task_manager, manager

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Schemas ---

class ShowCreate(BaseModel):
    title: str
    description: Optional[str] = None

class ShowUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class TourToggle(BaseModel):
    enable: bool

class CreateFromTemplateRequest(BaseModel):
    template: str
    title: Optional[str] = None
    params: Optional[dict] = None


# --- Show endpoints ---

@router.post("/api/shows")
def api_create_show(data: ShowCreate, db: Session = Depends(get_db)):
    from backend.services.show_service import create_show
    show = create_show(db, title=data.title, description=data.description)
    return {"id": show.id, "title": show.title, "status": show.status.value}


@router.get("/api/shows")
def api_list_shows(db: Session = Depends(get_db)):
    from backend.services.show_service import list_shows
    shows = list_shows(db)
    return [{"id": s.id, "title": s.title, "status": s.status.value,
             "corps_id": s.corps_id} for s in shows]


@router.get("/api/shows/{show_id}")
def api_get_show(show_id: str, db: Session = Depends(get_db)):
    from backend.services.show_service import get_show
    show = get_show(db, show_id)
    if not show:
        raise HTTPException(404, "Show not found")
    return {"id": show.id, "title": show.title, "status": show.status.value,
            "corps_id": show.corps_id, "segment_root_id": show.segment_root_id,
            "description": show.description}


@router.post("/api/shows/{show_id}/activate")
async def api_activate_show(show_id: str, db: Session = Depends(get_db)):
    from backend.services.show_service import activate_show, ShowError
    try:
        show = activate_show(db, show_id)
    except ShowError as e:
        raise HTTPException(400, str(e))

    # Auto-generate work: queue ED to design the show structure
    tm = get_task_manager()
    if tm and show.corps_id and show.segment_root_id:
        # Find the ED session
        ed_session_id = tm.get_session_for_role(db, show.corps_id, "executive_director")
        if ed_session_id:
            tm.start_agent(
                session_id=ed_session_id,
                task_description=(
                    f"The show '{show.title}' has been activated. The root segment ID is {show.segment_root_id}. "
                    f"The corps ID is {show.corps_id}. "
                    f"You are in Winter Camps, BASICS mode. "
                    f"Design the show structure: create MOVEMENT segments under the root segment, "
                    f"then hand off to the program_coordinator to break down further."
                ),
                corps_id=show.corps_id,
            )
            await manager.broadcast(show.corps_id, {
                "type": "message",
                "role": "system",
                "content": "Show activated. Winter Camps — ED is designing the show structure...",
            })

    return {"id": show.id, "status": show.status.value, "corps_id": show.corps_id}


@router.post("/api/shows/{show_id}/complete")
def api_complete_show(show_id: str, db: Session = Depends(get_db)):
    from backend.services.show_service import complete_show
    show = complete_show(db, show_id)
    return {"id": show.id, "status": show.status.value}


@router.post("/api/shows/{show_id}/tour")
def api_toggle_tour(show_id: str, data: TourToggle, db: Session = Depends(get_db)):
    from backend.services.show_service import toggle_tour, ShowError
    try:
        show = toggle_tour(db, show_id, data.enable)
        return {"id": show.id, "status": show.status.value}
    except ShowError as e:
        raise HTTPException(400, str(e))


@router.delete("/api/shows/{show_id}")
def api_delete_show(show_id: str, db: Session = Depends(get_db)):
    """Delete a show and optionally its corps."""
    from backend.models.show import Show
    show = db.get(Show, show_id)
    if not show:
        raise HTTPException(404, "Show not found")
    db.delete(show)
    db.commit()
    return {"deleted": show_id}


@router.get("/api/shows-overview")
def api_shows_overview(db: Session = Depends(get_db)):
    """Get all shows with summary stats for the dashboard."""
    from backend.models.show import Show
    from backend.models.corps import Corps
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.rep import Rep, RepStatus
    from backend.models.segment import Segment

    shows = db.query(Show).order_by(Show.created_at.desc()).all()
    results = []
    for show in shows:
        stats = {"agents_active": 0, "reps_total": 0, "reps_completed": 0, "reps_failed": 0, "segments_total": 0}
        if show.corps_id:
            stats["agents_active"] = db.query(AgentSession).filter(
                AgentSession.corps_id == show.corps_id,
                AgentSession.status == SessionStatus.ACTIVE,
            ).count()
            stats["reps_total"] = db.query(Rep).join(Segment).filter(
                Segment.id == Rep.segment_id,
            ).count() if show.segment_root_id else 0
            stats["reps_completed"] = db.query(Rep).join(Segment).filter(
                Rep.status == RepStatus.COMPLETED,
            ).count() if show.segment_root_id else 0
            stats["reps_failed"] = db.query(Rep).join(Segment).filter(
                Rep.status == RepStatus.FAILED,
            ).count() if show.segment_root_id else 0
        corps_name = None
        final_score = None
        if show.corps_id:
            corps = db.get(Corps, show.corps_id)
            if corps:
                corps_name = corps.name
            # Quick composite score
            from backend.models.score import Score
            score_count = db.query(Score).filter(Score.corps_id == show.corps_id).count()
            if score_count > 0:
                from sqlalchemy import func as sqlfunc
                avg = db.query(sqlfunc.avg(Score.value)).filter(Score.corps_id == show.corps_id).scalar()
                final_score = round(float(avg), 1) if avg else None
        results.append({
            "id": show.id,
            "title": show.title,
            "description": show.description,
            "status": show.status.value,
            "corps_id": show.corps_id,
            "corps_name": corps_name,
            "final_score": final_score,
            "segment_root_id": show.segment_root_id,
            "created_at": show.created_at.isoformat() if show.created_at else None,
            **stats,
        })
    return results


# --- Show Templates ---

@router.get("/api/show-templates")
def api_list_templates():
    """List available show templates."""
    from backend.services.show_templates import list_templates
    return {"templates": list_templates()}


@router.get("/api/show-templates/{name}")
def api_get_template(name: str):
    """Get a show template definition."""
    from backend.services.show_templates import load_template
    try:
        return load_template(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Template '{name}' not found")


@router.post("/api/show-templates/instantiate")
def api_instantiate_template(req: CreateFromTemplateRequest, db: Session = Depends(get_db)):
    """Create a show from a template."""
    from backend.services.show_templates import create_show_from_template
    try:
        return create_show_from_template(db, req.template, title=req.title, params=req.params)
    except FileNotFoundError:
        raise HTTPException(404, f"Template '{req.template}' not found")
