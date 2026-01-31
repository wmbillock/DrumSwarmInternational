"""Tests for memory bank service."""

import os
import shutil
import tempfile

import pytest


@pytest.fixture
def memory_bank():
    """Create a memory bank with a temporary directory."""
    tmpdir = tempfile.mkdtemp()
    from backend.services.memory_bank import MemoryBank
    bank = MemoryBank(persist_directory=tmpdir)
    yield bank
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestMemoryBank:
    def test_store_and_recall(self, memory_bank):
        if not memory_bank.available:
            pytest.skip("chromadb not installed")

        memory_bank.store("agent_alice", "Completed the pricing task successfully")
        memories = memory_bank.recall("agent_alice", "pricing work", k=3)
        assert len(memories) == 1
        assert "pricing" in memories[0].text

    def test_recall_empty_collection(self, memory_bank):
        if not memory_bank.available:
            pytest.skip("chromadb not installed")

        memories = memory_bank.recall("nonexistent_agent", "anything")
        assert memories == []

    def test_store_session_summary(self, memory_bank):
        if not memory_bank.available:
            pytest.skip("chromadb not installed")

        result = memory_bank.store_session_summary(
            agent_identity="alice",
            session_id="sess-1",
            role="executive_director",
            summary="Decomposed the auth feature into 3 movements",
            corps_id="corps-1",
            show_title="Auth Project",
        )
        assert result is True

        memories = memory_bank.recall("alice", "auth feature")
        assert len(memories) == 1
        assert "auth" in memories[0].text.lower()
        assert memories[0].metadata["type"] == "session_summary"

    def test_store_failure_lesson(self, memory_bank):
        if not memory_bank.available:
            pytest.skip("chromadb not installed")

        memory_bank.store_failure_lesson(
            agent_identity="bob",
            session_id="sess-2",
            what_failed="API endpoint creation",
            lesson="Need to check schema before generating endpoints",
        )

        memories = memory_bank.recall("bob", "API endpoint errors")
        assert len(memories) == 1
        assert "schema" in memories[0].text.lower()

    def test_get_context_for_task(self, memory_bank):
        if not memory_bank.available:
            pytest.skip("chromadb not installed")

        memory_bank.store("carol", "Successfully refactored the database layer")
        memory_bank.store("carol", "Fixed a bug in the authentication middleware")

        context = memory_bank.get_context_for_task("carol", "database work")
        assert "Relevant memories" in context
        assert "database" in context.lower() or "authentication" in context.lower()

    def test_get_context_empty(self, memory_bank):
        if not memory_bank.available:
            pytest.skip("chromadb not installed")

        context = memory_bank.get_context_for_task("nobody", "anything")
        assert context == ""

    def test_multiple_agents_isolated(self, memory_bank):
        if not memory_bank.available:
            pytest.skip("chromadb not installed")

        memory_bank.store("agent_a", "Agent A's secret memory")
        memory_bank.store("agent_b", "Agent B's different memory")

        a_memories = memory_bank.recall("agent_a", "secret", k=10)
        b_memories = memory_bank.recall("agent_b", "different", k=10)

        assert len(a_memories) == 1
        assert "Agent A" in a_memories[0].text
        assert len(b_memories) == 1
        assert "Agent B" in b_memories[0].text

    def test_metadata_preserved(self, memory_bank):
        if not memory_bank.available:
            pytest.skip("chromadb not installed")

        memory_bank.store(
            "dave",
            "Test memory with metadata",
            metadata={"type": "test", "score": 95, "active": True},
        )

        memories = memory_bank.recall("dave", "test")
        assert len(memories) == 1
        assert memories[0].metadata["type"] == "test"
        assert memories[0].metadata["score"] == 95
