"""Deterministic corps drafting — select agents from talent pool by role.

Pure YAML, no LLM, no DB writes. ``draft_roster`` is read-only;
``execute_draft`` wraps it with file writes.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from backend.services.corps_persistence import assign_roster
from backend.services.talent_pool import load_talent_pool


@dataclass
class RoleRequirement:
    role: str
    count: int = 1
    preferred_specialties: list[str] = field(default_factory=list)


@dataclass
class DraftResult:
    corps_id: str
    assignments: list[dict]
    summary: dict[str, list[str]]


class DraftError(Exception):
    """Raised when the pool cannot fill all required roles."""

    def __init__(self, message: str, unfilled: dict[str, int]):
        super().__init__(message)
        self.unfilled = unfilled


def rank_candidates(
    candidates: list[dict],
    preferred_specialties: list[str] | None = None,
) -> list[dict]:
    """Sort deterministically: specialty match > trust_score > experience > agent_id."""
    prefs = set(preferred_specialties or [])

    def sort_key(agent: dict):
        has_match = 1 if prefs and any(s in prefs for s in agent.get("specialties", [])) else 0
        return (
            -has_match,
            -(agent.get("trust_score") or 0),
            -(agent.get("experience_seasons") or 0),
            agent.get("agent_id", ""),
        )

    return sorted(candidates, key=sort_key)


def draft_roster(
    corps_id: str,
    requirements: list[RoleRequirement],
    pool_dir: Path,
) -> DraftResult:
    """Pure selection — no side effects."""
    pool = load_talent_pool(Path(pool_dir))
    agents_by_id = {a["agent_id"]: a for a in pool["agents"]}

    drafted_ids: set[str] = set()
    assignments: list[dict] = []
    summary: dict[str, list[str]] = {}
    unfilled: dict[str, int] = {}

    for req in requirements:
        candidates = [
            a for a in agents_by_id.values()
            if a.get("primary_instrument") == req.role
            and a.get("availability") == "active"
            and a["agent_id"] not in drafted_ids
        ]
        ranked = rank_candidates(candidates, req.preferred_specialties)
        selected = ranked[: req.count]

        if len(selected) < req.count:
            unfilled[req.role] = req.count - len(selected)

        for agent in selected:
            drafted_ids.add(agent["agent_id"])
            assignments.append({"agent_id": agent["agent_id"], "role": req.role})

        summary[req.role] = [a["agent_id"] for a in selected]

    if unfilled:
        raise DraftError(
            f"Cannot fill roles: {unfilled}",
            unfilled=unfilled,
        )

    return DraftResult(corps_id=corps_id, assignments=assignments, summary=summary)


def _atomic_write(path: Path, content: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, content.encode())
        os.close(fd)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def execute_draft(
    corps_id: str,
    requirements: list[RoleRequirement],
    pool_dir: Path,
    corps_dir: Path,
) -> DraftResult:
    """draft_roster + mark agents assigned in pool + write roster."""
    pool_dir = Path(pool_dir)
    corps_dir = Path(corps_dir)

    result = draft_roster(corps_id, requirements, pool_dir)

    # Mark agents as assigned in per-agent YAML and ledger
    drafted_ids = {a["agent_id"] for a in result.assignments}
    agents_dir = pool_dir / "agents"

    for agent_id in drafted_ids:
        agent_path = agents_dir / f"{agent_id}.yaml"
        agent_data = yaml.safe_load(agent_path.read_text())
        agent_data["availability"] = "assigned"
        _atomic_write(agent_path, yaml.dump(agent_data, default_flow_style=False))

    # Update ledger
    ledger_path = pool_dir / "ledger.yaml"
    ledger = yaml.safe_load(ledger_path.read_text())
    for entry in ledger.get("agents", []):
        if entry["agent_id"] in drafted_ids:
            entry["availability"] = "assigned"
    _atomic_write(ledger_path, yaml.dump(ledger, default_flow_style=False))

    # Write roster
    assign_roster(corps_dir, result.assignments, pool_dir)

    return result
