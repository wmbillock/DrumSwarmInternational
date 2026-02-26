"""Tests for vector store — ChromaDB wrapper."""

import sys
import pytest

from backend.services import vector_store

# ChromaDB 1.5.1 uses pydantic v1 internals that break on Python 3.14+
_chromadb_broken = sys.version_info >= (3, 14)
pytestmark = pytest.mark.skipif(
    _chromadb_broken,
    reason="ChromaDB incompatible with Python 3.14+ (pydantic v1)",
)


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the global client between tests."""
    vector_store._client = None
    vector_store._available = None
    yield
    vector_store._client = None
    vector_store._available = None


class TestVectorStoreAvailability:
    def test_is_available(self):
        # ChromaDB is installed as a dep
        assert vector_store.is_available() is True

    def test_get_collection(self):
        coll = vector_store._get_collection("test_collection")
        assert coll is not None


class TestStoreAndSearch:
    def test_store_memory(self):
        doc_id = vector_store.store_memory(
            "test_store_search", "The agent learned to use error handling",
            metadata={"category": "lesson"},
        )
        assert doc_id is not None

    def test_search_memory(self):
        vector_store.store_memory(
            "test_search", "Python async patterns are important for concurrency",
            metadata={"category": "architecture"},
        )
        vector_store.store_memory(
            "test_search", "Always write tests before implementing features",
            metadata={"category": "testing"},
        )

        results = vector_store.search_memory("test_search", "how to handle concurrency")
        assert len(results) > 0
        assert "document" in results[0]

    def test_search_empty_collection(self):
        results = vector_store.search_memory("empty_test_collection", "anything")
        assert results == []


class TestDrillBookContext:
    def test_store_drill_context(self):
        doc_id = vector_store.store_drill_context(
            book_id="book-1",
            summary="Implemented error handling for agent runtime",
            outcome="All tests pass",
            corps_id="corps-1",
            role="brass_tech",
        )
        assert doc_id == "book-1"

    def test_search_drill_context(self):
        vector_store.store_drill_context(
            book_id="book-search-1",
            summary="Implemented RAII pattern for session cleanup",
            outcome="Sessions no longer leak",
            corps_id="corps-1",
            role="brass_tech",
        )

        results = vector_store.search_drill_context("session cleanup RAII")
        assert len(results) > 0


class TestSwarmMemory:
    def test_store_lesson(self):
        doc_id = vector_store.store_lesson(
            "Always check for orphaned sessions on startup",
            agent_identity="executive_director",
            corps_id="corps-1",
            category="debugging",
        )
        assert doc_id is not None

    def test_recall(self):
        vector_store.store_lesson(
            "Use context managers for DB sessions to prevent leaks",
            agent_identity="test_agent",
            corps_id="corps-recall",
            category="architecture",
        )

        results = vector_store.recall("DB session management")
        assert len(results) > 0
