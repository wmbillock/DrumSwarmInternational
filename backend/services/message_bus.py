"""Message bus (pub/sub) — in-process event-driven reactivity.

Typed topics with dataclass messages. Subscribers register callbacks;
bus triggers actions like agent wake-ups via TaskManager.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# --- Typed Messages ---

@dataclass
class RepStatusChanged:
    rep_id: str
    old_status: str
    new_status: str
    coordinate_id: str
    session_id: Optional[str] = None


@dataclass
class CoordinateCompleted:
    coordinate_id: str
    parent_id: Optional[str] = None
    corps_id: Optional[str] = None


@dataclass
class AgentPhaseChanged:
    session_id: str
    role: str
    old_phase: str
    new_phase: str
    corps_id: Optional[str] = None


@dataclass
class AgentCompleted:
    session_id: str
    role: str
    status: str
    corps_id: Optional[str] = None


@dataclass
class VerificationFailed:
    rep_id: str
    coordinate_id: str
    failed_gates: list[str] = field(default_factory=list)
    corps_id: Optional[str] = None


# Topic names
TOPICS = {
    "rep.status_changed": RepStatusChanged,
    "coordinate.completed": CoordinateCompleted,
    "agent.phase_changed": AgentPhaseChanged,
    "agent.completed": AgentCompleted,
    "verification.failed": VerificationFailed,
}


class MessageBus:
    """In-process pub/sub message bus with typed topics."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, topic: str, callback: Callable) -> None:
        """Register a callback for a topic."""
        self._subscribers.setdefault(topic, []).append(callback)

    def unsubscribe(self, topic: str, callback: Callable) -> None:
        """Remove a callback from a topic."""
        subs = self._subscribers.get(topic, [])
        if callback in subs:
            subs.remove(callback)

    def publish(self, topic: str, message: Any) -> None:
        """Publish a message to all subscribers of a topic."""
        for callback in self._subscribers.get(topic, []):
            try:
                callback(message)
            except Exception:
                logger.exception("Error in message bus subscriber for topic '%s'", topic)

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._subscribers.clear()

    @property
    def topics(self) -> list[str]:
        """List topics with active subscribers."""
        return [t for t, subs in self._subscribers.items() if subs]


# Global bus instance
_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Get or create the global message bus."""
    global _bus
    if _bus is None:
        _bus = MessageBus()
    return _bus
