"""Reputation/fitness update system.

After a performance is scored (Standings produced), updates each participating
agent's trust_score and session counts in the talent pool YAML files.
Deterministic, pure YAML, no DB writes.
"""

import math
from pathlib import Path

from backend.services.scoring_engine import Standings
from backend.services.yaml_util import atomic_write, safe_dump_yaml, safe_load_yaml_dict

MINIMUM_SAMPLE_THRESHOLD = 3
DECAY_RATE = 0.05
DECAY_BASELINE = 50.0
SUCCESS_THRESHOLD = 60.0


def _validate_score(value, name="score", lo=0.0, hi=100.0):
    """Validate a numeric score is within range. Rejects None, NaN, and Inf."""
    if value is None:
        raise ValueError(f"Invalid {name}: {value!r}")
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"Invalid {name}: {value!r}")
    if not (lo <= value <= hi):
        raise ValueError(f"{name} must be {lo}..{hi}, got {value}")
    return value


def _clamp(value, lo=0.0, hi=100.0):
    """Clamp value to [lo, hi] range."""
    return max(lo, min(hi, value))


def _load_agent(pool_dir: Path, agent_id: str) -> dict:
    return safe_load_yaml_dict((pool_dir / "agents" / f"{agent_id}.yaml").read_text(encoding="utf-8"))


def _save_agent(pool_dir: Path, agent: dict) -> None:
    path = pool_dir / "agents" / f"{agent['agent_id']}.yaml"
    atomic_write(path, safe_dump_yaml(agent))


def _sync_ledger_entry(pool_dir: Path, agent_id: str, updates: dict) -> None:
    """Update fields for agent_id in ledger.yaml."""
    ledger_path = pool_dir / "ledger.yaml"
    ledger = safe_load_yaml_dict(ledger_path.read_text(encoding="utf-8"), {"agents": []})
    for entry in ledger.get("agents", []):
        if entry["agent_id"] == agent_id:
            entry.update(updates)
            break
    atomic_write(ledger_path, safe_dump_yaml(ledger))


def _update_ledger_availability(pool_dir: Path, agent_id: str, availability: str) -> None:
    _sync_ledger_entry(pool_dir, agent_id, {"availability": availability})


def update_reputations(
    standings: Standings,
    pool_dir: Path,
    roster_map: dict[str, list[str]],
    session_id: str = "",
) -> None:
    """Update agent trust_score and session counts from standings.

    roster_map: {corps_id: [agent_ids]}.
    session_id: unique identifier for idempotency; if already seen, agent is skipped.
    """
    pool_dir = Path(pool_dir)
    score_by_corps = {r.corps_id: r.final_score for r in standings.results}

    for corps_id, agent_ids in roster_map.items():
        if corps_id not in score_by_corps:
            continue
        performance_score = _validate_score(
            score_by_corps[corps_id], name="performance_score"
        )

        for agent_id in agent_ids:
            agent = _load_agent(pool_dir, agent_id)

            # Idempotency: skip if session already processed
            if session_id:
                seen = agent.get("seen_sessions", [])
                if session_id in seen:
                    continue

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

            agent["trust_score"] = round(_clamp(new_trust), 6)
            agent["total_sessions"] = old_samples + 1

            if performance_score >= SUCCESS_THRESHOLD:
                agent["successful_sessions"] = int(agent.get("successful_sessions", 0)) + 1
            else:
                agent["failed_sessions"] = int(agent.get("failed_sessions", 0)) + 1

            # Record session for idempotency
            if session_id:
                seen = agent.get("seen_sessions", [])
                seen.append(session_id)
                agent["seen_sessions"] = seen[-20:]  # cap at 20 most recent

            _save_agent(pool_dir, agent)
            _sync_ledger_entry(pool_dir, agent_id, {"trust_score": agent["trust_score"]})


def apply_season_decay(
    pool_dir: Path,
    decay_rate: float = DECAY_RATE,
    baseline: float = DECAY_BASELINE,
) -> None:
    """Decay all active agents' trust toward baseline."""
    pool_dir = Path(pool_dir)
    ledger = safe_load_yaml_dict((pool_dir / "ledger.yaml").read_text(encoding="utf-8"), {"agents": []})

    for entry in ledger.get("agents", []):
        if entry.get("availability") != "active":
            continue
        agent = _load_agent(pool_dir, entry["agent_id"])
        trust = float(agent.get("trust_score", baseline))
        trust += decay_rate * (baseline - trust)
        agent["trust_score"] = round(_clamp(trust), 6)
        _save_agent(pool_dir, agent)
        _sync_ledger_entry(pool_dir, entry["agent_id"], {"trust_score": agent["trust_score"]})


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
    corps = safe_load_yaml_dict(corps_path.read_text(encoding="utf-8"))

    if "history" not in corps:
        corps["history"] = []

    corps["history"].append({
        "season_id": season_id,
        "placement": placement,
        "final_score": final_score,
        "notes": notes,
    })

    atomic_write(corps_path, safe_dump_yaml(corps))
