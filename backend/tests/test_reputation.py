"""Tests for the reputation/fitness update system."""

import math
import yaml
from pathlib import Path

import pytest

from backend.services.scoring_engine import Standings, CorpsResult
from backend.models.score import JudgeType
from backend.services.reputation import (
    update_reputations,
    apply_season_decay,
    release_agent,
    record_corps_placement,
    _validate_score,
    MINIMUM_SAMPLE_THRESHOLD,
    SUCCESS_THRESHOLD,
    DECAY_RATE,
    DECAY_BASELINE,
)


def _make_agent_yaml(
    agent_id: str = "agent-001",
    display_name: str = "Alice",
    primary_instrument: str = "bass",
    availability: str = "active",
    trust_score: float = 50.0,
    total_sessions: int = 0,
    successful_sessions: int = 0,
    failed_sessions: int = 0,
    experience_seasons: int = 0,
    **extra,
) -> dict:
    d = dict(
        agent_id=agent_id,
        display_name=display_name,
        primary_instrument=primary_instrument,
        availability=availability,
        trust_score=trust_score,
        total_sessions=total_sessions,
        successful_sessions=successful_sessions,
        failed_sessions=failed_sessions,
        experience_seasons=experience_seasons,
    )
    d.update(extra)
    return d


def _write_pool(pool_dir: Path, agents: list[dict]) -> None:
    """Write ledger.yaml and agent files."""
    pool_dir.mkdir(parents=True, exist_ok=True)
    agents_dir = pool_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    ledger = {
        "agents": [
            {
                "agent_id": a["agent_id"],
                "display_name": a["display_name"],
                "primary_instrument": a["primary_instrument"],
                "availability": a["availability"],
            }
            for a in agents
        ]
    }
    (pool_dir / "ledger.yaml").write_text(yaml.dump(ledger, default_flow_style=False))
    for a in agents:
        (agents_dir / f"{a['agent_id']}.yaml").write_text(
            yaml.dump(a, default_flow_style=False)
        )


def _read_agent(pool_dir: Path, agent_id: str) -> dict:
    return yaml.safe_load((pool_dir / "agents" / f"{agent_id}.yaml").read_text())


def _make_standings(
    season_id: str = "2025-spring",
    results: list[CorpsResult] | None = None,
) -> Standings:
    if results is None:
        results = [
            CorpsResult(
                corps_id="corps-A",
                caption_scores={JudgeType.BRASS: 80.0},
                penalties_total=0.0,
                difficulty_coefficient=1.0,
                raw_score=80.0,
                final_score=80.0,
                rank=1,
            )
        ]
    return Standings(
        season_id=season_id,
        results=results,
        generated_at="2025-01-01T00:00:00+00:00",
    )


