"""Offseason proposal creation, loading, and application.

Proposals are stored as markdown with YAML front matter blocks —
human-readable, machine-parseable, git-diffable.
"""

from dataclasses import dataclass, asdict
from pathlib import Path

from backend.services.yaml_util import safe_dump_yaml
from backend.services.corps_persistence import (
    VALID_TRANSITIONS,
    load_corps,
    update_corps_state,
    assign_roster,
    retire_corps,
)
from backend.services.lifecycle_transitions import (
    SeasonPhase,
    require_phase,
    retire_corps_and_release,
)


@dataclass
class Proposal:
    proposal_type: str   # "state_change", "roster_change", "retirement"
    corps_id: str
    description: str
    changes: dict        # type-specific payload


def create_proposals_file(
    base_dir: Path, season_id: str, proposals: list[Proposal],
    phase: SeasonPhase = SeasonPhase.OFFSEASON,
) -> Path:
    """Write seasons/<season_id>/offseason/proposals.md.

    Only callable in OFFSEASON phase.
    """
    require_phase(phase, SeasonPhase.OFFSEASON)
    base_dir = Path(base_dir)
    offseason_dir = base_dir / "seasons" / season_id / "offseason"
    offseason_dir.mkdir(parents=True, exist_ok=True)
    path = offseason_dir / "proposals.md"

    lines = ["# Offseason Proposals\n"]
    for i, p in enumerate(proposals):
        lines.append(f"\n## Proposal {i + 1}: {p.description}\n")
        lines.append("```yaml")
        block = {
            "proposal_type": p.proposal_type,
            "corps_id": p.corps_id,
            "description": p.description,
            "changes": p.changes,
        }
        lines.append(safe_dump_yaml(block).rstrip())
        lines.append("```\n")

    path.write_text("\n".join(lines))
    return path


def load_proposals(base_dir: Path, season_id: str) -> list[Proposal]:
    """Parse proposals.md back into Proposal objects."""
    base_dir = Path(base_dir)
    path = base_dir / "seasons" / season_id / "offseason" / "proposals.md"
    text = path.read_text()

    proposals: list[Proposal] = []
    in_yaml = False
    yaml_lines: list[str] = []

    for line in text.splitlines():
        if line.strip() == "```yaml":
            in_yaml = True
            yaml_lines = []
        elif line.strip() == "```" and in_yaml:
            in_yaml = False
            from backend.services.yaml_util import safe_load_yaml_dict
            block = safe_load_yaml_dict("\n".join(yaml_lines))
            if not block:
                continue
            proposals.append(Proposal(
                proposal_type=block["proposal_type"],
                corps_id=block["corps_id"],
                description=block["description"],
                changes=block.get("changes", {}),
            ))
        elif in_yaml:
            yaml_lines.append(line)

    return proposals


def apply_proposals(
    base_dir: Path,
    season_id: str,
    corps_base_dir: Path,
    pool_dir: Path,
    apply: bool = False,
) -> list[dict]:
    """Validate and apply proposals. REQUIRES apply=True.

    Raises ValueError if apply is False.
    Each proposal validated independently; failures don't block others.
    Returns list of {proposal_index, corps_id, result, error?} for audit.
    """
    if not apply:
        raise ValueError("apply_proposals requires apply=True to execute changes")

    proposals = load_proposals(base_dir, season_id)
    corps_base_dir = Path(corps_base_dir)
    pool_dir = Path(pool_dir)
    audit: list[dict] = []

    for i, p in enumerate(proposals):
        entry: dict = {"proposal_index": i, "corps_id": p.corps_id}
        corps_dir = corps_base_dir / p.corps_id

        try:
            if not corps_dir.exists():
                raise ValueError(f"Corps '{p.corps_id}' not found")

            if p.proposal_type == "state_change":
                new_state = p.changes.get("new_state", "")
                data = load_corps(corps_dir)
                current = data["state"]
                if new_state not in VALID_TRANSITIONS.get(current, set()):
                    raise ValueError(
                        f"Invalid transition: {current} -> {new_state}"
                    )
                update_corps_state(corps_dir, new_state)
                entry["result"] = "applied"

            elif p.proposal_type == "retirement":
                from backend.services.corps_persistence import load_roster
                roster = load_roster(corps_dir)
                retire_corps_and_release(corps_dir, p.corps_id, roster, pool_dir)
                entry["result"] = "applied"

            elif p.proposal_type == "roster_change":
                assignments = p.changes.get("assignments", [])
                assign_roster(corps_dir, assignments, pool_dir)
                entry["result"] = "applied"

            else:
                raise ValueError(f"Unknown proposal type: {p.proposal_type}")

        except Exception as exc:
            entry["result"] = "error"
            entry["error"] = str(exc)

        audit.append(entry)

    return audit
