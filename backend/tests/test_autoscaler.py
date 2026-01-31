"""Tests for autoscaler."""

import asyncio
from backend.services.autoscaler import AutoScaler, ScaleConfig


class TestAutoScaler:
    def test_initial_config(self):
        scaler = AutoScaler(ScaleConfig(base_concurrency=3))
        assert scaler.current_limit == 3
        assert scaler.active_count == 0

    def test_acquire_release(self):
        scaler = AutoScaler(ScaleConfig(base_concurrency=2))
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(scaler.acquire("s1"))
            assert scaler.active_count == 1
            scaler.release("s1")
            assert scaler.active_count == 0
        finally:
            loop.close()

    def test_stats(self):
        scaler = AutoScaler(ScaleConfig(base_concurrency=5))
        stats = scaler.get_stats()
        assert stats["current_limit"] == 5
        assert stats["active_count"] == 0
        assert stats["waiting_count"] == 0

    def test_adjust_limits_no_psutil(self):
        scaler = AutoScaler(ScaleConfig(base_concurrency=5))
        result = scaler.adjust_limits()
        # Should return current limit even if psutil not installed
        assert result >= 1
