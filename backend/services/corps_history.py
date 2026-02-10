"""Corps history index — build and query per-corps history indexes from filesystem artifacts."""

import re
from datetime import datetime, timezone
from pathlib import Path

from backend.services.yaml_util import atomic_write, safe_dump_yaml, safe_load_yaml_dict


def _parse_show_slug(notes: str) -> str | None:
    """Extract show slug from notes field (convention: 'show:<slug>')."""
    if not notes:
        return None
    m = re.search(r"show:(\S+)", notes)
    return m.group(1) if m else None


def _probe_artifacts(root: Path, corps_id: str, season_id: str, show_slug: str | None) -> dict:
    """Return dict of artifact_type -> relative_path for paths that exist on disk."""
    candidates = {
        "standings": f"seasons/{season_id}/standings.yaml",
        "corps_scores": f"seasons/{season_id}/performances/{corps_id}/scores.yaml",
    }
    if show_slug:
        candidates["show_status"] = f"shows/{show_slug}/status.yaml"
        candidates["design_notes"] = f"shows/{show_slug}/design_notes.md"
        candidates["show_prompt"] = f"shows/{show_slug}/show_prompt.md"

    return {k: v for k, v in candidates.items() if (root / v).exists()}


def _discover_runs(root: Path, corps_id: str, season_id: str) -> list[str]:
    """Find run directories under performances/<corps_id>/ that contain manifest.yaml."""
    perf_dir = root / "seasons" / season_id / "performances" / corps_id
    if not perf_dir.is_dir():
        return []
    runs = []
    for child in sorted(perf_dir.iterdir()):
        if child.is_dir() and (child / "manifest.yaml").exists():
            runs.append(child.name)
    return runs


def build_history_index(project_root: Path, corps_id: str) -> dict:
    """Scan corps.yaml + filesystem, write and return history index.

    Deduplicates by (corps_id, season_id), keeping the last occurrence.
    Entries are sorted by entry_id for stable ordering.
    """
    project_root = Path(project_root)
    corps_path = project_root / "corps" / corps_id / "corps.yaml"
    corps = safe_load_yaml_dict(corps_path.read_text(encoding="utf-8"))
    history = corps.get("history", [])

    # Deduplicate: last entry per season wins
    by_season: dict[str, dict] = {}
    for entry in history:
        by_season[entry["season_id"]] = entry

    entries = []
    for season_id, h in by_season.items():
        show_slug = _parse_show_slug(h.get("notes", ""))
        entry_id = f"{corps_id}-{season_id}"
        artifacts = _probe_artifacts(project_root, corps_id, season_id, show_slug)
        runs = _discover_runs(project_root, corps_id, season_id)

        entries.append({
            "entry_id": entry_id,
            "season_id": season_id,
            "show_slug": show_slug,
            "placement": h["placement"],
            "final_score": h["final_score"],
            "artifacts": artifacts,
            "runs": runs,
        })

    # Stable ordering by entry_id
    entries.sort(key=lambda e: e["entry_id"])

    index = {
        "corps_id": corps_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }

    # Write to disk
    index_dir = project_root / "corps" / corps_id / "history"
    index_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(index_dir / "index.yaml", safe_dump_yaml(index))

    return index


def load_history_index(project_root: Path, corps_id: str) -> dict:
    """Read cached index or build if missing."""
    project_root = Path(project_root)
    index_path = project_root / "corps" / corps_id / "history" / "index.yaml"
    if index_path.exists():
        return safe_load_yaml_dict(index_path.read_text(encoding="utf-8"))
    return build_history_index(project_root, corps_id)


def get_history_entry(project_root: Path, corps_id: str, entry_id: str) -> dict:
    """Single entry from index. Raises ValueError if not found."""
    index = load_history_index(project_root, corps_id)
    for entry in index["entries"]:
        if entry["entry_id"] == entry_id:
            return entry
    raise ValueError(f"History entry '{entry_id}' not found for corps '{corps_id}'")
