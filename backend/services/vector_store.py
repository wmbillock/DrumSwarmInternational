"""Vector store — ChromaDB wrapper for semantic memory.

Two collections:
- swarm_memory: institutional knowledge, lessons learned, prior work patterns
- drill_book_context: embeddings of drill book summaries, evidence, outcomes

Falls back gracefully if ChromaDB is not available.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_client = None
_available = None


def _get_client():
    """Lazily initialize ChromaDB client with persistent storage."""
    global _client, _available
    if _available is False:
        return None
    if _client is not None:
        return _client
    try:
        import chromadb
        _client = chromadb.PersistentClient(path=".chromadb")
        _available = True
        logger.info("ChromaDB client initialized (persistent at .chromadb/)")
        return _client
    except Exception:
        _available = False
        logger.info("ChromaDB not available — vector store disabled")
        return None


def is_available() -> bool:
    """Check if the vector store is available."""
    return _get_client() is not None


def _get_collection(name: str):
    """Get or create a ChromaDB collection."""
    client = _get_client()
    if client is None:
        return None
    return client.get_or_create_collection(name=name)


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def store_memory(
    collection: str,
    text: str,
    metadata: Optional[dict] = None,
    doc_id: Optional[str] = None,
) -> Optional[str]:
    """Embed and store a text in the given collection.

    Returns the document ID, or None if store unavailable.
    """
    coll = _get_collection(collection)
    if coll is None:
        return None

    import uuid
    doc_id = doc_id or str(uuid.uuid4())
    try:
        coll.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id],
        )
        return doc_id
    except Exception:
        logger.debug("Failed to store memory in %s", collection, exc_info=True)
        return None


def search_memory(
    collection: str,
    query: str,
    top_k: int = 5,
    where: Optional[dict] = None,
) -> list[dict]:
    """Semantic search in a collection.

    Returns list of {id, document, metadata, distance}.
    """
    coll = _get_collection(collection)
    if coll is None:
        return []

    try:
        kwargs = {
            "query_texts": [query],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where

        results = coll.query(**kwargs)

        output = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                output.append({
                    "id": doc_id,
                    "document": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                })
        return output
    except Exception:
        logger.debug("Failed to search %s", collection, exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Drill book context
# ---------------------------------------------------------------------------

DRILL_BOOK_COLLECTION = "drill_book_context"
SWARM_MEMORY_COLLECTION = "swarm_memory"


def store_drill_context(
    book_id: str,
    summary: str,
    outcome: str = "",
    corps_id: str = "",
    role: str = "",
) -> Optional[str]:
    """Index a completed drill book's summary + outcome for future retrieval."""
    text = f"Book: {summary}"
    if outcome:
        text += f"\nOutcome: {outcome}"

    return store_memory(
        DRILL_BOOK_COLLECTION,
        text,
        metadata={
            "book_id": book_id,
            "corps_id": corps_id,
            "role": role,
            "outcome": outcome[:200] if outcome else "",
        },
        doc_id=book_id,
    )


def search_drill_context(
    query: str,
    top_k: int = 5,
    corps_id: Optional[str] = None,
    role: Optional[str] = None,
) -> list[dict]:
    """Search drill book context for relevant prior work."""
    where = {}
    if corps_id:
        where["corps_id"] = corps_id
    if role:
        where["role"] = role
    return search_memory(DRILL_BOOK_COLLECTION, query, top_k=top_k, where=where or None)


# ---------------------------------------------------------------------------
# Swarm memory (institutional knowledge)
# ---------------------------------------------------------------------------


def store_lesson(
    text: str,
    agent_identity: str = "",
    corps_id: str = "",
    category: str = "general",
) -> Optional[str]:
    """Store an institutional lesson/insight."""
    return store_memory(
        SWARM_MEMORY_COLLECTION,
        text,
        metadata={
            "agent_identity": agent_identity,
            "corps_id": corps_id,
            "category": category,
        },
    )


def recall(
    query: str,
    top_k: int = 5,
    corps_id: Optional[str] = None,
) -> list[dict]:
    """Recall relevant institutional memories."""
    where = {"corps_id": corps_id} if corps_id else None
    return search_memory(SWARM_MEMORY_COLLECTION, query, top_k=top_k, where=where)
