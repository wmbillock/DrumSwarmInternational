"""AutoScaler — dynamic concurrency limits for agent tasks.

Uses asyncio.Semaphore-based limiter with priority queue.
Adjusts limits based on system resource usage via psutil (optional).
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScaleConfig:
    """Configuration for the autoscaler."""
    base_concurrency: int = 5
    max_concurrency: int = 20
    min_concurrency: int = 1
    cpu_high_watermark: float = 80.0  # percent
    cpu_low_watermark: float = 40.0
    memory_high_watermark: float = 85.0  # percent


# Priority levels for agents (lower number = higher priority)
from backend.models.agent_definition import ModelTier

TIER_PRIORITY = {
    ModelTier.OPUS: 0,
    ModelTier.SONNET: 1,
    ModelTier.HAIKU: 2,
}


class AutoScaler:
    """Dynamic concurrency limiter for background agent tasks."""

    def __init__(self, config: Optional[ScaleConfig] = None):
        self.config = config or ScaleConfig()
        self._current_limit = self.config.base_concurrency
        self._semaphore = asyncio.Semaphore(self._current_limit)
        self._active_count = 0
        self._waiting: list[tuple[int, asyncio.Event, str]] = []  # (priority, event, session_id)

    @property
    def current_limit(self) -> int:
        return self._current_limit

    @property
    def active_count(self) -> int:
        return self._active_count

    async def acquire(self, session_id: str, model_tier: str = ModelTier.HAIKU) -> None:
        """Acquire a slot, waiting if at capacity. Higher-tier agents get priority."""
        priority = TIER_PRIORITY.get(model_tier, 2)

        if self._active_count < self._current_limit:
            self._active_count += 1
            return

        # Wait in priority queue
        event = asyncio.Event()
        entry = (priority, event, session_id)
        self._waiting.append(entry)
        self._waiting.sort(key=lambda x: x[0])  # Sort by priority
        await event.wait()
        self._active_count += 1

    def release(self, session_id: str) -> None:
        """Release a slot and wake the highest-priority waiter."""
        self._active_count = max(0, self._active_count - 1)

        if self._waiting:
            _, event, _ = self._waiting.pop(0)
            event.set()

    def adjust_limits(self) -> int:
        """Adjust concurrency limits based on system resources and budget. Returns new limit."""
        # Apply budget-based cap
        try:
            from backend.services.budget_manager import get_budget_manager
            budget_cap = get_budget_manager().config.max_concurrent_processes
            if budget_cap < self.config.max_concurrency:
                self.config.max_concurrency = budget_cap
        except Exception:
            pass

        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().percent

            if cpu > self.config.cpu_high_watermark or mem > self.config.memory_high_watermark:
                new_limit = max(self.config.min_concurrency, self._current_limit - 1)
                if new_limit != self._current_limit:
                    logger.info("AutoScaler: reducing limit %d -> %d (cpu=%.0f%%, mem=%.0f%%)",
                                self._current_limit, new_limit, cpu, mem)
                    self._current_limit = new_limit
            elif cpu < self.config.cpu_low_watermark and self._current_limit < self.config.max_concurrency:
                new_limit = min(self.config.max_concurrency, self._current_limit + 1)
                if new_limit != self._current_limit:
                    logger.info("AutoScaler: increasing limit %d -> %d (cpu=%.0f%%, mem=%.0f%%)",
                                self._current_limit, new_limit, cpu, mem)
                    self._current_limit = new_limit
        except ImportError:
            pass  # psutil not installed, keep current limits
        except Exception:
            logger.exception("AutoScaler: error adjusting limits")

        # Check process registry threshold
        try:
            from backend.services.process_registry import get_process_registry
            warning = get_process_registry().check_threshold()
            if warning:
                logger.warning("AutoScaler: %s", warning)
        except Exception:
            pass

        return self._current_limit

    def get_stats(self) -> dict:
        """Return current autoscaler stats."""
        return {
            "current_limit": self._current_limit,
            "active_count": self._active_count,
            "waiting_count": len(self._waiting),
        }
