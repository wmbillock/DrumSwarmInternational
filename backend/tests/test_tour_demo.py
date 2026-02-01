"""Tests for the lifecycle tour demo."""

import yaml

from backend.scripts.tour_demo import run_deterministic_tour


class TestFullLifecyclePath:
    def test_full_lifecycle_path(self, tmp_path):
        recap = run_deterministic_tour(tmp_path, seed=1, seasons=1, corps_count=2)

        # Recap is a non-empty string
        assert "Tour Recap" in recap
        assert "Final Agent Trust Scores" in recap

        # Pool, corps, season artifacts all created
        pool_dir = tmp_path / "talent_pool"
        assert (pool_dir / "ledger.yaml").is_file()
        agent_files = list((pool_dir / "agents").glob("*.yaml"))
        assert len(agent_files) == 10  # 2 corps * 5 instruments

        # Corps created, drafted, have history
        corps_dirs = [d for d in (tmp_path / "corps").iterdir() if d.is_dir()]
        assert len(corps_dirs) == 2
        for cd in corps_dirs:
            corps_data = yaml.safe_load((cd / "corps.yaml").read_text())
            assert len(corps_data["history"]) >= 1
            roster = yaml.safe_load((cd / "roster.yaml").read_text())
            assert len(roster["assignments"]) == 5

        # Standings written
        standings = yaml.safe_load(
            (tmp_path / "seasons" / "tour-s1" / "standings.yaml").read_text()
        )
        assert len(standings["results"]) == 2

        # Agents released back to active after tour
        for af in agent_files:
            agent = yaml.safe_load(af.read_text())
            assert agent["availability"] == "active"

        # Recap artifact written
        assert (tmp_path / "docs" / "outputs" / "tour_seed1.md").is_file()

    def test_multi_season_decay(self, tmp_path):
        """With 2 seasons, decay is applied between them."""
        recap = run_deterministic_tour(tmp_path, seed=1, seasons=2, corps_count=2)
        assert "decay" in recap.lower()

        # Both seasons have standings
        assert (tmp_path / "seasons" / "tour-s1" / "standings.yaml").is_file()
        assert (tmp_path / "seasons" / "tour-s2" / "standings.yaml").is_file()

        # Agents have 2 sessions (one per season)
        for af in (tmp_path / "talent_pool" / "agents").glob("*.yaml"):
            agent = yaml.safe_load(af.read_text())
            # Only agents that were drafted get sessions; all should have been drafted
            if agent["total_sessions"] > 0:
                assert agent["total_sessions"] == 2
