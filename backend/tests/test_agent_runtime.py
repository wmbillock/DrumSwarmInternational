import json

import pytest

from backend.models.agent_definition import ModelTier
from backend.models.agent_session import SessionStatus
from backend.services.agent_lifecycle import create_definition, spawn_session
from backend.services.agent_runtime import build_initial_messages, run_agent
from backend.services.llm_client import (
    LLMMessage,
    LLMResponse,
    MockLLMClient,
    MODEL_TIER_MAP,
    ToolCall,
)
from backend.services.tool_executor import ToolExecutor, ToolRegistry


CORPS_ID = "test-corps-1"


def _make_registry_and_executor():
    registry = ToolRegistry()
    registry.register(
        "tuner",
        lambda value: {"in_tune": True, "value": value},
        schema={"name": "tuner", "description": "Check if value is in tune"},
    )
    registry.register(
        "gock_block",
        lambda duration: {"timing_ok": duration <= 100},
        schema={"name": "gock_block", "description": "Check timing"},
    )
    return registry, ToolExecutor(registry)


class TestBuildInitialMessages:
    def test_basic_messages(self, db):
        defn = create_definition(db, "performer", "You are a performer.")
        messages = build_initial_messages(defn, "Implement the login page")
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[0].content == "You are a performer."
        assert messages[1].role == "user"
        assert messages[1].content == "Implement the login page"

    def test_with_context_snapshot(self, db):
        defn = create_definition(db, "performer", "You are a performer.")
        snapshot = json.dumps({"summary": "Started login, got to 50%"})
        messages = build_initial_messages(defn, "Continue the work", context_snapshot=snapshot)
        assert len(messages) == 4
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert "previous session" in messages[1].content
        assert snapshot in messages[1].content
        assert messages[2].role == "assistant"
        assert messages[3].role == "user"
        assert messages[3].content == "Continue the work"


class TestLLMClient:
    def test_mock_records_calls(self):
        client = MockLLMClient()
        messages = [LLMMessage("user", "Hello")]
        client.chat(messages, ModelTier.SONNET)
        assert len(client.calls) == 1
        assert client.calls[0]["model_tier"] == ModelTier.SONNET
        assert client.calls[0]["model_id"] == MODEL_TIER_MAP[ModelTier.SONNET]

    def test_mock_returns_default(self):
        client = MockLLMClient()
        response = client.chat([LLMMessage("user", "Hi")], ModelTier.HAIKU)
        assert response.content == "Mock response"
        assert not response.wants_tool_use

    def test_mock_queued_responses(self):
        client = MockLLMClient()
        client.queue_response(LLMResponse(content="First"))
        client.queue_response(LLMResponse(content="Second"))
        r1 = client.chat([LLMMessage("user", "1")], ModelTier.HAIKU)
        r2 = client.chat([LLMMessage("user", "2")], ModelTier.HAIKU)
        r3 = client.chat([LLMMessage("user", "3")], ModelTier.HAIKU)
        assert r1.content == "First"
        assert r2.content == "Second"
        assert r3.content == "Mock response"  # falls back to default

    def test_tool_call_response(self):
        client = MockLLMClient()
        client.queue_response(LLMResponse(
            content="",
            tool_calls=[ToolCall(tool_name="tuner", arguments={"value": 440})],
            stop_reason="tool_use",
        ))
        response = client.chat([LLMMessage("user", "Check pitch")], ModelTier.SONNET)
        assert response.wants_tool_use
        assert response.tool_calls[0].tool_name == "tuner"

    def test_model_tier_mapping(self):
        assert MODEL_TIER_MAP[ModelTier.OPUS] == "claude-opus-4-5-20251101"
        assert MODEL_TIER_MAP[ModelTier.SONNET] == "claude-sonnet-4-20250514"
        assert MODEL_TIER_MAP[ModelTier.HAIKU] == "claude-haiku-4-20250414"