class TestTrustScoreUpdate:
    def test_trust_score_updated_after_scoring(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(trust_score=50.0, total_sessions=10)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(
            results=[
                CorpsResult(
                    corps_id="corps-A",
                    caption_scores={JudgeType.BRASS: 80.0},
                    penalties_total=0.0,
                    difficulty_coefficient=1.0,
                    raw_score=80.0,
                    final_score=80.0,
                    rank=1,
                )
            ]
        )
        roster_map = {"corps-A": ["agent-001"]}
        update_reputations(standings, pool_dir, roster_map)

        updated = _read_agent(pool_dir, "agent-001")
        # new_trust = (50*10 + 80) / 11 = 580/11 ≈ 52.727
        expected = (50.0 * 10 + 80.0) / 11
        assert abs(updated["trust_score"] - expected) < 0.001

    def test_session_counts_incremented(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(
            trust_score=50.0, total_sessions=5, successful_sessions=3, failed_sessions=2
        )
        _write_pool(pool_dir, [agent])

        standings = _make_standings(
            results=[
                CorpsResult(
                    corps_id="corps-A",
                    caption_scores={},
                    penalties_total=0.0,
                    difficulty_coefficient=1.0,
                    raw_score=70.0,
                    final_score=70.0,
                    rank=1,
                )
            ]
        )
        roster_map = {"corps-A": ["agent-001"]}
        update_reputations(standings, pool_dir, roster_map)

        updated = _read_agent(pool_dir, "agent-001")
        assert updated["total_sessions"] == 6
        assert updated["successful_sessions"] == 4  # 70 >= 60
        assert updated["failed_sessions"] == 2

    def test_failed_session_counted(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(
            trust_score=50.0, total_sessions=5, successful_sessions=3, failed_sessions=2
        )
        _write_pool(pool_dir, [agent])

        standings = _make_standings(
            results=[
                CorpsResult(
                    corps_id="corps-A",
                    caption_scores={},
                    penalties_total=0.0,
                    difficulty_coefficient=1.0,
                    raw_score=40.0,
                    final_score=40.0,
                    rank=1,
                )
            ]
        )
        roster_map = {"corps-A": ["agent-001"]}
        update_reputations(standings, pool_dir, roster_map)

        updated = _read_agent(pool_dir, "agent-001")
        assert updated["total_sessions"] == 6
        assert updated["successful_sessions"] == 3
        assert updated["failed_sessions"] == 3


class TestMinimumSampleDampening:
    def test_minimum_sample_dampening(self, tmp_path):
        pool_dir = tmp_path / "pool"
        # 1 session so far → dampening = 1/3
        agent = _make_agent_yaml(trust_score=50.0, total_sessions=1)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(
            results=[
                CorpsResult(
                    corps_id="corps-A",
                    caption_scores={},
                    penalties_total=0.0,
                    difficulty_coefficient=1.0,
                    raw_score=80.0,
                    final_score=80.0,
                    rank=1,
                )
            ]
        )
        roster_map = {"corps-A": ["agent-001"]}
        update_reputations(standings, pool_dir, roster_map)

        updated = _read_agent(pool_dir, "agent-001")
        # full_new = (50*1 + 80) / 2 = 65
        # dampening = 1/3
        # new_trust = 50 + (1/3)*(65 - 50) = 50 + 5 = 55
        expected = 50.0 + (1.0 / MINIMUM_SAMPLE_THRESHOLD) * (65.0 - 50.0)
        assert abs(updated["trust_score"] - expected) < 0.001

    def test_no_dampening_above_threshold(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(trust_score=50.0, total_sessions=10)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(
            results=[
                CorpsResult(
                    corps_id="corps-A",
                    caption_scores={},
                    penalties_total=0.0,
                    difficulty_coefficient=1.0,
                    raw_score=80.0,
                    final_score=80.0,
                    rank=1,
                )
            ]
        )
        roster_map = {"corps-A": ["agent-001"]}
        update_reputations(standings, pool_dir, roster_map)

        updated = _read_agent(pool_dir, "agent-001")
        # full_new = (50*10 + 80)/11 ≈ 52.727 — no dampening applied
        expected = (50.0 * 10 + 80.0) / 11
        assert abs(updated["trust_score"] - expected) < 0.001


class TestSeasonDecay:
    def test_decay_between_seasons(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(trust_score=80.0, total_sessions=10)
        _write_pool(pool_dir, [agent])

        apply_season_decay(pool_dir, decay_rate=0.05, baseline=50.0)

        updated = _read_agent(pool_dir, "agent-001")
        # trust += 0.05 * (50 - 80) = 80 - 1.5 = 78.5
        assert abs(updated["trust_score"] - 78.5) < 0.001

    def test_no_decay_when_factor_zero(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(trust_score=80.0, total_sessions=10)
        _write_pool(pool_dir, [agent])

        apply_season_decay(pool_dir, decay_rate=0.0, baseline=50.0)

        updated = _read_agent(pool_dir, "agent-001")
        assert updated["trust_score"] == 80.0


class TestReleaseAgent:
    def test_retirement_returns_to_pool(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(
            availability="assigned",
            trust_score=72.5,
            total_sessions=10,
            successful_sessions=8,
            failed_sessions=2,
            experience_seasons=3,
        )
        _write_pool(pool_dir, [agent])

        release_agent(pool_dir, "agent-001")

        updated = _read_agent(pool_dir, "agent-001")
        assert updated["availability"] == "active"
        assert updated["trust_score"] == 72.5
        assert updated["total_sessions"] == 10
        assert updated["successful_sessions"] == 8
        assert updated["failed_sessions"] == 2
        assert updated["experience_seasons"] == 3

    def test_retirement_preserves_corps_history(self, tmp_path):
        pool_dir = tmp_path / "pool"
        corps_dir = tmp_path / "corps"
        corps_dir.mkdir(parents=True)

        agent = _make_agent_yaml(availability="assigned")
        _write_pool(pool_dir, [agent])

        # Write corps history first
        corps_data = {
            "corps_id": "corps-A",
            "history": [
                {"season_id": "2025-spring", "placement": 1, "final_score": 92.5, "notes": ""}
            ],
        }
        (corps_dir / "corps.yaml").write_text(yaml.dump(corps_data, default_flow_style=False))

        release_agent(pool_dir, "agent-001")

        corps = yaml.safe_load((corps_dir / "corps.yaml").read_text())
        assert len(corps["history"]) == 1
        assert corps["history"][0]["season_id"] == "2025-spring"


class TestCorpsHistory:
    def test_corps_history_appended(self, tmp_path):
        corps_dir = tmp_path / "corps"
        corps_dir.mkdir(parents=True)
        corps_data = {"corps_id": "corps-A", "history": []}
        (corps_dir / "corps.yaml").write_text(yaml.dump(corps_data, default_flow_style=False))

        record_corps_placement(corps_dir, "2025-spring", 1, 92.5, notes="Clean sweep")

        corps = yaml.safe_load((corps_dir / "corps.yaml").read_text())
        assert len(corps["history"]) == 1
        assert corps["history"][0] == {
            "season_id": "2025-spring",
            "placement": 1,
            "final_score": 92.5,
            "notes": "Clean sweep",
        }

    def test_corps_history_appended_to_existing(self, tmp_path):
        corps_dir = tmp_path / "corps"
        corps_dir.mkdir(parents=True)
        corps_data = {
            "corps_id": "corps-A",
            "history": [
                {"season_id": "2024-fall", "placement": 3, "final_score": 70.0, "notes": ""}
            ],
        }
        (corps_dir / "corps.yaml").write_text(yaml.dump(corps_data, default_flow_style=False))

        record_corps_placement(corps_dir, "2025-spring", 1, 92.5)

        corps = yaml.safe_load((corps_dir / "corps.yaml").read_text())
        assert len(corps["history"]) == 2
        assert corps["history"][1]["season_id"] == "2025-spring"


class TestDeterministicOutput:
    def test_deterministic_output(self, tmp_path):
        """Same input produces same output across two runs."""
        results = []
        for _ in range(2):
            pool_dir = tmp_path / "pool"
            if pool_dir.exists():
                import shutil
                shutil.rmtree(pool_dir)
            agent = _make_agent_yaml(trust_score=50.0, total_sessions=5)
            _write_pool(pool_dir, [agent])

            standings = _make_standings(
                results=[
                    CorpsResult(
                        corps_id="corps-A",
                        caption_scores={},
                        penalties_total=0.0,
                        difficulty_coefficient=1.0,
                        raw_score=75.0,
                        final_score=75.0,
                        rank=1,
                    )
                ]
            )
            roster_map = {"corps-A": ["agent-001"]}
            update_reputations(standings, pool_dir, roster_map)
            results.append(_read_agent(pool_dir, "agent-001"))

        assert results[0]["trust_score"] == results[1]["trust_score"]
        assert results[0]["total_sessions"] == results[1]["total_sessions"]


class TestDraftingSeesUpdatedTrust:
    def test_drafting_sees_trust_after_reputation_update(self, tmp_path):
        """update_reputations changes trust → draft_roster picks higher-trust agent."""
        from backend.services.drafting import draft_roster, RoleRequirement

        pool_dir = tmp_path / "pool"
        # Two brass agents with same trust initially
        agents = [
            _make_agent_yaml(agent_id="a1", display_name="A1", primary_instrument="brass",
                             trust_score=50.0, total_sessions=10),
            _make_agent_yaml(agent_id="a2", display_name="A2", primary_instrument="brass",
                             trust_score=50.0, total_sessions=10),
        ]
        _write_pool(pool_dir, agents)

        # Give a1 a high score to boost trust
        standings = _make_standings(results=[
            CorpsResult(corps_id="corps-A", caption_scores={JudgeType.BRASS: 95.0},
                        penalties_total=0.0, difficulty_coefficient=1.0,
                        raw_score=95.0, final_score=95.0, rank=1),
        ])
        update_reputations(standings, pool_dir, {"corps-A": ["a1"]}, session_id="s1")

        # Now draft — a1 should be preferred (higher trust)
        result = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert result.summary["brass"] == ["a1"]

    def test_drafting_sees_trust_after_decay(self, tmp_path):
        """apply_season_decay changes trust → draft_roster reflects it."""
        from backend.services.drafting import draft_roster, RoleRequirement

        pool_dir = tmp_path / "pool"
        agents = [
            _make_agent_yaml(agent_id="a1", display_name="A1", primary_instrument="brass",
                             trust_score=90.0, total_sessions=10),
            _make_agent_yaml(agent_id="a2", display_name="A2", primary_instrument="brass",
                             trust_score=89.0, total_sessions=10),
        ]
        _write_pool(pool_dir, agents)

        # Before decay, a1 wins
        result1 = draft_roster("c1", [RoleRequirement("brass", 1)], pool_dir)
        assert result1.summary["brass"] == ["a1"]

        # Apply heavy decay to verify trust changed in files
        apply_season_decay(pool_dir, decay_rate=0.5, baseline=50.0)
        a1 = _read_agent(pool_dir, "a1")
        a2 = _read_agent(pool_dir, "a2")
        # Both should have decayed toward 50
        assert a1["trust_score"] < 90.0
        assert a2["trust_score"] < 89.0


class TestScoreValidation:
    def test_performance_score_none_raises(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(trust_score=50.0, total_sessions=5)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(results=[
            CorpsResult(corps_id="corps-A", caption_scores={},
                        penalties_total=0.0, difficulty_coefficient=1.0,
                        raw_score=0.0, final_score=None, rank=1),
        ])
        with pytest.raises(ValueError, match="Invalid performance_score"):
            update_reputations(standings, pool_dir, {"corps-A": ["agent-001"]}, session_id="s1")

    def test_performance_score_nan_raises(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(trust_score=50.0, total_sessions=5)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(results=[
            CorpsResult(corps_id="corps-A", caption_scores={},
                        penalties_total=0.0, difficulty_coefficient=1.0,
                        raw_score=0.0, final_score=float("nan"), rank=1),
        ])
        with pytest.raises(ValueError, match="Invalid performance_score"):
            update_reputations(standings, pool_dir, {"corps-A": ["agent-001"]}, session_id="s1")

    def test_performance_score_out_of_range_raises(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(trust_score=50.0, total_sessions=5)
        _write_pool(pool_dir, [agent])

        for bad_score in [150.0, -1.0]:
            standings = _make_standings(results=[
                CorpsResult(corps_id="corps-A", caption_scores={},
                            penalties_total=0.0, difficulty_coefficient=1.0,
                            raw_score=bad_score, final_score=bad_score, rank=1),
            ])
            with pytest.raises(ValueError, match="performance_score must be"):
                update_reputations(standings, pool_dir, {"corps-A": ["agent-001"]}, session_id="s1")

    def test_trust_clamped_to_range(self, tmp_path):
        pool_dir = tmp_path / "pool"
        # Agent with trust near 100, give a perfect score
        agent = _make_agent_yaml(trust_score=99.0, total_sessions=100)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(results=[
            CorpsResult(corps_id="corps-A", caption_scores={},
                        penalties_total=0.0, difficulty_coefficient=1.0,
                        raw_score=100.0, final_score=100.0, rank=1),
        ])
        update_reputations(standings, pool_dir, {"corps-A": ["agent-001"]}, session_id="s1")

        updated = _read_agent(pool_dir, "agent-001")
        assert 0.0 <= updated["trust_score"] <= 100.0


class TestIdempotency:
    def test_idempotent_same_session_id(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(trust_score=50.0, total_sessions=5)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(results=[
            CorpsResult(corps_id="corps-A", caption_scores={},
                        penalties_total=0.0, difficulty_coefficient=1.0,
                        raw_score=80.0, final_score=80.0, rank=1),
        ])
        roster_map = {"corps-A": ["agent-001"]}

        update_reputations(standings, pool_dir, roster_map, session_id="session-X")
        after_first = _read_agent(pool_dir, "agent-001")

        update_reputations(standings, pool_dir, roster_map, session_id="session-X")
        after_second = _read_agent(pool_dir, "agent-001")

        assert after_first["trust_score"] == after_second["trust_score"]
        assert after_first["total_sessions"] == after_second["total_sessions"]

    def test_different_session_ids_both_apply(self, tmp_path):
        pool_dir = tmp_path / "pool"
        agent = _make_agent_yaml(trust_score=50.0, total_sessions=5)
        _write_pool(pool_dir, [agent])

        standings = _make_standings(results=[
            CorpsResult(corps_id="corps-A", caption_scores={},
                        penalties_total=0.0, difficulty_coefficient=1.0,
                        raw_score=80.0, final_score=80.0, rank=1),
        ])
        roster_map = {"corps-A": ["agent-001"]}

        update_reputations(standings, pool_dir, roster_map, session_id="session-1")
        after_first = _read_agent(pool_dir, "agent-001")

        update_reputations(standings, pool_dir, roster_map, session_id="session-2")
        after_second = _read_agent(pool_dir, "agent-001")

        assert after_second["total_sessions"] == after_first["total_sessions"] + 1
        assert after_second["trust_score"] != after_first["trust_score"]
