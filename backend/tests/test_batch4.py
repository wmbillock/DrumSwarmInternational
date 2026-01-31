"""Tests for Batch 4: metrics, show templates, event bus, MCP adapter, dry-run."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# --- Metrics Collector ---

class TestMetricsCollector:
    def test_collect_corps_metrics_empty(self, db):
        from backend.services.metrics_collector import collect_corps_metrics
        metrics = collect_corps_metrics(db, "nonexistent")
        assert metrics.total_sessions == 0
        assert metrics.corps_id == "nonexistent"

    def test_recommendations_low_success_rate(self):
        from backend.services.metrics_collector import _generate_recommendations, CorpsMetrics, RoleMetrics
        rm = RoleMetrics(role="test", total_sessions=5, successful_sessions=1,
                         failed_sessions=4, success_rate=0.2)
        metrics = CorpsMetrics(corps_id="c1", role_metrics=[rm])
        recs = _generate_recommendations(metrics)
        assert any("prompt refinement" in r for r in recs)

    def test_recommendations_low_completion(self):
        from backend.services.metrics_collector import _generate_recommendations, CorpsMetrics
        metrics = CorpsMetrics(corps_id="c1", total_reps=10, completed_reps=3,
                               rep_completion_rate=0.3)
        recs = _generate_recommendations(metrics)
        assert any("completion rate" in r.lower() for r in recs)

    def test_recommendations_low_score(self):
        from backend.services.metrics_collector import _generate_recommendations, CorpsMetrics
        metrics = CorpsMetrics(corps_id="c1", avg_score=45.0)
        recs = _generate_recommendations(metrics)
        assert any("score below 60" in r.lower() for r in recs)


# --- Show Templates ---

class TestShowTemplates:
    def test_list_templates(self):
        from backend.services.show_templates import list_templates
        templates = list_templates()
        assert "software_project" in templates
        assert "code_review" in templates
        assert "research" in templates

    def test_load_template(self):
        from backend.services.show_templates import load_template
        t = load_template("software_project")
        assert "movements" in t
        assert len(t["movements"]) > 0

    def test_load_nonexistent_template(self):
        from backend.services.show_templates import load_template
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent_xyz")

    def test_create_show_from_template(self, db):
        from backend.services.show_templates import create_show_from_template
        result = create_show_from_template(
            db, "software_project",
            title="My Project",
            params={"project_name": "TestApp"},
        )
        assert result["root_id"]
        assert result["coordinates"] > 1
        assert result["reps"] > 0

    def test_create_show_from_code_review_template(self, db):
        from backend.services.show_templates import create_show_from_template
        result = create_show_from_template(
            db, "code_review",
            params={"target": "auth module"},
        )
        assert result["coordinates"] > 1

    def test_interpolation(self):
        from backend.services.show_templates import _interpolate
        assert _interpolate("Hello {{name}}", {"name": "World"}) == "Hello World"
        assert _interpolate("No vars", {}) == "No vars"
        assert _interpolate("", {"key": "val"}) == ""


# --- Event Bus ---

class TestEventBus:
    def test_publish_subscribe(self):
        from backend.services.event_bus import EventBus
        bus = EventBus()
        received = []
        bus.subscribe("test.topic", lambda t, p: received.append((t, p)))
        bus.publish("test.topic", {"key": "value"})
        assert len(received) == 1
        assert received[0] == ("test.topic", {"key": "value"})

    def test_wildcard_subscriber(self):
        from backend.services.event_bus import EventBus
        bus = EventBus()
        received = []
        bus.subscribe("*", lambda t, p: received.append(t))
        bus.publish("a.topic")
        bus.publish("b.topic")
        assert len(received) == 2

    def test_unsubscribe(self):
        from backend.services.event_bus import EventBus
        bus = EventBus()
        received = []
        cb = lambda t, p: received.append(t)
        bus.subscribe("topic", cb)
        bus.publish("topic")
        assert len(received) == 1
        bus.unsubscribe("topic", cb)
        bus.publish("topic")
        assert len(received) == 1  # No new events

    def test_subscriber_error_doesnt_break_others(self):
        from backend.services.event_bus import EventBus
        bus = EventBus()
        received = []

        def bad_cb(t, p):
            raise RuntimeError("oops")

        bus.subscribe("topic", bad_cb)
        bus.subscribe("topic", lambda t, p: received.append(t))
        bus.publish("topic")
        assert len(received) == 1

    def test_topics_property(self):
        from backend.services.event_bus import EventBus
        bus = EventBus()
        bus.subscribe("a", lambda t, p: None)
        bus.subscribe("b", lambda t, p: None)
        assert set(bus.topics) == {"a", "b"}

    def test_singleton(self):
        from backend.services.event_bus import get_event_bus
        b1 = get_event_bus()
        b2 = get_event_bus()
        assert b1 is b2


# --- MCP Adapter ---

class TestMCPAdapter:
    def test_register_from_config(self):
        from backend.services.mcp_adapter import register_mcp_tools
        from backend.services.tool_executor import ToolRegistry
        registry = ToolRegistry()
        config = {
            "servers": {
                "test_server": {
                    "command": "echo test",
                    "tools": [
                        {"name": "do_thing", "roles": ["brass_tech"]},
                        {"name": "do_other", "roles": ["guard_tech"]},
                    ]
                }
            }
        }
        count = register_mcp_tools(registry, config)
        assert count == 2
        assert "test_server.do_thing" in registry._tools

    def test_empty_config(self):
        from backend.services.mcp_adapter import register_mcp_tools
        from backend.services.tool_executor import ToolRegistry
        registry = ToolRegistry()
        count = register_mcp_tools(registry, {})
        assert count == 0

    def test_proxy_execution(self):
        from backend.services.mcp_adapter import register_mcp_tools
        from backend.services.tool_executor import ToolRegistry
        registry = ToolRegistry()
        config = {
            "servers": {
                "gh": {
                    "command": "npx server",
                    "tools": [{"name": "list_issues", "roles": []}]
                }
            }
        }
        register_mcp_tools(registry, config)
        func = registry._tools["gh.list_issues"]
        result = func(None, repo="test/repo")
        assert result["server"] == "gh"
        assert result["tool"] == "list_issues"


# --- Dry Run ---

class TestDryRun:
    def test_dry_run_tool_executor(self):
        from backend.services.dry_run import DryRunToolExecutor
        executor = DryRunToolExecutor()
        r1 = executor.execute("create_coordinate", {"type": "movement", "title": "M1"})
        assert r1["status"] == "pending"
        assert r1["id"].startswith("dry-run-")

        r2 = executor.execute("create_rep", {"coordinate_id": "c1"})
        assert r2["status"] == "pending"

        assert len(executor.calls) == 2

    def test_dry_run_submit_work(self):
        from backend.services.dry_run import DryRunToolExecutor
        executor = DryRunToolExecutor()
        r = executor.execute("submit_work", {"rep_id": "r1", "result": "done"})
        assert r["status"] == "review"

    def test_dry_run_handoff(self):
        from backend.services.dry_run import DryRunToolExecutor
        executor = DryRunToolExecutor()
        r = executor.execute("handoff", {"from_role": "ed", "to_role": "pc"})
        assert r["status"] == "handed_off"

    def test_simulate_agent(self):
        from backend.services.dry_run import simulate_agent
        result = simulate_agent("executive_director", "Build a web app", system_prompt="You are the ED")
        assert result.role == "executive_director"
        assert "dry-run" in result.plan
        assert result.estimated_iterations > 0

    def test_dry_run_unknown_tool(self):
        from backend.services.dry_run import DryRunToolExecutor
        executor = DryRunToolExecutor()
        r = executor.execute("unknown_tool", {"foo": "bar"})
        assert r["dry_run"] is True
