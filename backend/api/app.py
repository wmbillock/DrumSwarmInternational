"""FastAPI application — DCI Layer API."""

import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import Base, create_db_engine, create_session_factory


# --- Database setup ---

engine = create_db_engine()
SessionFactory = create_session_factory(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


def get_db():
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()


# --- App ---

app = FastAPI(title="DCI Swarm", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Schemas ---

class ShowCreate(BaseModel):
    title: str
    description: Optional[str] = None

class ShowUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class TourToggle(BaseModel):
    enable: bool

class RehearsalModeSet(BaseModel):
    mode: str  # basics, sectionals, full_ensemble, run_through

class CoordinateCreate(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    caption: Optional[str] = None

class RepCreate(BaseModel):
    coordinate_id: str

class RepTransition(BaseModel):
    new_status: str
    assigned_to: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None

class ScoreCreate(BaseModel):
    judge_type: str
    value: float
    box: int
    rep_id: Optional[str] = None
    coordinate_id: Optional[str] = None
    feedback: Optional[str] = None

class MessageCreate(BaseModel):
    from_role: str
    type: str
    subject: str
    body: Optional[str] = None
    to_role: Optional[str] = None
    priority: str = "normal"
    coordinate_id: Optional[str] = None


# --- Show endpoints ---

@app.post("/api/shows")
def api_create_show(data: ShowCreate, db: Session = Depends(get_db)):
    from backend.services.show_service import create_show
    show = create_show(db, title=data.title, description=data.description)
    return {"id": show.id, "title": show.title, "status": show.status.value}


@app.get("/api/shows")
def api_list_shows(db: Session = Depends(get_db)):
    from backend.services.show_service import list_shows
    shows = list_shows(db)
    return [{"id": s.id, "title": s.title, "status": s.status.value,
             "corps_id": s.corps_id} for s in shows]


@app.get("/api/shows/{show_id}")
def api_get_show(show_id: str, db: Session = Depends(get_db)):
    from backend.services.show_service import get_show
    show = get_show(db, show_id)
    if not show:
        raise HTTPException(404, "Show not found")
    return {"id": show.id, "title": show.title, "status": show.status.value,
            "corps_id": show.corps_id, "coordinate_root_id": show.coordinate_root_id,
            "description": show.description}


@app.post("/api/shows/{show_id}/activate")
def api_activate_show(show_id: str, db: Session = Depends(get_db)):
    from backend.services.show_service import activate_show, ShowError
    try:
        show = activate_show(db, show_id)
        return {"id": show.id, "status": show.status.value, "corps_id": show.corps_id}
    except ShowError as e:
        raise HTTPException(400, str(e))


@app.post("/api/shows/{show_id}/complete")
def api_complete_show(show_id: str, db: Session = Depends(get_db)):
    from backend.services.show_service import complete_show
    show = complete_show(db, show_id)
    return {"id": show.id, "status": show.status.value}


@app.post("/api/shows/{show_id}/tour")
def api_toggle_tour(show_id: str, data: TourToggle, db: Session = Depends(get_db)):
    from backend.services.show_service import toggle_tour, ShowError
    try:
        show = toggle_tour(db, show_id, data.enable)
        return {"id": show.id, "tour_mode": data.enable}
    except ShowError as e:
        raise HTTPException(400, str(e))


# --- Corps endpoints ---

@app.get("/api/corps/{corps_id}")
def api_get_corps(corps_id: str, db: Session = Depends(get_db)):
    from backend.models.corps import Corps
    corps = db.get(Corps, corps_id)
    if not corps:
        raise HTTPException(404, "Corps not found")
    return {"id": corps.id, "name": corps.name, "status": corps.status.value,
            "tour_mode": corps.tour_mode,
            "rehearsal_mode": corps.rehearsal_mode.value if corps.rehearsal_mode else None}


@app.post("/api/corps/{corps_id}/rehearsal-mode")
def api_set_rehearsal_mode(corps_id: str, data: RehearsalModeSet, db: Session = Depends(get_db)):
    from backend.models.corps import RehearsalMode
    from backend.services.corps_service import set_rehearsal_mode, CorpsError
    try:
        mode = RehearsalMode(data.mode)
        corps = set_rehearsal_mode(db, corps_id, mode)
        return {"id": corps.id, "rehearsal_mode": corps.rehearsal_mode.value}
    except (ValueError, CorpsError) as e:
        raise HTTPException(400, str(e))


# --- Roster (agent sessions) ---

@app.get("/api/corps/{corps_id}/roster")
def api_get_roster(corps_id: str, db: Session = Depends(get_db)):
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition
    sessions = (
        db.query(AgentSession)
        .filter(AgentSession.corps_id == corps_id)
        .all()
    )
    result = []
    for s in sessions:
        defn = db.get(AgentDefinition, s.definition_id)
        result.append({
            "id": s.id,
            "role": defn.role if defn else "unknown",
            "status": s.status.value,
            "parent_session_id": s.parent_session_id,
            "started_at": s.started_at.isoformat() if s.started_at else None,
        })
    return result


# --- Coordinate endpoints ---

@app.post("/api/coordinates")
def api_create_coordinate(data: CoordinateCreate, db: Session = Depends(get_db)):
    from backend.models.coordinate import CoordinateType
    from backend.services.coordinate_service import create_coordinate, InvalidCoordinateStructure
    try:
        coord = create_coordinate(
            db, type=CoordinateType(data.type), title=data.title,
            description=data.description, parent_id=data.parent_id, caption=data.caption,
        )
        return {"id": coord.id, "type": coord.type.value, "title": coord.title,
                "status": coord.status.value}
    except (ValueError, InvalidCoordinateStructure) as e:
        raise HTTPException(400, str(e))


@app.get("/api/coordinates/{coord_id}")
def api_get_coordinate(coord_id: str, db: Session = Depends(get_db)):
    from backend.services.coordinate_service import get_coordinate
    coord = get_coordinate(db, coord_id)
    if not coord:
        raise HTTPException(404, "Coordinate not found")
    return {"id": coord.id, "type": coord.type.value, "title": coord.title,
            "status": coord.status.value, "parent_id": coord.parent_id,
            "caption": coord.caption, "description": coord.description}


@app.get("/api/coordinates/{coord_id}/children")
def api_get_coordinate_children(coord_id: str, db: Session = Depends(get_db)):
    from backend.services.coordinate_service import get_children
    children = get_children(db, coord_id)
    return [{"id": c.id, "type": c.type.value, "title": c.title,
             "status": c.status.value} for c in children]


# --- Rep endpoints ---

@app.post("/api/reps")
def api_create_rep(data: RepCreate, db: Session = Depends(get_db)):
    from backend.services.rep_service import create_rep
    rep = create_rep(db, coordinate_id=data.coordinate_id)
    return {"id": rep.id, "status": rep.status.value, "coordinate_id": rep.coordinate_id}


@app.post("/api/reps/{rep_id}/transition")
def api_transition_rep(rep_id: str, data: RepTransition, db: Session = Depends(get_db)):
    from backend.models.rep import RepStatus
    from backend.services.rep_service import transition_rep, InvalidRepTransition
    try:
        rep = transition_rep(
            db, rep_id=rep_id, new_status=RepStatus(data.new_status),
            assigned_to=data.assigned_to, result=data.result, error=data.error,
        )
        return {"id": rep.id, "status": rep.status.value}
    except (ValueError, InvalidRepTransition) as e:
        raise HTTPException(400, str(e))


@app.get("/api/coordinates/{coord_id}/reps")
def api_get_reps_for_coordinate(coord_id: str, db: Session = Depends(get_db)):
    from backend.services.rep_service import get_reps_for_coordinate
    reps = get_reps_for_coordinate(db, coord_id)
    return [{"id": r.id, "status": r.status.value, "assigned_to": r.assigned_to,
             "result": r.result, "error": r.error} for r in reps]


# --- Score endpoints ---

@app.post("/api/scores")
def api_create_score(data: ScoreCreate, db: Session = Depends(get_db)):
    from backend.models.score import JudgeType
    from backend.services.scoring_service import record_score, InvalidScore
    try:
        score = record_score(
            db, corps_id="default", judge_type=JudgeType(data.judge_type),
            value=data.value, box=data.box, rep_id=data.rep_id,
            coordinate_id=data.coordinate_id, feedback=data.feedback,
        )
        return {"id": score.id, "value": score.value, "box": score.box}
    except (ValueError, InvalidScore) as e:
        raise HTTPException(400, str(e))


@app.get("/api/reps/{rep_id}/scores")
def api_get_scores_for_rep(rep_id: str, db: Session = Depends(get_db)):
    from backend.services.scoring_service import get_scores_for_rep
    scores = get_scores_for_rep(db, rep_id)
    return [{"id": s.id, "judge_type": s.judge_type.value, "value": s.value,
             "box": s.box, "feedback": s.feedback} for s in scores]


@app.get("/api/reps/{rep_id}/composite")
def api_get_composite(rep_id: str, db: Session = Depends(get_db)):
    from backend.services.scoring_service import compute_composite
    result = compute_composite(db, corps_id="default", rep_id=rep_id)
    return {
        "raw_total": result.raw_total,
        "penalties_total": result.penalties_total,
        "final_score": result.final_score,
        "needs_rework": result.needs_rework,
        "needs_escalation": result.needs_escalation,
    }


# --- Message endpoints ---

@app.post("/api/corps/{corps_id}/messages")
def api_send_message(corps_id: str, data: MessageCreate, db: Session = Depends(get_db)):
    from backend.models.message import MessageType, MessagePriority
    from backend.services.message_service import send_message, InvalidMessagePath, InvalidMessageType
    try:
        msg = send_message(
            db, corps_id=corps_id, from_role=data.from_role,
            type=MessageType(data.type), subject=data.subject, body=data.body,
            to_role=data.to_role, priority=MessagePriority(data.priority),
            coordinate_id=data.coordinate_id,
        )
        return {"id": msg.id, "type": msg.type.value, "subject": msg.subject}
    except (ValueError, InvalidMessagePath, InvalidMessageType) as e:
        raise HTTPException(400, str(e))


@app.get("/api/corps/{corps_id}/messages")
def api_poll_messages(corps_id: str, role: Optional[str] = None, db: Session = Depends(get_db)):
    from backend.services.message_service import poll_messages
    msgs = poll_messages(db, corps_id=corps_id, role=role)
    return [{"id": m.id, "type": m.type.value, "from_role": m.from_role,
             "to_role": m.to_role, "subject": m.subject, "priority": m.priority.value,
             "acknowledged_at": m.acknowledged_at.isoformat() if m.acknowledged_at else None
             } for m in msgs]


# --- Improvement endpoints ---

@app.post("/api/corps/{corps_id}/basics/{caption}")
def api_run_basics(corps_id: str, caption: str, db: Session = Depends(get_db)):
    from backend.services.improvement import run_basics
    result = run_basics(db, corps_id, caption)
    return {
        "caption": result.caption,
        "definitions_reviewed": result.definitions_reviewed,
        "improvements_suggested": result.improvements_suggested,
        "suggestions": result.suggestions,
    }


@app.get("/api/reps/{rep_id}/critique")
def api_run_critique(rep_id: str, corps_id: str = "default", db: Session = Depends(get_db)):
    from backend.services.improvement import run_critique
    result = run_critique(db, rep_id, corps_id)
    return {
        "rep_id": result.rep_id,
        "overall_assessment": result.overall_assessment,
        "needs_rework": result.needs_rework,
        "feedbacks": [
            {"judge_type": f.judge_type.value, "score": f.score_value,
             "strengths": f.strengths, "weaknesses": f.weaknesses,
             "action_items": f.action_items}
            for f in result.feedbacks
        ],
    }


@app.get("/api/corps/{corps_id}/banquet")
def api_run_banquet(corps_id: str, db: Session = Depends(get_db)):
    from backend.services.improvement import run_banquet
    report = run_banquet(db, corps_id)
    return {
        "corps_id": report.corps_id,
        "total_reps": report.total_reps,
        "completed_reps": report.completed_reps,
        "failed_reps": report.failed_reps,
        "average_score": report.average_score,
        "top_caption": report.top_caption,
        "what_worked": report.what_worked,
        "what_failed": report.what_failed,
        "improvements": report.improvements,
    }


# --- Metronome endpoint ---

@app.post("/api/corps/{corps_id}/metronome/tick")
def api_metronome_tick(corps_id: str, db: Session = Depends(get_db)):
    from backend.tools.metronome import tick
    result = tick(db, corps_id)
    return {
        "checked": result.checked,
        "reclaimed": result.reclaimed,
        "reclaimed_rep_ids": result.reclaimed_rep_ids,
    }


# --- Merge monitor endpoint ---

@app.post("/api/corps/{corps_id}/merge-check")
def api_merge_check(corps_id: str, db: Session = Depends(get_db)):
    from backend.services.corps_service import merge_monitor_check
    result = merge_monitor_check(db, corps_id)
    return {
        "checked": result.checked,
        "merged": result.merged,
        "conflicts": result.conflicts,
        "merged_coordinate_ids": result.merged_coordinate_ids,
        "conflict_coordinate_ids": result.conflict_coordinate_ids,
    }


# --- WebSocket for real-time updates ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, corps_id: str):
        await websocket.accept()
        self.active_connections.setdefault(corps_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, corps_id: str):
        conns = self.active_connections.get(corps_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast(self, corps_id: str, message: dict):
        for ws in self.active_connections.get(corps_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws/{corps_id}")
async def websocket_endpoint(websocket: WebSocket, corps_id: str):
    await manager.connect(websocket, corps_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now; in production, handle commands
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, corps_id)
