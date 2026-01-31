"""Tests for dry-run simulation."""

from unittest.mock import MagicMock
from backend.services.simulation import DryRunToolExecutor, SimulationLLMClient, DryRunRecord
from backend.services.tool_executor import ToolRegistry, ToolResult
from backend.services.llm_client import MockLLMClient, LLMMessage, LLMResponse, ModelTier


class TestDryRunToolExecutor:
    def _make_executor(self):
        registry = ToolRegistry()
        registry.register("create_segment", lambda **kw: kw)
        registry.register("submit_work", lambda **kw: kw)
        return DryRunToolExecutor(registry)

    def test_records_calls(self):
        executor = self._make_executor()
        result = executor.execute(None, "session-1", "create_segment", {"type": "movement", "title": "test"})
        assert result.success
        assert len(executor.recorded_calls) == 1
        assert executor.recorded_calls[0].tool_name == "create_segment"

    def test_synthetic_result(self):
        executor = self._make_executor()
        result = executor.execute(None, "s", "create_segment", {"type": "set", "title": "t"})
        assert result.output["type"] == "set"
        assert result.output["status"] == "simulated"

    def test_summary(self):
        executor = self._make_executor()
        assert "No tool calls" in executor.get_summary()
        executor.execute(None, "s", "create_segment", {"type": "set", "title": "t"})
        executor.execute(None, "s", "submit_work", {"rep_id": "r1"})
        summary = executor.get_summary()
        assert "2 tool calls" in summary

    def test_does_not_check_permissions(self):
        executor = self._make_executor()
        # Should not raise even though no session exists
        result = executor.execute(None, "nonexistent", "create_segment", {"type": "movement", "title": "t"})
        assert result.success


class TestSimulationLLMClient:
    def test_injects_simulation_prefix(self):
        mock = MockLLMClient()
        sim = SimulationLLMClient(mock)
        sim.chat(
            [LLMMessage(role="system", content="You are a tech.")],
            ModelTier.OPUS,
        )
        assert len(mock.calls) == 1
        system_msg = mock.calls[0]["messages"][0]
        assert "SIMULATION MODE" in system_msg.content

    def test_forces_haiku(self):
        mock = MockLLMClient()
        sim = SimulationLLMClient(mock)
        sim.chat(
            [LLMMessage(role="system", content="test")],
            ModelTier.OPUS,
        )
        assert mock.calls[0]["model_tier"] == ModelTier.HAIKU
