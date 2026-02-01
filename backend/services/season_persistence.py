"""Season persistence layer.

Manages season workspaces on disk with scorecard, lifecycle rules, and per-corps
performance directories.
Directory structure: seasons/<season_id>/scorecard.md + lifecycle_rules.md + performances/
"""

from pathlib import Path

from backend.services.yaml_util import atomic_write, safe_dump_yaml

SCORECARD_TEMPLATE = """# Season Scorecard

## Brass

## Percussion

## Guard

## Visual

## General Effect
"""

LIFECYCLE_RULES_TEMPLATE = """# Lifecycle Rules

TODO: Define season lifecycle rules.
"""


def create_season(base_dir: Path, season_id: str, metadata: dict | None = None) -> Path:
    """Create a season workspace directory with scorecard and lifecycle rules.

    Returns the season directory path.
    Raises ValueError if season already exists.
    """
    base_dir = Path(base_dir)
    season_dir = base_dir / "seasons" / season_id
    if season_dir.exists():
        raise ValueError(f"Season '{season_id}' already exists at {season_dir}")
    season_dir.mkdir(parents=True)
    (season_dir / "performances").mkdir()
    atomic_write(season_dir / "scorecard.md", SCORECARD_TEMPLATE)
    atomic_write(season_dir / "lifecycle_rules.md", LIFECYCLE_RULES_TEMPLATE)
    meta = {"season_id": season_id, "metadata": metadata or {}}
    atomic_write(season_dir / "season.yaml", safe_dump_yaml(meta))
    return season_dir


def load_season(season_dir: Path) -> dict:
    """Read season metadata and list of registered corps.

    Validates required files exist. Raises FileNotFoundError if missing.
    """
    season_dir = Path(season_dir)
    for required in ("scorecard.md", "lifecycle_rules.md", "season.yaml"):
        if not (season_dir / required).exists():
            raise FileNotFoundError(f"Required file '{required}' missing in {season_dir}")

    import yaml
    data = yaml.safe_load((season_dir / "season.yaml").read_text())
    data["registered_corps"] = list_registered_corps(season_dir)
    return data


def register_corps(season_dir: Path, corps_id: str, corps_base_dir: Path) -> Path:
    """Register a corps for this season by creating a performances subdirectory.

    Raises FileNotFoundError if season or corps is invalid.
    """
    season_dir = Path(season_dir)
    corps_base_dir = Path(corps_base_dir)
    if not (season_dir / "season.yaml").exists():
        raise FileNotFoundError(f"Invalid season directory: {season_dir}")
    if not (corps_base_dir / corps_id / "corps.yaml").exists():
        raise FileNotFoundError(f"Corps '{corps_id}' not found at {corps_base_dir / corps_id}")
    perf_dir = season_dir / "performances" / corps_id
    perf_dir.mkdir(parents=True, exist_ok=True)
    return perf_dir


def list_registered_corps(season_dir: Path) -> list[str]:
    """Return corps_ids that have performance directories."""
    season_dir = Path(season_dir)
    perf_root = season_dir / "performances"
    if not perf_root.exists():
        return []
    return sorted(d.name for d in perf_root.iterdir() if d.is_dir())
