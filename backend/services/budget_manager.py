"""Operating budget manager — tracks and enforces LLM spend limits.

Loads config from backend/config/budget.yaml with env var overrides.
Tracks spend per session, per corps, and per day. Provides gate checks
before spawning new agent sessions.
"""

import logging
import os
import threading
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from backend.services.yaml_util import safe_load_yaml_dict
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "budget.yaml"


@dataclass
class BudgetConfig:
    max_concurrent_processes: int = 5
    max_daily_spend_usd: float = 10.0
    max_session_spend_usd: float = 0.50
    max_agents_per_corps: int = 3
    max_daily_spend_per_corps_usd: float = 5.0
    provider_costs: dict = field(default_factory=dict)


@dataclass
class SpendRecord:
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    request_count: int = 0


class BudgetManager:
    """Thread-safe budget tracking and enforcement."""

    _instance: Optional["BudgetManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "BudgetManager":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._config = cls._load_config()
                inst._daily_spend = SpendRecord()
                inst._session_spend: dict[str, SpendRecord] = {}
                inst._corps_spend: dict[str, SpendRecord] = {}
                inst._spend_lock = threading.Lock()
                inst._current_day = datetime.now(timezone.utc).date()
                cls._instance = inst
        return cls._instance

    @staticmethod
    def _load_config() -> BudgetConfig:
        """Load from YAML, then apply env var overrides."""
        raw: dict = {}
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                raw = safe_load_yaml_dict(f.read())

        g = raw.get("global", {})
        c = raw.get("corps", {})

        config = BudgetConfig(
            max_concurrent_processes=int(os.environ.get(
                "DSI_MAX_CONCURRENT_PROCESSES",
                g.get("max_concurrent_processes", 5),
            )),
            max_daily_spend_usd=float(os.environ.get(
                "DSI_MAX_DAILY_SPEND_USD",
                g.get("max_daily_spend_usd", 10.0),
            )),
            max_session_spend_usd=float(os.environ.get(
                "DSI_MAX_SESSION_SPEND_USD",
                g.get("max_session_spend_usd", 0.50),
            )),
            max_agents_per_corps=int(os.environ.get(
                "DSI_MAX_AGENTS_PER_CORPS",
                c.get("max_agents_per_corps", 3),
            )),
            max_daily_spend_per_corps_usd=float(os.environ.get(
                "DSI_MAX_DAILY_SPEND_PER_CORPS_USD",
                c.get("max_daily_spend_per_corps_usd", 5.0),
            )),
            provider_costs=raw.get("provider_costs", {}),
        )
        logger.info(
            "Budget config loaded: daily=$%.2f, session=$%.2f, concurrent=%d",
            config.max_daily_spend_usd,
            config.max_session_spend_usd,
            config.max_concurrent_processes,
        )
        return config

    @property
    def config(self) -> BudgetConfig:
        return self._config

    def _maybe_reset_daily(self) -> None:
        """Reset daily counters if the day has changed."""
        today = datetime.now(timezone.utc).date()
        if today != self._current_day:
            with self._spend_lock:
                self._daily_spend = SpendRecord()
                self._corps_spend.clear()
                self._current_day = today
                logger.info("Budget daily reset for %s", today)

    def _estimate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate USD cost from token counts and provider rates."""
        rates = self._config.provider_costs.get(provider, {})
        if not rates:
            return 0.0
        input_rate = rates.get("input_per_1m", 0.0)
        output_rate = rates.get("output_per_1m", 0.0)
        return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000

    def can_start_session(self, session_id: str, corps_id: Optional[str] = None) -> tuple[bool, str]:
        """Check if a new session is allowed under budget constraints.

        Returns (allowed, reason).
        """
        self._maybe_reset_daily()

        with self._spend_lock:
            # Daily global limit
            if self._daily_spend.estimated_cost_usd >= self._config.max_daily_spend_usd:
                return False, f"Daily budget exhausted (${self._daily_spend.estimated_cost_usd:.2f}/${self._config.max_daily_spend_usd:.2f})"

            # Per-corps daily limit
            if corps_id:
                corps_rec = self._corps_spend.get(corps_id, SpendRecord())
                if corps_rec.estimated_cost_usd >= self._config.max_daily_spend_per_corps_usd:
                    return False, f"Corps daily budget exhausted (${corps_rec.estimated_cost_usd:.2f}/${self._config.max_daily_spend_per_corps_usd:.2f})"

        return True, "ok"

    def record_spend(
        self,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        session_id: Optional[str] = None,
        corps_id: Optional[str] = None,
    ) -> float:
        """Record token usage after an LLM call. Returns estimated cost."""
        self._maybe_reset_daily()
        cost = self._estimate_cost(provider, input_tokens, output_tokens)

        with self._spend_lock:
            # Global daily
            self._daily_spend.input_tokens += input_tokens
            self._daily_spend.output_tokens += output_tokens
            self._daily_spend.estimated_cost_usd += cost
            self._daily_spend.request_count += 1

            # Per-session
            if session_id:
                rec = self._session_spend.setdefault(session_id, SpendRecord())
                rec.input_tokens += input_tokens
                rec.output_tokens += output_tokens
                rec.estimated_cost_usd += cost
                rec.request_count += 1

            # Per-corps
            if corps_id:
                rec = self._corps_spend.setdefault(corps_id, SpendRecord())
                rec.input_tokens += input_tokens
                rec.output_tokens += output_tokens
                rec.estimated_cost_usd += cost
                rec.request_count += 1

        return cost

    def session_over_budget(self, session_id: str) -> bool:
        """Check if a session has exceeded its per-session budget."""
        with self._spend_lock:
            rec = self._session_spend.get(session_id)
            if not rec:
                return False
            return rec.estimated_cost_usd >= self._config.max_session_spend_usd

    def get_stats(self) -> dict:
        """Return budget status for API exposure."""
        self._maybe_reset_daily()
        from dataclasses import asdict

        with self._spend_lock:
            top_corps = sorted(
                self._corps_spend.items(),
                key=lambda x: x[1].estimated_cost_usd,
                reverse=True,
            )[:10]

            return {
                "config": {
                    "max_daily_spend_usd": self._config.max_daily_spend_usd,
                    "max_session_spend_usd": self._config.max_session_spend_usd,
                    "max_concurrent_processes": self._config.max_concurrent_processes,
                    "max_agents_per_corps": self._config.max_agents_per_corps,
                    "max_daily_spend_per_corps_usd": self._config.max_daily_spend_per_corps_usd,
                },
                "daily": asdict(self._daily_spend),
                "daily_remaining_usd": max(0, self._config.max_daily_spend_usd - self._daily_spend.estimated_cost_usd),
                "active_sessions": len(self._session_spend),
                "top_corps_spend": [
                    {"corps_id": cid, **asdict(rec)} for cid, rec in top_corps
                ],
                "date": str(self._current_day),
            }


def get_budget_manager() -> BudgetManager:
    return BudgetManager()
