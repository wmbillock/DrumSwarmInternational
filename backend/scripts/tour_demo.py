"""Living system lifecycle tour demo.

Runs a complete pool → draft → score → reputation update → decay → release cycle
in a temporary directory. Demonstrates the full lifecycle of the DCI swarm system.
"""

import tempfile
from pathlib import Path

import yaml

from backend.models.score import JudgeType
from backend.services.corps_persistence import create_corps
from backend.services.drafting import RoleRequirement, execute_draft
from backend.services.reputation import (
    apply_season_decay,
    release_agent,
    update_reputations,
)
from backend.services.scoring_engine import CorpsResult, Standings
from backend.services.yaml_util import safe_dump_yaml


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
    (pool_dir / "ledger.yaml").write_text(safe_dump_yaml(ledger))
    for a in agents:
        (agents_dir / f"{a['agent_id']}.yaml").write_text(safe_dump_yaml(a))


def run_tour(base_dir: Path) -> dict:
    """Run full lifecycle tour. Returns summary dict."""
    base_dir = Path(base_dir)
    pool_dir = base_dir / "pool"
    corps_base = base_dir / "corps"

    # 1. Create talent pool
    agents = [
        {
            "agent_id": "agent-alpha",
            "display_name": "Alpha",
            "primary_instrument": "brass",
            "availability": "active",
            "trust_score": 70.0,
            "total_sessions": 5,
            "successful_sessions": 0,
            "failed_sessions": 0,
            "experience_seasons": 1,
            "specialties": ["jazz"],
        },
        {
            "agent_id": "agent-beta",
            "display_name": "Beta",
            "primary_instrument": "percussion",
            "availability": "active",
            "trust_score": 60.0,
            "total_sessions": 5,
            "successful_sessions": 3,
            "failed_sessions": 2,
            "experience_seasons": 2,
            "specialties": [],
        },
    ]
    _write_pool(pool_dir, agents)

    # 2. Create corps and draft roster
    corps_id = "demo-corps"
    corps_dir = corps_base / corps_id
    create_corps(corps_dir, {
        "corps_id": corps_id,
        "display_name": "Demo Corps",
        "philosophy": "Excellence through iteration",
        "state": "commissioned",
    })

    # Transition to active for drafting
    from backend.services.corps_persistence import update_corps_state
    update_corps_state(corps_dir, "active")

    draft_result = execute_draft(
        corps_id,
        [RoleRequirement("brass", 1), RoleRequirement("percussion", 1)],
        pool_dir,
        corps_dir,
    )

    # 3. Build standings (simulate scoring)
    standings = Standings(
        season_id="2025-tour",
        results=[
            CorpsResult(
                corps_id=corps_id,
                caption_scores={JudgeType.BRASS: 85.0},
                penalties_total=0.0,
                difficulty_coefficient=1.0,
                raw_score=85.0,
                final_score=85.0,
                rank=1,
            )
        ],
        generated_at="2025-01-01T00:00:00+00:00",
    )

    # 4. Update reputations
    roster_map = {corps_id: [a["agent_id"] for a in draft_result.assignments]}
    update_reputations(standings, pool_dir, roster_map, session_id="tour-session-1")

    # Read post-update state
    alpha_after_update = yaml.safe_load(
        (pool_dir / "agents" / "agent-alpha.yaml").read_text()
    )
    beta_after_update = yaml.safe_load(
        (pool_dir / "agents" / "agent-beta.yaml").read_text()
    )

    # 5. Release agents
    for a in draft_result.assignments:
        release_agent(pool_dir, a["agent_id"])

    # 6. Apply season decay
    apply_season_decay(pool_dir)

    # Read final state
    alpha_final = yaml.safe_load(
        (pool_dir / "agents" / "agent-alpha.yaml").read_text()
    )
    beta_final = yaml.safe_load(
        (pool_dir / "agents" / "agent-beta.yaml").read_text()
    )

    return {
        "drafted": [a["agent_id"] for a in draft_result.assignments],
        "alpha_trust_after_update": alpha_after_update["trust_score"],
        "beta_trust_after_update": beta_after_update["trust_score"],
        "alpha_trust_final": alpha_final["trust_score"],
        "beta_trust_final": beta_final["trust_score"],
        "alpha_sessions": alpha_final["total_sessions"],
        "beta_sessions": beta_final["total_sessions"],
        "alpha_availability": alpha_final["availability"],
        "beta_availability": beta_final["availability"],
    }


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        summary = run_tour(Path(tmpdir))
        print("=== DCI Swarm Lifecycle Tour ===")
        for k, v in summary.items():
            print(f"  {k}: {v}")
        print("Tour complete.")
