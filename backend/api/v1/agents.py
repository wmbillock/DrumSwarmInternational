"""V1 API — Agent memory and stats routes."""

from typing import Optional

from fastapi import APIRouter

from backend.api.v1.helpers import _get_db_session

router = APIRouter(prefix="/api/v1")


@router.get("/agents/{agent_identity}/memories")
def v1_get_memories(agent_identity: str, memory_type: Optional[str] = None):
    from backend.services.memory_manager import MemoryManager
    db = _get_db_session()
    try:
        mgr = MemoryManager(db)
        memories = mgr.get_memories(agent_identity, memory_type=memory_type)
        return [
            {"id": m.id, "memory_type": m.memory_type, "title": m.title,
             "content": m.content, "confidence": m.confidence, "version": m.version,
             "created_at": m.created_at.isoformat() if m.created_at else None}
            for m in memories
        ]
    finally:
        db.close()


@router.get("/agents/{agent_identity}/memory-stats")
def v1_memory_stats(agent_identity: str):
    from backend.services.memory_manager import MemoryManager
    db = _get_db_session()
    try:
        mgr = MemoryManager(db)
        return mgr.get_memory_stats(agent_identity)
    finally:
        db.close()
