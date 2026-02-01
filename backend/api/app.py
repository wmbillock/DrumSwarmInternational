"""FastAPI application — DCI Layer API."""

import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
    # Import all models so Base.metadata.create_all() sees every table
    import backend.models  # noqa: F401

    from backend.database import init_db
    init_db(engine)

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

# --- Workspace routes (filesystem readers) ---
from backend.api.workspace_routes import router as workspace_router
app.include_router(workspace_router)

# --- Design Room routes ---
from backend.api.design_room_routes import router as design_room_router
app.include_router(design_room_router)

# --- Judging & Critique routes ---
from backend.api.judging_routes import router as judging_router
app.include_router(judging_router)

# --- Evolution & Talent Pool routes ---
from backend.api.evolution_routes import router as evolution_router
app.include_router(evolution_router)

# --- Seance & Corps History routes ---
from backend.api.seance_routes import router as seance_router
app.include_router(seance_router)

# --- V1 versioned API ---
from backend.api.v1.router import router as v1_router
app.include_router(v1_router)

from backend.api.v1.scoreboards import router as scoreboards_router
app.include_router(scoreboards_router)

# --- Legacy routes (extracted from app.py) ---
from backend.api.legacy.shows_routes import router as shows_router
app.include_router(shows_router)

from backend.api.legacy.corps_routes import router as corps_router
app.include_router(corps_router)

from backend.api.legacy.segments_routes import router as segments_router
app.include_router(segments_router)

from backend.api.legacy.scoring_routes import router as scoring_router
app.include_router(scoring_router)

from backend.api.legacy.communication_routes import router as communication_router
from backend.api.legacy.communication_routes import _build_chat_agent_context  # noqa: F401 — re-export for tests
app.include_router(communication_router)

from backend.api.legacy.system_routes import router as system_router
app.include_router(system_router)

from backend.api.legacy.performers_routes import router as performers_router
app.include_router(performers_router)

from backend.api.legacy.improvement_routes import router as improvement_router
app.include_router(improvement_router)

from backend.api.legacy.memory_routes import router as memory_router
app.include_router(memory_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
                                from backend.api.legacy.communication_routes import _build_chat_agent_context
                                task_desc, snapshot = _build_chat_agent_context(
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
