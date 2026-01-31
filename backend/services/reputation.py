"""Reputation/fitness update system.

After a performance is scored (Standings produced), updates each participating
agent's trust_score and session counts in the talent pool YAML files.
Deterministic, pure YAML, no DB writes.
"""

from pathlib import Path

import yaml

from backend.services.scoring_engine import Standings
from backend.services.season_persistence import _atomic_write

MINIMUM_SAMPLE_THRESHOLD = 3
DECAY_RATE = 0.05
DECAY_BASELINE = 50.0
SUCCESS_THRESHOLD = 60.0


def _load_agent(pool_dir: Path, agent_id: str) -> dict:
    return yaml.safe_load((pool_dir / "agents" / f"{agent_id}.yaml").read_text())


def _save_agent(pool_dir: Path, agent: dict) -> None:
    path = pool_dir / "agents" / f"{agent['agent_id']}.yaml"
    _atomic_write(path, yaml.dump(agent, default_flow_style=False))


def _update_ledger_availability(pool_dir: Path, agent_id: str, availability: str) -> None:
    ledger_path = pool_dir / "ledger.yaml"
    ledger = yaml.safe_load(ledger_path.read_text())
    for entry in ledger.get("agents", []):
        if entry["agent_id"] == agent_id:
            entry["availability"] = availability
            break
    _atomic_write(ledger_path, yaml.dump(ledger, default_flow_style=False))


def update_reputations(
    standings: Standings,
    pool_dir: Path,
    roster_map: dict[str, list[str]],
) -> None:
    """Update agent trust_score and session counts from standings.

    roster_map: {corps_id: [agent_ids]}.
    """
    pool_dir = Path(pool_dir)
    score_by_corps = {r.corps_id: r.final_score for r in standings.results}

    for corps_id, agent_ids in roster_map.items():
        if corps_id not in score_by_corps:
            continue
        performance_score = score_by_corps[corps_id]

        for agent_id in agent_ids:
            agent = _load_agent(pool_dir, agent_id)

            old_trust = float(agent.get("trust_score", 50.0))
            old_samples = int(agent.get("total_sessions", 0))

            # Weighted moving average
            full_new_trust = (old_trust * old_samples + performance_score) / (old_samples + 1)

            # Minimum sample dampening
            if old_samples < MINIMUM_SAMPLE_THRESHOLD:
                dampening = old_samples / MINIMUM_SAMPLE_THRESHOLD
                new_trust = old_trust + dampening * (full_new_trust - old_trust)
            else:
                new_trust = full_new_trust

            agent["trust_score"] = round(new_trust, 6)
            agent["total_sessions"] = old_samples + 1

            if performance_score >= SUCCESS_THRESHOLD:
                agent["successful_sessions"] = int(agent.get("successful_sessions", 0)) + 1
            else:
                agent["failed_sessions"] = int(agent.get("failed_sessions", 0)) + 1

            _save_agent(pool_dir, agent)


def apply_season_decay(
    pool_dir: Path,
    decay_rate: float = DECAY_RATE,
    baseline: float = DECAY_BASELINE,
) -> None:
    """Decay all active agents' trust toward baseline."""
    pool_dir = Path(pool_dir)
    ledger = yaml.safe_load((pool_dir / "ledger.yaml").read_text())

    for entry in ledger.get("agents", []):
        if entry.get("availability") != "active":
            continue
        agent = _load_agent(pool_dir, entry["agent_id"])
        trust = float(agent.get("trust_score", baseline))
        trust += decay_rate * (baseline - trust)
        agent["trust_score"] = round(trust, 6)
        _save_agent(pool_dir, agent)


def release_agent(pool_dir: Path, agent_id: str) -> None:
    """Return assigned agent to pool (availability -> "active"), preserve reputation."""
    pool_dir = Path(pool_dir)
    agent = _load_agent(pool_dir, agent_id)
    agent["availability"] = "active"
    _save_agent(pool_dir, agent)
    _update_ledger_availability(pool_dir, agent_id, "active")


def record_corps_placement(
    corps_dir: Path,
    season_id: str,
    placement: int,
    final_score: float,
    notes: str = "",
) -> None:
    """Append placement entry to corps.yaml history list."""
    corps_dir = Path(corps_dir)
    corps_path = corps_dir / "corps.yaml"
    corps = yaml.safe_load(corps_path.read_text())

    if "history" not in corps:
        corps["history"] = []

    corps["history"].append({
        "season_id": season_id,
        "placement": placement,
        "final_score": final_score,
        "notes": notes,
    })

    _atomic_write(corps_path, yaml.dump(corps, default_flow_style=False))
