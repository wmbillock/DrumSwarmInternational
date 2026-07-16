"""Memory manager — orchestrates three-layer agent memory.

Layers:
1. Short-term: in-process context (handled by agent_runtime)
2. Semantic: ChromaDB / memory_bank for similarity retrieval
3. Episodic/Structured: SQL tables (AgentMemory, TaskMemory)

Key principles:
- Store summaries, not raw transcripts
- Memory is explicit, inspectable, editable
- Agent doesn't decide what memory structures exist
- Separate long-term from scratchpad
"""

import hashlib
import json
import logging
import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.models.agent_memory import AgentMemory, MemoryType, TaskMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """Orchestrates the three memory layers for agent context."""

    def __init__(self, db: Session):
        self.db = db

    def prepare_context(
        self,
        agent_identity: str,
        task_description: str,
        max_semantic: int = 5,
        max_episodic: int = 3,
        max_explicit: int = 10,
    ) -> dict[str, Any]:
        """Retrieval flow: gather relevant memories for prompt injection.

        1. Query semantic store for relevant memories (if available)
        2. Query task_memory for same/similar tasks (episodic)
        3. Query agent_memory for high-confidence explicit memories
        4. Return structured dict ready for prompt injection
        """
        task_hash = hashlib.sha256(task_description.encode()).hexdigest()

        # Semantic retrieval from memory_bank (ChromaDB)
        semantic_memories: list[str] = []
        try:
            from backend.services.memory_bank import get_memory_bank
            bank = get_memory_bank()
            if bank:
                results = bank.recall(agent_identity, task_description, k=max_semantic)
                semantic_memories = [r.text if hasattr(r, 'text') else str(r) for r in results]
        except Exception as e:
            logger.debug("Semantic memory unavailable: %s", e)

        # Episodic retrieval — exact task match first, then recent
        similar_tasks = (
            self.db.query(TaskMemory)
            .filter(TaskMemory.agent_identity == agent_identity)
            .filter(TaskMemory.task_hash == task_hash)
            .order_by(TaskMemory.created_at.desc())
            .limit(max_episodic)
            .all()
        )

        if not similar_tasks:
            # Fall back to most recent tasks
            similar_tasks = (
                self.db.query(TaskMemory)
                .filter(TaskMemory.agent_identity == agent_identity)
                .order_by(TaskMemory.created_at.desc())
                .limit(max_episodic)
                .all()
            )

        # Explicit memories — high-confidence, non-superseded
        explicit = (
            self.db.query(AgentMemory)
            .filter(AgentMemory.agent_identity == agent_identity)
            .filter(AgentMemory.confidence >= 0.7)
            .filter(AgentMemory.superseded_by.is_(None))
            .order_by(AgentMemory.updated_at.desc())
            .limit(max_explicit)
            .all()
        )

        return {
            "semantic": semantic_memories,
            "episodic": [
                {
                    "summary": t.result_summary or "",
                    "success": t.success,
                    "tool_calls": json.loads(t.tool_calls) if t.tool_calls else [],
                }
                for t in similar_tasks
            ],
            "explicit": [
                {
                    "type": e.memory_type,
                    "title": e.title,
                    "content": e.content,
                    "confidence": e.confidence,
                }
                for e in explicit
            ],
        }

    def format_for_prompt(self, context: dict[str, Any]) -> str:
        """Format memory context as a prompt section."""
        parts: list[str] = []

        if context.get("explicit"):
            parts.append("## Remembered Knowledge")
            for mem in context["explicit"]:
                parts.append(f"- [{mem['type']}] {mem['title']}: {mem['content']}")

        if context.get("episodic"):
            parts.append("\n## Past Task Experience")
            for ep in context["episodic"]:
                status = "succeeded" if ep["success"] else "failed"
                parts.append(f"- Previous attempt ({status}): {ep['summary'][:200]}")

        if context.get("semantic"):
            parts.append("\n## Related Memories")
            for s in context["semantic"]:
                parts.append(f"- {s[:200]}")

        return "\n".join(parts) if parts else ""

    def store_after_action(
        self,
        session_id: str,
        agent_identity: str,
        task_description: str,
        result_summary: str,
        success: bool,
        tool_calls_made: list[dict] | None = None,
    ) -> None:
        """After-action write back to all memory layers."""
        task_hash = hashlib.sha256(task_description.encode()).hexdigest()

        # 1. Episodic: TaskMemory entry
        task_mem = TaskMemory(
            session_id=session_id,
            agent_identity=agent_identity,
            task_hash=task_hash,
            tool_calls=json.dumps(tool_calls_made or []),
            outcomes=json.dumps({"success": success}),
            result_summary=result_summary[:2000] if result_summary else "",
            success=success,
        )
        self.db.add(task_mem)

        # 2. Explicit: Extract decisions from high-stakes tool calls
        high_stakes_tools = {"handoff", "create_segment", "transition_rep", "submit_work", "fire_staff"}
        for tc in (tool_calls_made or []):
            tool_name = tc.get("tool", tc.get("tool_name", ""))
            if tool_name in high_stakes_tools:
                decision = AgentMemory(
                    agent_identity=agent_identity,
                    memory_type=MemoryType.DECISION.value,
                    title=f"{tool_name} decision",
                    content=json.dumps(tc.get("arguments", tc.get("args", {}))),
                    confidence=0.9 if success else 0.5,
                    source_session_id=session_id,
                    source_task=task_description[:500],
                )
                self.db.add(decision)

        # 3. Session summary as lesson (if successful)
        if success and result_summary:
            summary_mem = AgentMemory(
                agent_identity=agent_identity,
                memory_type=MemoryType.SUMMARY.value,
                title=f"Session {session_id[:8]} summary",
                content=result_summary[:1000],
                confidence=0.8,
                source_session_id=session_id,
            )
            self.db.add(summary_mem)

        # 4. Semantic: store in ChromaDB if available
        try:
            from backend.services.memory_bank import get_memory_bank
            bank = get_memory_bank()
            if bank and result_summary:
                bank.store(
                    agent_identity,
                    f"Task: {task_description[:200]}\nResult: {result_summary[:500]}",
                    metadata={"session_id": session_id, "success": success},
                )
        except Exception as e:
            logger.debug("Semantic memory store failed: %s", e)

        self.db.commit()

    def store_explicit_memory(
        self,
        agent_identity: str,
        memory_type: str,
        title: str,
        content: str,
        confidence: float = 1.0,
        session_id: str | None = None,
    ) -> AgentMemory:
        """Store an explicit memory entry."""
        mem = AgentMemory(
            agent_identity=agent_identity,
            memory_type=memory_type,
            title=title,
            content=content,
            confidence=confidence,
            source_session_id=session_id,
        )
        self.db.add(mem)
        self.db.commit()
        self.db.refresh(mem)
        return mem

    def supersede_memory(self, memory_id: str, new_content: str) -> AgentMemory:
        """Update a memory by creating a new version and marking old as superseded."""
        old = self.db.get(AgentMemory, memory_id)
        if old is None:
            raise ValueError(f"Memory {memory_id} not found")

        new_mem = AgentMemory(
            agent_identity=old.agent_identity,
            memory_type=old.memory_type,
            title=old.title,
            content=new_content,
            confidence=old.confidence,
            source_session_id=old.source_session_id,
            version=old.version + 1,
        )
        self.db.add(new_mem)
        self.db.flush()  # generate new_mem.id
        old.superseded_by = new_mem.id
        self.db.commit()
        self.db.refresh(new_mem)
        return new_mem

    def get_memories(
        self,
        agent_identity: str,
        memory_type: str | None = None,
        include_superseded: bool = False,
    ) -> list[AgentMemory]:
        """Retrieve memories for an agent."""
        query = self.db.query(AgentMemory).filter(
            AgentMemory.agent_identity == agent_identity
        )
        if memory_type:
            query = query.filter(AgentMemory.memory_type == memory_type)
        if not include_superseded:
            query = query.filter(AgentMemory.superseded_by.is_(None))
        return query.order_by(AgentMemory.updated_at.desc()).all()

    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory entry."""
        mem = self.db.get(AgentMemory, memory_id)
        if mem:
            self.db.delete(mem)
            self.db.commit()

    def get_memory_stats(self, agent_identity: str) -> dict:
        """Get memory statistics for an agent.

        Queries both SQL tables and ChromaDB. If SQL tables are empty
        (common — agent_runtime stores to ChromaDB, not SQL), falls
        back to ChromaDB collection stats.
        """
        from sqlalchemy import func as sa_func

        total = (
            self.db.query(sa_func.count(AgentMemory.id))
            .filter(AgentMemory.agent_identity == agent_identity)
            .scalar()
        ) or 0
        by_type = dict(
            self.db.query(AgentMemory.memory_type, sa_func.count(AgentMemory.id))
            .filter(AgentMemory.agent_identity == agent_identity)
            .filter(AgentMemory.superseded_by.is_(None))
            .group_by(AgentMemory.memory_type)
            .all()
        )
        avg_confidence = (
            self.db.query(sa_func.avg(AgentMemory.confidence))
            .filter(AgentMemory.agent_identity == agent_identity)
            .filter(AgentMemory.superseded_by.is_(None))
            .scalar()
        )
        task_count = (
            self.db.query(sa_func.count(TaskMemory.id))
            .filter(TaskMemory.agent_identity == agent_identity)
            .scalar()
        ) or 0

        # Enrich with ChromaDB if SQL tables are empty
        chroma_count = 0
        chroma_by_type: dict[str, int] = {}
        if total == 0:
            try:
                from backend.services.memory_bank import get_memory_bank
                bank = get_memory_bank()
                if bank.available:
                    collection = bank._get_collection(agent_identity)
                    chroma_count = collection.count()
                    if chroma_count > 0:
                        # Sample a few to get type distribution
                        sample = collection.get(
                            limit=min(chroma_count, 50),
                            include=["metadatas"],
                        )
                        for meta in (sample.get("metadatas") or []):
                            mt = (meta or {}).get("type", "general")
                            chroma_by_type[mt] = chroma_by_type.get(mt, 0) + 1
            except Exception as e:
                logger.debug("ChromaDB stats lookup failed for %s: %s", agent_identity, e)

        combined_total = total + chroma_count
        combined_by_type = dict(by_type)
        for mt, count in chroma_by_type.items():
            combined_by_type[mt] = combined_by_type.get(mt, 0) + count

        return {
            "total_memories": combined_total,
            "by_type": combined_by_type,
            "avg_confidence": round(avg_confidence or (0.7 if chroma_count > 0 else 0), 2),
            "task_memories": task_count,
        }
