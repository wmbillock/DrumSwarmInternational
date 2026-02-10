"""Agent-callable memory tool — recall and learn from institutional knowledge.

Provides two actions:
- recall(query): search swarm memory for relevant prior work
- learn(insight): store a new lesson/pattern
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def recall_memory(
    db: Session,
    session_id: str,
    query: str,
    top_k: int = 5,
    corps_id: Optional[str] = None,
) -> dict:
    """Search institutional memory for relevant context.

    Returns search results from both swarm_memory and drill_book_context.
    """
    from backend.services.vector_store import recall, search_drill_context, is_available

    if not is_available():
        return {
            "success": False,
            "output": "Vector store not available",
            "error": None,
        }

    # Search both collections
    swarm_results = recall(query, top_k=top_k, corps_id=corps_id)
    drill_results = search_drill_context(query, top_k=top_k, corps_id=corps_id)

    # Merge and format
    memories = []
    for r in swarm_results:
        memories.append({
            "source": "institutional",
            "content": r["document"],
            "relevance": 1.0 - (r["distance"] or 0),
        })
    for r in drill_results:
        memories.append({
            "source": "drill_book",
            "content": r["document"],
            "relevance": 1.0 - (r["distance"] or 0),
        })

    # Sort by relevance
    memories.sort(key=lambda m: m["relevance"], reverse=True)
    memories = memories[:top_k]

    if not memories:
        return {
            "success": True,
            "output": "No relevant memories found.",
            "error": None,
        }

    lines = ["## Relevant Memories\n"]
    for i, m in enumerate(memories, 1):
        lines.append(f"{i}. [{m['source']}] {m['content']}")

    return {
        "success": True,
        "output": "\n".join(lines),
        "error": None,
    }


def learn_memory(
    db: Session,
    session_id: str,
    insight: str,
    category: str = "general",
    corps_id: Optional[str] = None,
) -> dict:
    """Store a new lesson/pattern in institutional memory."""
    from backend.services.vector_store import store_lesson, is_available

    if not is_available():
        return {
            "success": False,
            "output": "Vector store not available",
            "error": None,
        }

    # Get agent identity from session
    agent_identity = "unknown"
    try:
        from backend.models.agent_session import AgentSession
        from backend.models.agent_definition import AgentDefinition
        session = db.get(AgentSession, session_id)
        if session:
            defn = db.get(AgentDefinition, session.definition_id)
            if defn:
                agent_identity = defn.nickname or defn.role
            corps_id = corps_id or session.corps_id
    except Exception:
        pass

    doc_id = store_lesson(
        insight,
        agent_identity=agent_identity,
        corps_id=corps_id or "",
        category=category,
    )

    if doc_id:
        return {
            "success": True,
            "output": f"Lesson stored (id: {doc_id[:8]}...)",
            "error": None,
        }
    return {
        "success": False,
        "output": "Failed to store lesson",
        "error": "store_lesson returned None",
    }


# ---------------------------------------------------------------------------
# Tool schema for registration
# ---------------------------------------------------------------------------

RECALL_SCHEMA = {
    "name": "recall_memory",
    "description": "Search institutional memory for relevant prior work, lessons learned, and patterns.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for in memory",
            },
            "top_k": {
                "type": "integer",
                "description": "Max results to return",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

LEARN_SCHEMA = {
    "name": "learn_memory",
    "description": "Store a new lesson, insight, or pattern in institutional memory for future agents.",
    "parameters": {
        "type": "object",
        "properties": {
            "insight": {
                "type": "string",
                "description": "The lesson or insight to store",
            },
            "category": {
                "type": "string",
                "description": "Category: general, debugging, architecture, testing, etc.",
                "default": "general",
            },
        },
        "required": ["insight"],
    },
}
