"""Tests for the lifecycle tour demo."""

from backend.scripts.tour_demo import run_tour


class TestFullLifecyclePath:
    def test_full_lifecycle_path(self, tmp_path):
        summary = run_tour(tmp_path)

        # Both agents were drafted
        assert "agent-alpha" in summary["drafted"]
        assert "agent-beta" in summary["drafted"]

        # Trust changed after update (both have >= threshold sessions)
        assert summary["alpha_trust_after_update"] != 70.0
        assert summary["beta_trust_after_update"] != 60.0

        # Sessions incremented (alpha started at 5, beta at 5)
        assert summary["alpha_sessions"] == 6
        assert summary["beta_sessions"] == 6

        # Agents released back to active
        assert summary["alpha_availability"] == "active"
        assert summary["beta_availability"] == "active"

        # Decay was applied (final trust differs from post-update trust)
        assert summary["alpha_trust_final"] != summary["alpha_trust_after_update"]
        assert summary["beta_trust_final"] != summary["beta_trust_after_update"]
