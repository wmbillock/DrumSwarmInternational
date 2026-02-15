"""FastAPI application — DCI Layer API."""

import json
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import Base, create_db_engine, create_session_factory
from backend.services.db_pool import get_db_pool

logger = logging.getLogger(__name__)

# --- Database setup --- use the singleton DBPool engine so all code shares one connection
_db_pool = get_db_pool()
engine = _db_pool.engine
SessionFactory = _db_pool.session_factory


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

    async def broadcast_all(self, message: dict):
        """Broadcast a message to all active connections."""
        for corps_id in list(self.active_connections.keys()):
            await self.broadcast(corps_id, message)


manager = ConnectionManager()

# Singleton references set during lifespan
_task_manager = None


def get_task_manager():
    return _task_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _task_manager
    # Import all models so Base.metadata.create_all() sees every table
    import backend.models  # noqa: F401

    test_mode = os.environ.get("DCI_TEST_MODE") == "1"

    from backend.database import init_db
    init_db(engine)

    # Ensure generated_images directory exists
    from pathlib import Path
    images_dir = Path("generated_images")
    images_dir.mkdir(exist_ok=True)

    if not test_mode:
        # Reap any orphaned subprocesses from a previous crash of this instance
        from backend.services.process_registry import get_process_registry
        get_process_registry().reap_orphans()

    # Initialize task manager with real LLM client and tool registry
    from backend.services.llm_client import build_llm_client, MockLLMClient
    from backend.tools import create_tool_registry
    from backend.services.tool_executor import ToolExecutor
    from backend.services.task_manager import TaskManager

    if not test_mode:
        # Seed founding corps on first startup
        from backend.services.corps_seeder import seed_founding_corps
        from backend.services.model_spec_seeder import seed_default_specs
        seed_db = SessionFactory()
        try:
            seed_default_specs(seed_db)
            seed_founding_corps(seed_db)
        finally:
            seed_db.close()

    if test_mode:
        llm_client = MockLLMClient()
    else:
        llm_client = build_llm_client()

    # Enable agent code writes so competition dispatch can produce real implementations
    os.environ.setdefault("DSI_ENABLE_CODE_WRITES", "1")

    registry = create_tool_registry()
    tool_executor = ToolExecutor(registry)
    _task_manager = TaskManager(manager, llm_client, tool_executor)

    if not test_mode:
        _task_manager.start_metronome()

        # Broadcast achievement unlocks via websocket
        from backend.services.event_bus import get_event_bus

        def _broadcast_award(topic: str, payload: dict):
            if topic != "award.unlocked":
                return
            corps_id = payload.get("corps_id")
            if corps_id:
                asyncio.create_task(manager.broadcast(corps_id, payload))
            else:
                asyncio.create_task(manager.broadcast_all(payload))

        get_event_bus().subscribe("award.unlocked", _broadcast_award)

    yield

    _task_manager.stop()

    if not test_mode:
        # Kill any orphaned subprocesses
        from backend.services.process_registry import get_process_registry
        registry = get_process_registry()
        if registry.count > 0:
            logger.info("Shutdown: killing %d orphaned subprocess(es)", registry.count)
            registry.kill_all()


def get_db():
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()


# --- App ---

app = FastAPI(title="DCI Swarm", version="0.1.0", lifespan=lifespan)

# --- Legacy routes (superseded by v1 API — kept for reference, not mounted) ---
# from backend.api.workspace_routes import router as workspace_router
# from backend.api.design_room_routes import router as design_room_router
# from backend.api.judging_routes import router as judging_router
# from backend.api.evolution_routes import router as evolution_router
# from backend.api.seance_routes import router as seance_router

# --- V1 versioned API (domain routers) ---
from backend.api.v1.corps import router as v1_corps_router
from backend.api.v1.design import router as v1_design_router
from backend.api.v1.competitions import router as v1_competitions_router
from backend.api.v1.messaging import router as v1_messaging_router
from backend.api.v1.seasons import router as v1_seasons_router
from backend.api.v1.runs import router as v1_runs_router
from backend.api.v1.seances import router as v1_seances_router
from backend.api.v1.shows import router as v1_shows_router
from backend.api.v1.performers import router as v1_performers_router
from backend.api.v1.system import router as v1_system_router
from backend.api.v1.segments import router as v1_segments_router
from backend.api.v1.reps import router as v1_reps_router
from backend.api.v1.metrics import router as v1_metrics_router
from backend.api.v1.critique import router as v1_critique_router
from backend.api.v1.evolution import router as v1_evolution_router
from backend.api.v1.admin import router as v1_admin_router
from backend.api.v1.judging import router as v1_judging_router
from backend.api.v1.self_improvement import router as v1_self_improvement_router
from backend.api.v1.agents import router as v1_agents_router
from backend.api.v1.staff import router as v1_staff_router
from backend.api.v1.templates import router as v1_templates_router
from backend.api.v1.ci import router as v1_ci_router
from backend.api.v1.awards import router as v1_awards_router
from backend.api.v1.misc import router as v1_misc_router
from backend.api.v1.drill_books import router as v1_drill_books_router
from backend.api.v1.experiments import router as v1_experiments_router
from backend.api.v1.images import router as v1_images_router
from backend.api.v1.model_strategy import router as v1_model_strategy_router

for _r in [
    v1_corps_router, v1_design_router, v1_competitions_router, v1_messaging_router,
    v1_seasons_router, v1_runs_router, v1_seances_router, v1_shows_router,
    v1_performers_router, v1_system_router, v1_segments_router, v1_reps_router,
    v1_metrics_router, v1_critique_router, v1_evolution_router, v1_admin_router,
    v1_judging_router, v1_self_improvement_router, v1_agents_router, v1_staff_router,
    v1_templates_router, v1_ci_router, v1_awards_router, v1_misc_router,
    v1_drill_books_router,
    v1_experiments_router,
    v1_images_router,
    v1_model_strategy_router,
]:
    app.include_router(_r)


from fastapi.staticfiles import StaticFiles
import pathlib as _pathlib
_img_dir = _pathlib.Path("generated_images")
_img_dir.mkdir(exist_ok=True)
app.mount("/generated_images", StaticFiles(directory=str(_img_dir)), name="generated_images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Ensure unhandled exceptions still return CORS-safe JSON ---

from fastapi.requests import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


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

                        # Wake agent with full context including chat history
                        tm = get_task_manager()
                        if tm:
                            session_id = tm.get_session_for_role(db, corps_id, to_role)
                            if session_id and not tm.is_active(session_id):
                                from backend.services.chat_service import build_chat_agent_context
                                task_desc, snapshot = build_chat_agent_context(
                                    db, corps_id, to_role, content, session_id
                                )
                                tm.start_agent(
                                    session_id=session_id,
                                    task_description=task_desc,
                                    corps_id=corps_id,
                                    context_snapshot=snapshot,
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
