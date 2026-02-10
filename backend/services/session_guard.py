"""RAII guard for agent sessions — unique_ptr semantics.

Guarantees session cleanup on exit, whether normal completion, exception,
or parent session death. Children cascade-killed when parent guard exits.

Usage:
    async with AgentSessionGuard(db, session_id, task_manager) as guard:
        result = run_agent(db, session_id, ...)
        guard.result = result

Or synchronously:
    with SyncSessionGuard(db, session_id) as guard:
        result = run_agent(db, session_id, ...)
"""

import logging
import threading
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.agent_session import AgentSession, SessionStatus

logger = logging.getLogger(__name__)


class _GuardMetrics:
    """Thread-safe singleton tracking session guard activity."""

    _instance: Optional["_GuardMetrics"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "_GuardMetrics":
        with cls._lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._counters_lock = threading.Lock()
                obj.sync_guard_activations = 0
                obj.async_guard_activations = 0
                obj.total_cascades = 0
                obj.total_children_cascaded = 0
                obj.unhandled_exceptions_caught = 0
                cls._instance = obj
        return cls._instance

    def record_sync_activation(self) -> None:
        with self._counters_lock:
            self.sync_guard_activations += 1

    def record_async_activation(self) -> None:
        with self._counters_lock:
            self.async_guard_activations += 1

    def record_cascade(self, children_count: int) -> None:
        with self._counters_lock:
            self.total_cascades += 1
            self.total_children_cascaded += children_count

    def record_unhandled_exception(self) -> None:
        with self._counters_lock:
            self.unhandled_exceptions_caught += 1

    def get_stats(self) -> dict:
        with self._counters_lock:
            return {
                "sync_guard_activations": self.sync_guard_activations,
                "async_guard_activations": self.async_guard_activations,
                "total_cascades": self.total_cascades,
                "total_children_cascaded": self.total_children_cascaded,
                "unhandled_exceptions_caught": self.unhandled_exceptions_caught,
            }


def get_guard_metrics() -> _GuardMetrics:
    return _GuardMetrics()


def cascade_fail_children(db: Session, parent_session_id: str, error: str = "parent session terminated") -> int:
    """Transition all ACTIVE child sessions to FAILED when parent dies.

    Returns the number of children cascade-failed.
    """
    from backend.services.agent_lifecycle import fail_session, InvalidSessionTransition

    children = (
        db.query(AgentSession)
        .filter(
            AgentSession.parent_session_id == parent_session_id,
            AgentSession.status == SessionStatus.ACTIVE,
        )
        .all()
    )

    count = 0
    for child in children:
        try:
            fail_session(db, child.id, error=error)
            count += 1
            logger.info("Cascade-failed child session %s (parent: %s)", child.id, parent_session_id)
            # Recurse: cascade to grandchildren
            count += cascade_fail_children(db, child.id, error=error)
        except InvalidSessionTransition:
            pass  # Already in terminal state
        except Exception:
            logger.warning("Failed to cascade-fail child session %s", child.id, exc_info=True)

    return count


class SyncSessionGuard:
    """Synchronous RAII guard for agent sessions.

    Used in run_agent() to guarantee cleanup even on crash.
    """

    def __init__(self, db: Session, session_id: str, cascade_children: bool = True):
        self.db = db
        self.session_id = session_id
        self.cascade_children = cascade_children
        self._completed = False
        self._failed = False

    def __enter__(self):
        return self

    def mark_completed(self):
        """Mark that the session was handled (completed or failed) by the caller."""
        self._completed = True

    def mark_failed(self):
        """Mark that the session was handled as failed by the caller."""
        self._failed = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        from backend.services.agent_lifecycle import fail_session, InvalidSessionTransition

        # If caller already handled the session, just cascade children on failure
        if self._completed:
            return False

        metrics = get_guard_metrics()

        # If there was an unhandled exception and session wasn't already terminated
        if exc_type is not None and not self._failed:
            metrics.record_unhandled_exception()
            metrics.record_sync_activation()
            try:
                session = self.db.get(AgentSession, self.session_id)
                if session and session.status == SessionStatus.ACTIVE:
                    error_msg = f"Unhandled exception: {exc_type.__name__}: {exc_val}"
                    fail_session(self.db, self.session_id, error=error_msg[:2000])
                    logger.warning("Session guard caught unhandled exception for %s: %s", self.session_id, error_msg)
            except InvalidSessionTransition:
                pass  # Already in terminal state
            except Exception:
                logger.warning("Session guard cleanup failed for %s", self.session_id, exc_info=True)

        # Cascade-fail children if parent is dying
        if self.cascade_children and (exc_type is not None or self._failed):
            try:
                count = cascade_fail_children(self.db, self.session_id)
                if count > 0:
                    metrics.record_cascade(count)
                    logger.info("Cascade-failed %d children of session %s", count, self.session_id)
            except Exception:
                logger.warning("Child cascade failed for session %s", self.session_id, exc_info=True)

        # Don't suppress exceptions
        return False


class AsyncSessionGuard:
    """Async RAII guard for agent sessions.

    Used in TaskManager._run_agent_task() for async context.
    """

    def __init__(
        self,
        db: Session,
        session_id: str,
        task_manager: Optional[object] = None,
        cascade_children: bool = True,
    ):
        self.db = db
        self.session_id = session_id
        self.task_manager = task_manager
        self.cascade_children = cascade_children
        self._completed = False
        self._failed = False

    async def __aenter__(self):
        return self

    def mark_completed(self):
        self._completed = True

    def mark_failed(self):
        self._failed = True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        import asyncio
        from backend.services.agent_lifecycle import fail_session, InvalidSessionTransition

        if self._completed:
            return False

        metrics = get_guard_metrics()

        if exc_type is not None and not self._failed:
            metrics.record_unhandled_exception()
            metrics.record_async_activation()
            try:
                def _fail():
                    session = self.db.get(AgentSession, self.session_id)
                    if session and session.status == SessionStatus.ACTIVE:
                        error_msg = f"Unhandled exception: {exc_type.__name__}: {exc_val}"
                        fail_session(self.db, self.session_id, error=error_msg[:2000])

                await asyncio.to_thread(_fail)
            except InvalidSessionTransition:
                pass
            except Exception:
                logger.warning("Async session guard cleanup failed for %s", self.session_id, exc_info=True)

        # Cascade-fail children
        if self.cascade_children and (exc_type is not None or self._failed):
            try:
                def _cascade():
                    return cascade_fail_children(self.db, self.session_id)

                count = await asyncio.to_thread(_cascade)
                if count > 0:
                    metrics.record_cascade(count)
                    logger.info("Cascade-failed %d children of session %s", count, self.session_id)
            except Exception:
                logger.warning("Async child cascade failed for %s", self.session_id, exc_info=True)

        # Cancel child asyncio tasks if task_manager is available
        if self.task_manager and (exc_type is not None or self._failed):
            try:
                _cancel_child_tasks(self.db, self.session_id, self.task_manager)
            except Exception:
                logger.warning("Failed to cancel child tasks for %s", self.session_id, exc_info=True)

        return False


def _cancel_child_tasks(db: Session, parent_session_id: str, task_manager) -> int:
    """Cancel asyncio tasks for child sessions in the task manager."""
    children = (
        db.query(AgentSession)
        .filter(AgentSession.parent_session_id == parent_session_id)
        .all()
    )

    cancelled = 0
    for child in children:
        if hasattr(task_manager, 'active_tasks'):
            task = task_manager.active_tasks.get(child.id)
            if task and not task.done():
                task.cancel()
                cancelled += 1
                logger.info("Cancelled asyncio task for child session %s", child.id)
        # Recurse
        cancelled += _cancel_child_tasks(db, child.id, task_manager)

    return cancelled
