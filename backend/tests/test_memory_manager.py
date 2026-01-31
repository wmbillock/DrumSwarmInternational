"""Tests for the three-layer memory manager."""

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.agent_memory import AgentMemory, MemoryType, TaskMemory

# Import all models for table creation
import backend.models.segment  # noqa: F401
import backend.models.rep  # noqa: F401
import backend.models.message  # noqa: F401
import backend.models.problem  # noqa: F401
import backend.models.subscription  # noqa: F401
import backend.models.agent_session  # noqa: F401
import backend.models.agent_definition  # noqa: F401
import backend.models.score  # noqa: F401
import backend.models.penalty  # noqa: F401
import backend.models.corps  # noqa: F401
import backend.models.agent_experience  # noqa: F401
import backend.models.self_improvement_log  # noqa: F401

from backend.services.memory_manager import MemoryManager


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mm(db):
    return MemoryManager(db)


class TestPrepareContext:
    def test_empty(self, mm):
        import uuid
        unique = f"agent-{uuid.uuid4()}"
        ctx = mm.prepare_context(unique, "do something unique " + unique)
        assert ctx["episodic"] == []
        assert ctx["explicit"] == []

    def test_returns_explicit_memories(self, db, mm):
        mm.store_explicit_memory("agent-1", MemoryType.LESSON.value, "Test", "Content", 0.9)
        ctx = mm.prepare_context("agent-1", "task")
        assert len(ctx["explicit"]) == 1
        assert ctx["explicit"][0]["title"] == "Test"

    def test_excludes_low_confidence(self, db, mm):
        mm.store_explicit_memory("agent-1", MemoryType.LESSON.value, "Low", "Content", 0.3)
        ctx = mm.prepare_context("agent-1", "task")
        assert len(ctx["explicit"]) == 0


class TestStoreAfterAction:
    def test_stores_task_memory(self, db, mm):
        mm.store_after_action("s-1", "agent-1", "build feature", "Done", True)
        tasks = db.query(TaskMemory).filter(TaskMemory.agent_identity == "agent-1").all()
        assert len(tasks) == 1
        assert tasks[0].success is True

    def test_stores_decisions_from_tool_calls(self, db, mm):
        mm.store_after_action(
            "s-1", "agent-1", "task", "Done", True,
            tool_calls_made=[{"tool": "handoff", "arguments": {"to": "tech"}}],
        )
        decisions = db.query(AgentMemory).filter(
            AgentMemory.memory_type == MemoryType.DECISION.value
        ).all()
        assert len(decisions) == 1

    def test_stores_summary_on_success(self, db, mm):
        mm.store_after_action("s-1", "agent-1", "task", "Result summary", True)
        summaries = db.query(AgentMemory).filter(
            AgentMemory.memory_type == MemoryType.SUMMARY.value
        ).all()
        assert len(summaries) == 1

    def test_no_summary_on_failure(self, db, mm):
        mm.store_after_action("s-1", "agent-1", "task", "Failed", False)
        summaries = db.query(AgentMemory).filter(
            AgentMemory.memory_type == MemoryType.SUMMARY.value
        ).all()
        assert len(summaries) == 0


class TestSupersede:
    def test_supersede_creates_new_version(self, db, mm):
        old = mm.store_explicit_memory("agent-1", MemoryType.LESSON.value, "T", "v1")
        new = mm.supersede_memory(old.id, "v2")
        assert new.version == 2
        assert new.content == "v2"
        db.refresh(old)
        assert old.superseded_by == new.id

    def test_get_excludes_superseded(self, db, mm):
        old = mm.store_explicit_memory("agent-1", MemoryType.LESSON.value, "T", "v1")
        mm.supersede_memory(old.id, "v2")
        memories = mm.get_memories("agent-1")
        assert len(memories) == 1
        assert memories[0].content == "v2"

    def test_get_includes_superseded(self, db, mm):
        old = mm.store_explicit_memory("agent-1", MemoryType.LESSON.value, "T", "v1")
        mm.supersede_memory(old.id, "v2")
        memories = mm.get_memories("agent-1", include_superseded=True)
        assert len(memories) == 2


class TestGetMemories:
    def test_filter_by_type(self, db, mm):
        mm.store_explicit_memory("agent-1", MemoryType.LESSON.value, "L", "lesson")
        mm.store_explicit_memory("agent-1", MemoryType.DECISION.value, "D", "decision")
        lessons = mm.get_memories("agent-1", memory_type=MemoryType.LESSON.value)
        assert len(lessons) == 1
        assert lessons[0].title == "L"


class TestDeleteMemory:
    def test_delete(self, db, mm):
        mem = mm.store_explicit_memory("agent-1", MemoryType.LESSON.value, "T", "C")
        mm.delete_memory(mem.id)
        assert mm.get_memories("agent-1") == []

    def test_delete_nonexistent(self, mm):
        mm.delete_memory("nonexistent")  # should not raise


class TestMemoryStats:
    def test_returns_counts(self, db, mm):
        mm.store_explicit_memory("agent-1", MemoryType.LESSON.value, "L1", "c")
        mm.store_explicit_memory("agent-1", MemoryType.LESSON.value, "L2", "c")
        mm.store_explicit_memory("agent-1", MemoryType.DECISION.value, "D1", "c")
        stats = mm.get_memory_stats("agent-1")
        assert stats["total_memories"] == 3
        assert stats["by_type"][MemoryType.LESSON.value] == 2
        assert stats["by_type"][MemoryType.DECISION.value] == 1

    def test_empty_stats(self, mm):
        stats = mm.get_memory_stats("nobody")
        assert stats["total_memories"] == 0
        assert stats["task_memories"] == 0


class TestFormatForPrompt:
    def test_formats_explicit(self, mm):
        ctx = {
            "semantic": [],
            "episodic": [],
            "explicit": [{"type": "lesson", "title": "T", "content": "C", "confidence": 1.0}],
        }
        result = mm.format_for_prompt(ctx)
        assert "Remembered Knowledge" in result
        assert "[lesson] T: C" in result

    def test_empty_returns_empty(self, mm):
        result = mm.format_for_prompt({"semantic": [], "episodic": [], "explicit": []})
        assert result == ""
