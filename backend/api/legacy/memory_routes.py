"""Legacy memory endpoints extracted from app.py."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.app import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Schemas ---

class MemoryUpdate(BaseModel):
    content: str


# --- Memory endpoints ---

@router.get("/api/agents/{agent_identity}/memories")
def api_get_memories(agent_identity: str, memory_type: Optional[str] = None, db: Session = Depends(get_db)):
    from backend.services.memory_manager import MemoryManager
    mgr = MemoryManager(db)
    memories = mgr.get_memories(agent_identity, memory_type=memory_type)
    return [
        {
            "id": m.id,
            "memory_type": m.memory_type,
            "title": m.title,
            "content": m.content,
            "confidence": m.confidence,
            "version": m.version,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in memories
    ]


@router.get("/api/agents/{agent_identity}/memory-stats")
def api_memory_stats(agent_identity: str, db: Session = Depends(get_db)):
    from backend.services.memory_manager import MemoryManager
    mgr = MemoryManager(db)
    return mgr.get_memory_stats(agent_identity)


@router.put("/api/memories/{memory_id}")
def api_update_memory(memory_id: str, data: MemoryUpdate, db: Session = Depends(get_db)):
    from backend.services.memory_manager import MemoryManager
    mgr = MemoryManager(db)
    new_mem = mgr.supersede_memory(memory_id, data.content)
    return {"id": new_mem.id, "version": new_mem.version}


@router.delete("/api/memories/{memory_id}")
def api_delete_memory(memory_id: str, db: Session = Depends(get_db)):
    from backend.services.memory_manager import MemoryManager
    mgr = MemoryManager(db)
    mgr.delete_memory(memory_id)
    return {"status": "deleted"}
