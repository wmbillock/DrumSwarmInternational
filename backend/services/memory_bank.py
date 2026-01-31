"""Memory bank for persistent cross-session agent memory using ChromaDB.

Each agent identity (performer or role) gets its own collection. Memories are
stored as embeddings and can be recalled by semantic similarity to a query.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Global singleton
_memory_bank: Optional["MemoryBank"] = None


@dataclass
class Memory:
    """A single memory entry."""
    text: str
    metadata: dict = field(default_factory=dict)
    distance: float = 0.0


class MemoryBank:
    """ChromaDB-backed semantic memory for agents.

    Collections are keyed by agent identity (e.g. performer name or role).
    """

    def __init__(self, persist_directory: str = ".chromadb"):
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=persist_directory)
            self._available = True
        except ImportError:
            logger.warning("chromadb not installed — memory bank disabled")
            self._client = None
            self._available = False
        except Exception as e:
            logger.warning("Failed to initialize ChromaDB: %s", e)
            self._client = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def _get_collection(self, agent_identity: str):
        """Get or create a collection for an agent identity."""
        # ChromaDB collection names must be 3-63 chars, alphanumeric + underscores
        safe_name = agent_identity.replace(" ", "_").replace("-", "_")[:63]
        if len(safe_name) < 3:
            safe_name = safe_name + "_mem"
        return self._client.get_or_create_collection(name=safe_name)

    def store(
        self,
        agent_identity: str,
        text: str,
        metadata: Optional[dict] = None,
        memory_id: Optional[str] = None,
    ) -> bool:
        """Store a memory for an agent.

        Returns True if stored successfully, False if memory bank unavailable.
        """
        if not self._available:
            return False

        try:
            collection = self._get_collection(agent_identity)
            import uuid
            doc_id = memory_id or str(uuid.uuid4())
            meta = metadata or {}
            # ChromaDB metadata values must be str, int, float, or bool
            safe_meta = {"_source": "memory_bank"}  # ensure non-empty
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    safe_meta[k] = v
                else:
                    safe_meta[k] = json.dumps(v)
            collection.add(
                documents=[text],
                metadatas=[safe_meta],
                ids=[doc_id],
            )
            return True
        except Exception as e:
            logger.warning("Failed to store memory: %s", e)
            return False

    def recall(
        self,
        agent_identity: str,
        query: str,
        k: int = 5,
        where: Optional[dict] = None,
    ) -> list[Memory]:
        """Recall memories similar to query.

        Returns up to k Memory objects sorted by relevance.
        """
        if not self._available:
            return []

        try:
            collection = self._get_collection(agent_identity)
            if collection.count() == 0:
                return []
            # Don't request more results than exist
            n_results = min(k, collection.count())
            kwargs = {"query_texts": [query], "n_results": n_results}
            if where:
                kwargs["where"] = where
            results = collection.query(**kwargs)

            memories = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    dist = results["distances"][0][i] if results["distances"] else 0.0
                    memories.append(Memory(text=doc, metadata=meta, distance=dist))
            return memories
        except Exception as e:
            logger.warning("Failed to recall memories: %s", e)
            return []

    def store_session_summary(
        self,
        agent_identity: str,
        session_id: str,
        role: str,
        summary: str,
        corps_id: str = "",
        show_title: str = "",
    ) -> bool:
        """Store a session summary as a memory."""
        return self.store(
            agent_identity,
            summary,
            metadata={
                "type": "session_summary",
                "session_id": session_id,
                "role": role,
                "corps_id": corps_id,
                "show_title": show_title,
            },
            memory_id=f"session_{session_id}",
        )

    def store_failure_lesson(
        self,
        agent_identity: str,
        session_id: str,
        what_failed: str,
        lesson: str,
    ) -> bool:
        """Store a failure lesson for cross-session learning."""
        text = f"Failure: {what_failed}\nLesson: {lesson}"
        return self.store(
            agent_identity,
            text,
            metadata={
                "type": "failure_lesson",
                "session_id": session_id,
                "what_failed": what_failed,
            },
        )

    def get_context_for_task(
        self,
        agent_identity: str,
        task_description: str,
        k: int = 5,
    ) -> str:
        """Build a context string from relevant memories for a task.

        Returns a formatted string ready to inject into agent prompts.
        """
        memories = self.recall(agent_identity, task_description, k=k)
        if not memories:
            return ""

        lines = ["Relevant memories from previous sessions:"]
        for i, mem in enumerate(memories, 1):
            mem_type = mem.metadata.get("type", "general")
            lines.append(f"\n[Memory {i} ({mem_type})]")
            lines.append(mem.text)
        return "\n".join(lines)


def get_memory_bank(persist_directory: str = ".chromadb") -> MemoryBank:
    """Get the global MemoryBank singleton."""
    global _memory_bank
    if _memory_bank is None:
        _memory_bank = MemoryBank(persist_directory=persist_directory)
    return _memory_bank