class TestToolRegistry:
    def test_register_and_call(self):
        registry = ToolRegistry()
        registry.register("add", lambda a, b: a + b)
        func = registry.get_tool("add")
        assert func(2, 3) == 5

    def test_list_tools(self):
        registry, _ = _make_registry_and_executor()
        assert set(registry.list_tools()) == {"tuner", "gock_block"}

    def test_schemas_for_session(self, db):
        registry, _ = _make_registry_and_executor()
        defn = create_definition(db, "performer", "test", tools_allowed=["tuner"])
        session = spawn_session(db, defn.id, CORPS_ID)
        schemas = registry.get_schemas_for_session(db, session.id)
        assert len(schemas) == 1
        assert schemas[0]["name"] == "tuner"

    def test_schemas_filtered_by_permission(self, db):
        registry, _ = _make_registry_and_executor()
        defn = create_definition(db, "performer", "test", tools_allowed=[])
        session = spawn_session(db, defn.id, CORPS_ID)
        schemas = registry.get_schemas_for_session(db, session.id)
        assert len(schemas) == 0


class TestToolExecutor:
    def test_execute_permitted_tool(self, db):
        _, executor = _make_registry_and_executor()
        defn = create_definition(db, "performer", "test", tools_allowed=["tuner"])
        session = spawn_session(db, defn.id, CORPS_ID)
        result = executor.execute(db, session.id, "tuner", {"value": 440})
        assert result.success is True
        assert result.output == {"in_tune": True, "value": 440}

    def test_execute_denied_tool(self, db):
        from backend.services.tool_executor import ToolPermissionDenied
        _, executor = _make_registry_and_executor()
        defn = create_definition(db, "performer", "test", tools_allowed=["tuner"])
        session = spawn_session(db, defn.id, CORPS_ID)
        with pytest.raises(ToolPermissionDenied):
            executor.execute(db, session.id, "gock_block", {"duration": 50})

    def test_execute_unknown_tool(self, db):
        from backend.services.tool_executor import ToolNotFound
        _, executor = _make_registry_and_executor()
        defn = create_definition(db, "performer", "test", tools_allowed=["nonexistent"])
        session = spawn_session(db, defn.id, CORPS_ID)
        with pytest.raises(ToolNotFound):
            executor.execute(db, session.id, "nonexistent", {})

    def test_tool_error_returns_result(self, db):
        registry = ToolRegistry()
        registry.register("explode", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        executor = ToolExecutor(registry)
        defn = create_definition(db, "performer", "test", tools_allowed=["explode"])
        session = spawn_session(db, defn.id, CORPS_ID)
        result = executor.execute(db, session.id, "explode", {})
        assert result.success is False
        assert "boom" in result.error


class TestAgentRuntime:
    def test_simple_completion(self, db):
        registry, executor = _make_registry_and_executor()
        client = MockLLMClient()
        client.queue_response(LLMResponse(content="Task done."))

        defn = create_definition(db, "performer", "You do work.", tools_allowed=["tuner"])
        session = spawn_session(db, defn.id, CORPS_ID)

        result = run_agent(db, session.id, client, executor, "Do the thing")
        assert result.status == "completed"
        assert result.final_response == "Task done."
        assert result.iterations == 1
        assert len(result.tool_calls_made) == 0

        # Session should be completed with snapshot
        db.refresh(session)
        assert session.status == SessionStatus.COMPLETED
        assert session.context_snapshot is not None

    def test_tool_use_loop(self, db):
        registry, executor = _make_registry_and_executor()
        client = MockLLMClient()

        # First response: request tool use
        client.queue_response(LLMResponse(
            content="Let me check the tuning.",
            tool_calls=[ToolCall(tool_name="tuner", arguments={"value": 440})],
            stop_reason="tool_use",
        ))
        # Second response: done
        client.queue_response(LLMResponse(content="Tuning is good. Task complete."))

        defn = create_definition(db, "performer", "You do work.", tools_allowed=["tuner"])
        session = spawn_session(db, defn.id, CORPS_ID)

        result = run_agent(db, session.id, client, executor, "Check tuning")
        assert result.status == "completed"
        assert result.iterations == 2
        assert len(result.tool_calls_made) == 1
        assert result.tool_calls_made[0]["tool"] == "tuner"
        assert result.tool_calls_made[0]["result"]["success"] is True

    def test_denied_tool_in_loop(self, db):
        registry, executor = _make_registry_and_executor()
        client = MockLLMClient()

        # LLM requests a tool the agent doesn't have permission for
        client.queue_response(LLMResponse(
            content="",
            tool_calls=[ToolCall(tool_name="gock_block", arguments={"duration": 50})],
            stop_reason="tool_use",
        ))
        client.queue_response(LLMResponse(content="OK, I'll proceed without that tool."))

        defn = create_definition(db, "performer", "You do work.", tools_allowed=["tuner"])
        session = spawn_session(db, defn.id, CORPS_ID)

        result = run_agent(db, session.id, client, executor, "Do work")
        assert result.status == "completed"
        assert result.tool_calls_made[0]["result"]["success"] is False
        assert "permission" in result.tool_calls_made[0]["result"]["error"].lower()

    def test_max_iterations(self, db):
        registry, executor = _make_registry_and_executor()
        client = MockLLMClient()

        # Always request tool use — never terminate
        for _ in range(5):
            client.queue_response(LLMResponse(
                content="",
                tool_calls=[ToolCall(tool_name="tuner", arguments={"value": 440})],
                stop_reason="tool_use",
            ))

        defn = create_definition(db, "performer", "You do work.", tools_allowed=["tuner"])
        session = spawn_session(db, defn.id, CORPS_ID)

        result = run_agent(db, session.id, client, executor, "Infinite loop", max_iterations=3)
        assert result.status == "max_iterations"
        assert result.iterations == 3

    def test_model_tier_passed_to_client(self, db):
        registry, executor = _make_registry_and_executor()
        client = MockLLMClient()

        defn = create_definition(
            db, "brass_caption_head", "You lead brass.",
            model_tier=ModelTier.OPUS, tools_allowed=["tuner"],
        )
        session = spawn_session(db, defn.id, CORPS_ID)

        run_agent(db, session.id, client, executor, "Do work")
        assert client.calls[0]["model_tier"] == ModelTier.OPUS

    def test_context_warmup(self, db):
        registry, executor = _make_registry_and_executor()
        client = MockLLMClient()

        defn = create_definition(db, "performer", "You do work.", tools_allowed=["tuner"])
        session = spawn_session(db, defn.id, CORPS_ID)

        snapshot = json.dumps({"progress": "50%", "notes": "login half done"})
        run_agent(db, session.id, client, executor, "Continue work", context_snapshot=snapshot)

        # Verify the messages sent to LLM include the snapshot
        sent_messages = client.calls[0]["messages"]
        assert len(sent_messages) == 4  # system, snapshot user, snapshot ack, task
        assert "previous session" in sent_messages[1].content
        assert "50%" in sent_messages[1].content

    def test_snapshot_saved_on_completion(self, db):
        registry, executor = _make_registry_and_executor()
        client = MockLLMClient()
        client.queue_response(LLMResponse(content="All done."))

        defn = create_definition(db, "performer", "You do work.")
        session = spawn_session(db, defn.id, CORPS_ID)

        run_agent(db, session.id, client, executor, "Do work")

        db.refresh(session)
        snapshot = json.loads(session.context_snapshot)
        assert snapshot["final_response"] == "All done."
        assert snapshot["iterations"] == 1

    def test_session_failed_on_error(self, db):
        """If the LLM client raises, the session should be marked failed."""
        registry, executor = _make_registry_and_executor()

        class FailingClient(MockLLMClient):
            def chat(self, messages, model_tier, tools=None):
                raise RuntimeError("API down")

        client = FailingClient()
        defn = create_definition(db, "performer", "You do work.")
        session = spawn_session(db, defn.id, CORPS_ID)

        result = run_agent(db, session.id, client, executor, "Do work")
        assert result.status == "failed"
        assert "API down" in result.error

        db.refresh(session)
        assert session.status == SessionStatus.FAILED
