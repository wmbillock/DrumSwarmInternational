"""Seance — query previous sessions for context and decisions.

"What did the last ED decide about X?" — implemented via memory bank
recall with session metadata filters.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class SeanceResult:
    """Result of a seance query."""
    query: str
    memories: list[dict] = field(default_factory=list)
    sessions_found: int = 0


def query_previous_sessions(
    query: str,
    role: Optional[str] = None,
    performer_name: Optional[str] = None,
    k: int = 5,
) -> SeanceResult:
    """Query previous sessions for context via the memory bank.

    Args:
        query: What to search for (e.g. "architecture decision for auth module")
        role: Optional role filter (e.g. "executive_director")
        performer_name: Optional performer name filter
        k: Max results to return
    """
    result = SeanceResult(query=query)

    try:
        from backend.services.memory_bank import get_memory_bank
        memory_bank = get_memory_bank()
        if not memory_bank.available:
            return result

        # Query by role identity if specified
        identity = role or performer_name or "system"
        memories = memory_bank.recall(identity, query, k=k)

        for mem in memories:
            result.memories.append({
                "text": mem.get("text", mem.get("document", "")),
                "metadata": mem.get("metadata", {}),
            })

        result.sessions_found = len(result.memories)

    except Exception:
        logger.warning("Seance query failed for: %s", query)

    return result


def query_for_agent_context(
    db: Session,
    role: str,
    task_description: str,
    corps_id: Optional[str] = None,
) -> str:
    """Build context from previous sessions for an agent starting work.

    Combines memory bank recall with capability ledger stats.
    """
    parts = []

    # Memory bank recall
    seance = query_previous_sessions(task_description, role=role, k=3)
    if seance.memories:
        parts.append("## Relevant context from previous sessions:")
        for mem in seance.memories:
            text = mem.get("text", "")
            if text:
                parts.append(f"- {text[:300]}")

    # Capability ledger stats
    try:
        from backend.models.agent_session import AgentSession
        from backend.models.agent_definition import AgentDefinition

        recent_sessions = (
            db.query(AgentSession)
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .filter(AgentDefinition.role == role)
            .order_by(AgentSession.started_at.desc())
            .limit(5)
            .all()
        )
        if recent_sessions:
            completed = sum(1 for s in recent_sessions if s.status.value == "completed")
            failed = sum(1 for s in recent_sessions if s.status.value == "failed")
            parts.append(f"\n## Recent performance: {completed}/{len(recent_sessions)} sessions succeeded, {failed} failed.")
    except Exception:
        pass

    return "\n".join(parts)
