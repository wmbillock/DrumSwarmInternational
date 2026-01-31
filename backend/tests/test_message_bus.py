"""Tests for message bus pub/sub."""

from backend.services.message_bus import (
    MessageBus, RepStatusChanged, SegmentCompleted,
    AgentPhaseChanged, AgentCompleted, VerificationFailed,
)


class TestMessageBus:
    def test_subscribe_and_publish(self):
        bus = MessageBus()
        received = []
        bus.subscribe("rep.status_changed", received.append)
        msg = RepStatusChanged(rep_id="r1", old_status="pending", new_status="assigned", segment_id="c1")
        bus.publish("rep.status_changed", msg)
        assert len(received) == 1
        assert received[0].rep_id == "r1"

    def test_multiple_subscribers(self):
        bus = MessageBus()
        r1, r2 = [], []
        bus.subscribe("test", r1.append)
        bus.subscribe("test", r2.append)
        bus.publish("test", "hello")
        assert r1 == ["hello"]
        assert r2 == ["hello"]

    def test_different_topics_isolated(self):
        bus = MessageBus()
        received = []
        bus.subscribe("topic_a", received.append)
        bus.publish("topic_b", "should not arrive")
        assert len(received) == 0

    def test_unsubscribe(self):
        bus = MessageBus()
        received = []
        bus.subscribe("test", received.append)
        bus.unsubscribe("test", received.append)
        bus.publish("test", "nope")
        assert len(received) == 0

    def test_clear(self):
        bus = MessageBus()
        bus.subscribe("a", lambda x: None)
        bus.subscribe("b", lambda x: None)
        bus.clear()
        assert len(bus.topics) == 0

    def test_error_in_subscriber_doesnt_break_others(self):
        bus = MessageBus()
        received = []
        def bad_callback(msg):
            raise ValueError("boom")
        bus.subscribe("test", bad_callback)
        bus.subscribe("test", received.append)
        bus.publish("test", "data")
        assert received == ["data"]

    def test_typed_messages(self):
        bus = MessageBus()
        received = []
        bus.subscribe("segment.completed", received.append)
        msg = SegmentCompleted(segment_id="c1", parent_id="p1", corps_id="corp1")
        bus.publish("segment.completed", msg)
        assert received[0].segment_id == "c1"

    def test_topics_property(self):
        bus = MessageBus()
        assert bus.topics == []
        bus.subscribe("a", lambda x: None)
        assert "a" in bus.topics
