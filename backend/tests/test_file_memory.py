"""Tests for file-based memory — human-inspectable agent state storage."""

import json
import pytest
from pathlib import Path

from backend.services.file_memory import FileMemory


@pytest.fixture
def fm(tmp_path):
    return FileMemory(base_path=str(tmp_path))


class TestProfile:
    def test_save_and_load(self, fm):
        profile = {"name": "Test Agent", "role": "brass_tech", "preferences": {"verbose": True}}
        fm.save_profile("agent-1", profile)
        loaded = fm.load_profile("agent-1")
        assert loaded == profile

    def test_load_missing_returns_empty(self, fm):
        assert fm.load_profile("nonexistent") == {}


class TestSessionSummary:
    def test_save_creates_file(self, fm):
        path = fm.save_session_summary("agent-1", "session-abc", "# Summary\nDid stuff.")
        assert path.exists()
        assert path.read_text() == "# Summary\nDid stuff."

    def test_list_summaries(self, fm):
        fm.save_session_summary("agent-1", "s1", "summary 1")
        fm.save_session_summary("agent-1", "s2", "summary 2")
        summaries = fm.list_summaries("agent-1")
        assert sorted(summaries) == ["s1", "s2"]

    def test_list_summaries_empty(self, fm):
        assert fm.list_summaries("nobody") == []


class TestDecision:
    def test_save_creates_file(self, fm):
        decision = {"tool": "handoff", "to": "tech", "reason": "escalation"}
        path = fm.save_decision("agent-1", "d-001", decision)
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded == decision

    def test_list_decisions(self, fm):
        fm.save_decision("agent-1", "d1", {"a": 1})
        fm.save_decision("agent-1", "d2", {"b": 2})
        decisions = fm.list_decisions("agent-1")
        assert sorted(decisions) == ["d1", "d2"]

    def test_list_decisions_empty(self, fm):
        assert fm.list_decisions("nobody") == []
