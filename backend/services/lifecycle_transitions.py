"""Lifecycle transition logic with season-phase gating.

Three phases: SHOW (mutations blocked), SCORING (corps updates from standings),
OFFSEASON (proposals created/applied). The caller passes the current phase;
no phase-tracking persistence in this module.
"""

import enum
from pathlib import Path

from backend.services.yaml_util import safe_dump_yaml

from backend.services.corps_persistence import (
    VALID_TRANSITIONS,
    assign_roster,
    load_corps,
    load_roster,
    retire_corps,
    update_corps_state,
)
from backend.services.scoring_engine import Standings


class SeasonPhase(str, enum.Enum):
    SHOW = "show"
    SCORING = "scoring"
    OFFSEASON = "offseason"


class MutationBlockedError(Exception):
    """Raised when a mutation is attempted during SHOW phase."""


def require_phase(current: SeasonPhase, *allowed: SeasonPhase) -> None:
    """Raise MutationBlockedError if current phase not in allowed."""
    if current not in allowed:
        raise MutationBlockedError(
            f"Operation not allowed in {current.value} phase. "
            f"Allowed phases: {', '.join(p.value for p in allowed)}"
        )


def guarded_update_corps_state(
    corps_dir: Path, new_state: str, phase: SeasonPhase
) -> None:
    """Wraps corps_persistence.update_corps_state; blocked during SHOW."""
    require_phase(phase, SeasonPhase.SCORING, SeasonPhase.OFFSEASON)
    update_corps_state(corps_dir, new_state)


def guarded_assign_roster(
    corps_dir: Path, assignments: list[dict], pool_dir: Path, phase: SeasonPhase
) -> None:
    """Wraps corps_persistence.assign_roster; blocked during SHOW."""
    require_phase(phase, SeasonPhase.SCORING, SeasonPhase.OFFSEASON)
    assign_roster(corps_dir, assignments, pool_dir)


def update_corps_from_standings(
    corps_base_dir: Path,
    standings: Standings,
    contending_threshold: int = 3,
    stagnant_threshold: int = 0,
    phase: SeasonPhase = SeasonPhase.SCORING,
) -> list[dict]:
    """Post-scoring: transition active corps based on standings rank.

    Rules:
    - rank <= contending_threshold AND current state is 'active' -> 'contending'
    - rank > (total_corps - stagnant_threshold) AND current state is 'active' -> 'stagnant'
    - Already contending/stagnant corps: no automatic change
    Returns list of {corps_id, old_state, new_state} for audit.
    Only callable in SCORING phase.
    """
    require_phase(phase, SeasonPhase.SCORING)
    corps_base_dir = Path(corps_base_dir)
    total = len(standings.results)
    audit: list[dict] = []

    for result in standings.results:
        corps_dir = corps_base_dir / result.corps_id
        data = load_corps(corps_dir)
        old_state = data["state"]

        if old_state != "active":
            continue

        new_state = None
        if result.rank <= contending_threshold:
            new_state = "contending"
        elif stagnant_threshold > 0 and result.rank > (total - stagnant_threshold):
            new_state = "stagnant"

        if new_state and new_state in VALID_TRANSITIONS.get(old_state, set()):
            update_corps_state(corps_dir, new_state)
            audit.append({
                "corps_id": result.corps_id,
                "old_state": old_state,
                "new_state": new_state,
            })

    return audit


def retire_corps_and_release(
    corps_dir: Path, corps_id: str, roster: dict, pool_dir: Path
) -> list[str]:
    """Retire corps, clear roster, write released agents marker.

    Returns list of released agent_ids.
    """
    corps_dir = Path(corps_dir)
    pool_dir = Path(pool_dir)

    released = [a["agent_id"] for a in roster.get("assignments", [])]

    retire_corps(corps_dir)

    # Write release marker for downstream consumption
    pool_dir.mkdir(parents=True, exist_ok=True)
    marker = {"corps_id": corps_id, "released_agent_ids": released}
    (pool_dir / "released_agents.yaml").write_text(safe_dump_yaml(marker))

    return released
