"""Event bus — simple pub/sub for internal domain events.

Topics: rep.status_changed, segment.completed, agent.phase_changed,
performer.trust_changed, show.completed, etc.

Subscribers are plain callables; they receive (topic, payload) args.
"""

import logging
from collections import defaultdict
from typing import Callable, Any

logger = logging.getLogger(__name__)

Subscriber = Callable[[str, dict[str, Any]], None]


class EventBus:
    """In-process pub/sub event bus."""

    def __init__(self):
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)

    def subscribe(self, topic: str, callback: Subscriber) -> None:
        """Subscribe to a topic."""
        self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Subscriber) -> None:
        """Remove a subscription."""
        try:
            self._subscribers[topic].remove(callback)
        except ValueError:
            pass

    def publish(self, topic: str, payload: dict[str, Any] | None = None) -> None:
        """Publish an event to all subscribers of a topic."""
        payload = payload or {}
        for callback in self._subscribers.get(topic, []):
            try:
                callback(topic, payload)
            except Exception:
                logger.exception("Event subscriber error on topic %s", topic)

        # Also notify wildcard subscribers
        for callback in self._subscribers.get("*", []):
            try:
                callback(topic, payload)
            except Exception:
                logger.exception("Wildcard subscriber error on topic %s", topic)

    @property
    def topics(self) -> list[str]:
        """List topics with active subscribers."""
        return [t for t, subs in self._subscribers.items() if subs]


# Module-level singleton
_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
