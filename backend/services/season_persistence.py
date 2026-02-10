"""Season persistence layer.

Manages season workspaces on disk with scorecard, lifecycle rules, and per-corps
performance directories.
Directory structure: seasons/<season_id>/scorecard.md + lifecycle_rules.md + performances/
"""

from pathlib import Path

from backend.services.yaml_util import atomic_write, safe_dump_yaml, safe_load_yaml_dict

SCORECARD_TEMPLATE = """# Season Scorecard

## Brass

## Percussion

## Guard

## Visual

## General Effect
"""

LIFECYCLE_RULES_TEMPLATE = """# Season Lifecycle Rules

## States
- **registration**: Corps can register. No competitions run.
- **in_progress**: Competitions are active. New registrations closed.
- **completed**: All competitions scored. Final standings locked.
- **archived**: Historical record only.

## Transitions
- registration -> in_progress: Requires at least 2 registered corps.
- in_progress -> completed: All scheduled competitions must have final scores.
- completed -> archived: Manual trigger only. Standings become read-only.

## Competition Rules
- Each corps may enter each competition at most once.
- A corps must be in ON_TOUR or READY_FOR_CONTEST state to compete.
- Scores are final after judging panel submits. No retroactive changes.

## Scoring
- Caption scores: Brass, Percussion, Guard, Visual, General Effect (each 0-20).
- Total score = sum of all captions (max 100).
- Tiebreaker: highest General Effect score wins.

## Penalties
- Late entry (after registration closes): -2.0 from total.
- Incomplete show (missing movements): -5.0 from total.
- Process violations (bypassed hierarchy, skipped rehearsal modes): -1.0 each.
"""

DEFAULT_CONFIG = {
    "corps_per_contest": 12,
    "required_scores": 1,
}


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
    meta = {
        "season_id": season_id,
        "metadata": metadata or {},
        "shows": [],
        "divisions": {},
        "config": dict(DEFAULT_CONFIG),
        "schedule": [],
        "locked": False,
    }
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

    data = safe_load_yaml_dict((season_dir / "season.yaml").read_text(encoding="utf-8"))
    data.setdefault("shows", [])
    data.setdefault("divisions", {})
    data.setdefault("config", dict(DEFAULT_CONFIG))
    data.setdefault("schedule", [])
    data.setdefault("locked", False)
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


def save_season(season_dir: Path, data: dict) -> None:
    season_dir = Path(season_dir)
    atomic_write(season_dir / "season.yaml", safe_dump_yaml(data))


def add_show(season_dir: Path, show_slug: str) -> dict:
    data = load_season(season_dir)
    shows = list(dict.fromkeys(data.get("shows", []) + [show_slug]))
    data["shows"] = shows
    data.setdefault("divisions", {})
    data["divisions"].setdefault(show_slug, [])
    save_season(season_dir, data)
    return data


def remove_show(season_dir: Path, show_slug: str) -> dict:
    data = load_season(season_dir)
    data["shows"] = [s for s in data.get("shows", []) if s != show_slug]
    data.get("divisions", {}).pop(show_slug, None)
    save_season(season_dir, data)
    return data


def assign_corps(season_dir: Path, show_slug: str, corps_ids: list[str]) -> dict:
    data = load_season(season_dir)
    if show_slug not in data.get("shows", []):
        data["shows"] = list(dict.fromkeys(data.get("shows", []) + [show_slug]))
    data.setdefault("divisions", {})
    data["divisions"][show_slug] = sorted(set(corps_ids))
    save_season(season_dir, data)
    return data


def update_config(season_dir: Path, config: dict) -> dict:
    data = load_season(season_dir)
    current = dict(DEFAULT_CONFIG)
    current.update(data.get("config", {}))
    current.update(config or {})
    data["config"] = current
    save_season(season_dir, data)
    return data


def lock_season(season_dir: Path) -> dict:
    data = load_season(season_dir)
    data["locked"] = True
    data.setdefault("metadata", {})
    data["metadata"]["status"] = "locked"
    save_season(season_dir, data)
    return data


def build_schedule(season_dir: Path) -> list[dict]:
    data = load_season(season_dir)
    season_id = data.get("season_id", season_dir.name)
    schedule = []
    divisions = data.get("divisions", {})
    for show_slug in data.get("shows", []):
        corps_ids = divisions.get(show_slug, data.get("registered_corps", []))
        schedule.append({
            "competition_id": f"{season_id}-{show_slug}",
            "show_slug": show_slug,
            "corps_ids": corps_ids,
        })
    return schedule


def start_tour(season_dir: Path) -> dict:
    data = load_season(season_dir)
    data.setdefault("metadata", {})
    data["metadata"]["status"] = "touring"
    if not data.get("schedule"):
        from backend.services.tour_coordinator import generate_schedule
        data["schedule"] = generate_schedule(season_dir)
    save_season(season_dir, data)
    return data
