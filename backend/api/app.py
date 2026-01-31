"""FastAPI application — DCI Layer API."""

import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import Base, create_db_engine, create_session_factory

logger = logging.getLogger(__name__)

# --- Database setup ---

engine = create_db_engine()
SessionFactory = create_session_factory(engine)


# --- WebSocket Connection Manager ---

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
        stale = []
        for ws in self.active_connections.get(corps_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        # Clean up stale connections
        for ws in stale:
            self.disconnect(ws, corps_id)


manager = ConnectionManager()

# Singleton references set during lifespan
_task_manager = None


def get_task_manager():
    return _task_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _task_manager
    Base.metadata.create_all(engine)

    # Initialize task manager with real LLM client and tool registry
    from backend.services.llm_client import AnthropicLLMClient
    from backend.tools import create_tool_registry
    from backend.services.tool_executor import ToolExecutor
    from backend.services.task_manager import TaskManager
    import os

    import shutil
    if shutil.which("claude"):
        from backend.services.llm_client import ClaudeCLIClient
        llm_client = ClaudeCLIClient()
        logger.info("Using Claude CLI client")
    elif shutil.which("chatgpt"):
        from backend.services.llm_client import ChatGPTCLIClient
        llm_client = ChatGPTCLIClient()
        logger.info("Using ChatGPT CLI client")
    elif os.environ.get("ANTHROPIC_API_KEY"):
        llm_client = AnthropicLLMClient()
        logger.info("Using Anthropic API client")
    elif os.environ.get("OPENAI_API_KEY"):
        from backend.services.llm_client import OpenAIClient
        llm_client = OpenAIClient()
        logger.info("Using OpenAI API client")
    else:
        from backend.services.llm_client import MockLLMClient
        llm_client = MockLLMClient()
        logger.warning("No LLM client available — using MockLLMClient")

    registry = create_tool_registry()
    tool_executor = ToolExecutor(registry)
    _task_manager = TaskManager(manager, llm_client, tool_executor)
    _task_manager.start_metronome()

    yield

    _task_manager.stop()


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

class ChatSend(BaseModel):
    content: str
    to_role: str = "executive_director"


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
async def api_activate_show(show_id: str, db: Session = Depends(get_db)):
    from backend.services.show_service import activate_show, ShowError
    try:
        show = activate_show(db, show_id)
    except ShowError as e:
        raise HTTPException(400, str(e))

    # Auto-generate work: queue ED to design the show structure
    tm = get_task_manager()
    if tm and show.corps_id and show.coordinate_root_id:
        # Find the ED session
        ed_session_id = tm.get_session_for_role(db, show.corps_id, "executive_director")
        if ed_session_id:
            tm.start_agent(
                session_id=ed_session_id,
                task_description=(
                    f"The show '{show.title}' has been activated. The root coordinate ID is {show.coordinate_root_id}. "
                    f"The corps ID is {show.corps_id}. "
                    f"Design the show structure: create MOVEMENT coordinates under the root coordinate, "
                    f"then hand off to the program_coordinator to break down further."
                ),
                corps_id=show.corps_id,
            )
            await manager.broadcast(show.corps_id, {
                "type": "message",
                "role": "system",
                "content": f"Show activated. Executive Director is designing the show structure...",
            })

    return {"id": show.id, "status": show.status.value, "corps_id": show.corps_id}


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
            "nickname": defn.nickname if defn else None,
            "model_tier": defn.model_tier.value if defn else "unknown",
            "status": s.status.value,
            "parent_session_id": s.parent_session_id,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
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


# --- Chat endpoints ---

@app.post("/api/corps/{corps_id}/chat")
async def api_send_chat(corps_id: str, data: ChatSend, db: Session = Depends(get_db)):
    """Send a user message to an agent role. Creates a message record and wakes the target agent."""
    from backend.models.message import MessageType, MessagePriority
    from backend.services.message_service import send_message

    # Record the message
    msg = send_message(
        db, corps_id=corps_id, from_role="user",
        to_role=data.to_role, type=MessageType.DIRECTIVE,
        subject=data.content[:100], body=data.content,
        priority=MessagePriority.NORMAL,
    )

    # Broadcast to WebSocket
    await manager.broadcast(corps_id, {
        "type": "chat",
        "from_role": "user",
        "to_role": data.to_role,
        "content": data.content,
        "message_id": msg.id,
    })

    # Wake target agent via task_manager
    tm = get_task_manager()
    if tm:
        session_id = tm.get_session_for_role(db, corps_id, data.to_role)
        if session_id and not tm.is_active(session_id):
            tm.start_agent(
                session_id=session_id,
                task_description=f"User message: {data.content}",
                corps_id=corps_id,
            )

    return {"id": msg.id, "status": "sent"}


@app.get("/api/corps/{corps_id}/chat")
def api_get_chat_history(corps_id: str, db: Session = Depends(get_db)):
    """Get chat history — all messages for a corps, ordered chronologically."""
    from backend.models.message import Message
    msgs = (
        db.query(Message)
        .filter(Message.corps_id == corps_id)
        .order_by(Message.created_at)
        .all()
    )
    return [{
        "id": m.id,
        "type": m.type.value,
        "from_role": m.from_role,
        "to_role": m.to_role,
        "subject": m.subject,
        "body": m.body,
        "priority": m.priority.value,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "acknowledged_at": m.acknowledged_at.isoformat() if m.acknowledged_at else None,
    } for m in msgs]


# --- Session Activity Log ---

@app.get("/api/sessions/{session_id}/activity")
def api_get_session_activity(session_id: str, db: Session = Depends(get_db)):
    """Get activity log for an agent session."""
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition
    from backend.models.message import Message

    session = db.get(AgentSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    defn = db.get(AgentDefinition, session.definition_id)

    # Get messages sent by or to this session
    messages = (
        db.query(Message)
        .filter(
            (Message.from_session_id == session_id) | (Message.to_session_id == session_id)
        )
        .order_by(Message.created_at)
        .all()
    )

    # Get context snapshot for tool call history
    snapshot = None
    if session.context_snapshot:
        try:
            snapshot = json.loads(session.context_snapshot)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "session_id": session_id,
        "role": defn.role if defn else "unknown",
        "status": session.status.value,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "tool_calls": snapshot.get("tool_calls", []) if snapshot else [],
        "final_response": snapshot.get("final_response", "") if snapshot else "",
        "iterations": snapshot.get("iterations", 0) if snapshot else 0,
        "messages": [{
            "id": m.id,
            "type": m.type.value,
            "from_role": m.from_role,
            "to_role": m.to_role,
            "subject": m.subject,
            "body": m.body,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in messages],
    }


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


# --- Work Log endpoint ---

@app.get("/api/work-log")
def api_get_global_work_log(limit: int = 100, event_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get work log across all corps."""
    from backend.models.work_log import WorkLog
    query = db.query(WorkLog)
    if event_type:
        query = query.filter(WorkLog.event_type == event_type)
    logs = query.order_by(WorkLog.timestamp.desc()).limit(limit).all()
    return [{
        "id": log.id,
        "session_id": log.session_id,
        "corps_id": log.corps_id,
        "role": log.role,
        "event_type": log.event_type,
        "phase": log.phase,
        "details": log.details,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    } for log in logs]


@app.get("/api/corps/{corps_id}/work-log")
def api_get_work_log(corps_id: str, limit: int = 100, event_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get structured work log for a corps."""
    from backend.models.work_log import WorkLog
    query = db.query(WorkLog).filter(WorkLog.corps_id == corps_id)
    if event_type:
        query = query.filter(WorkLog.event_type == event_type)
    logs = query.order_by(WorkLog.timestamp.desc()).limit(limit).all()
    return [{
        "id": log.id,
        "session_id": log.session_id,
        "role": log.role,
        "event_type": log.event_type,
        "phase": log.phase,
        "details": log.details,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    } for log in logs]


@app.get("/api/shows-overview")
def api_shows_overview(db: Session = Depends(get_db)):
    """Get all shows with summary stats for the dashboard."""
    from backend.models.show import Show
    from backend.models.corps import Corps
    from backend.models.agent_session import AgentSession
    from backend.models.rep import Rep, RepStatus
    from backend.models.coordinate import Coordinate

    shows = db.query(Show).order_by(Show.created_at.desc()).all()
    results = []
    for show in shows:
        stats = {"agents_active": 0, "reps_total": 0, "reps_completed": 0, "reps_failed": 0, "coordinates_total": 0}
        if show.corps_id:
            stats["agents_active"] = db.query(AgentSession).filter(
                AgentSession.corps_id == show.corps_id,
                AgentSession.status == "active",
            ).count()
            stats["reps_total"] = db.query(Rep).join(Coordinate).filter(
                Coordinate.id == Rep.coordinate_id,
            ).count() if show.coordinate_root_id else 0
            stats["reps_completed"] = db.query(Rep).join(Coordinate).filter(
                Rep.status == RepStatus.COMPLETED,
            ).count() if show.coordinate_root_id else 0
            stats["reps_failed"] = db.query(Rep).join(Coordinate).filter(
                Rep.status == RepStatus.FAILED,
            ).count() if show.coordinate_root_id else 0
        results.append({
            "id": show.id,
            "title": show.title,
            "description": show.description,
            "status": show.status.value,
            "corps_id": show.corps_id,
            "coordinate_root_id": show.coordinate_root_id,
            "created_at": show.created_at.isoformat() if show.created_at else None,
            **stats,
        })
    return results


@app.delete("/api/shows/{show_id}")
def api_delete_show(show_id: str, db: Session = Depends(get_db)):
    """Delete a show and optionally its corps."""
    from backend.models.show import Show
    show = db.get(Show, show_id)
    if not show:
        raise HTTPException(404, "Show not found")
    db.delete(show)
    db.commit()
    return {"deleted": show_id}


@app.get("/api/agents-overview")
def api_agents_overview(db: Session = Depends(get_db)):
    """Get all active agent sessions across all corps with their definitions."""
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    sessions = (
        db.query(AgentSession)
        .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
        .filter(AgentSession.status == SessionStatus.ACTIVE)
        .all()
    )
    results = []
    for s in sessions:
        defn = db.get(AgentDefinition, s.definition_id)
        results.append({
            "id": s.id,
            "role": defn.role if defn else "unknown",
            "nickname": defn.nickname if defn else None,
            "model_tier": defn.model_tier.value if defn else "unknown",
            "status": s.status.value,
            "corps_id": s.corps_id,
            "started_at": s.started_at.isoformat() if s.started_at else None,
        })
    return results


@app.get("/api/coordinates/{coord_id}/tree")
def api_get_coordinate_tree(coord_id: str, db: Session = Depends(get_db)):
    """Get full coordinate tree with reps for a given root."""
    from backend.services.coordinate_service import get_coordinate, get_children
    from backend.services.rep_service import get_reps_for_coordinate

    def _build(cid):
        coord = get_coordinate(db, cid)
        if not coord:
            return None
        reps = get_reps_for_coordinate(db, cid)
        children = get_children(db, cid)
        return {
            "id": coord.id,
            "type": coord.type.value,
            "title": coord.title,
            "description": coord.description,
            "status": coord.status.value,
            "caption": coord.caption,
            "reps": [{"id": r.id, "status": r.status.value, "result": r.result, "error": r.error, "assigned_to": r.assigned_to} for r in reps],
            "children": [_build(c.id) for c in children],
        }

    tree = _build(coord_id)
    if not tree:
        raise HTTPException(404, "Coordinate not found")
    return tree


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

@app.websocket("/ws/{corps_id}")
async def websocket_endpoint(websocket: WebSocket, corps_id: str):
    await manager.connect(websocket, corps_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "chat":
                    # Handle incoming chat via WebSocket
                    db = SessionFactory()
                    try:
                        from backend.models.message import MessageType, MessagePriority
                        from backend.services.message_service import send_message

                        to_role = msg.get("to_role", "executive_director")
                        content = msg.get("content", "")

                        record = send_message(
                            db, corps_id=corps_id, from_role="user",
                            to_role=to_role, type=MessageType.DIRECTIVE,
                            subject=content[:100], body=content,
                            priority=MessagePriority.NORMAL,
                        )

                        await manager.broadcast(corps_id, {
                            "type": "chat",
                            "from_role": "user",
                            "to_role": to_role,
                            "content": content,
                            "message_id": record.id,
                        })

                        # Wake agent
                        tm = get_task_manager()
                        if tm:
                            session_id = tm.get_session_for_role(db, corps_id, to_role)
                            if session_id and not tm.is_active(session_id):
                                tm.start_agent(
                                    session_id=session_id,
                                    task_description=f"User message: {content}",
                                    corps_id=corps_id,
                                )
                    finally:
                        db.close()
                else:
                    await websocket.send_json({"type": "ack", "data": data})
            except json.JSONDecodeError:
                await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, corps_id)
    except Exception:
        logger.exception("WebSocket error for corps %s", corps_id)
        manager.disconnect(websocket, corps_id)
