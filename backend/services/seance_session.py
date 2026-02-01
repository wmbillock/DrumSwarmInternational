"""Seance sessions anchored to corps history entries.

A seance session is a structured conversation with a simulated Executive Director
about a specific past show, grounded in the artifacts from that history entry.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from backend.services.corps_history import get_history_entry
from backend.services.yaml_util import atomic_write, safe_dump_yaml

REQUIRED_ARTIFACTS = {"standings"}


def _validate_seance_id(seance_id: str) -> None:
    """Reject seance IDs that could cause path traversal."""
    if ".." in seance_id or "/" in seance_id or "\\" in seance_id:
        raise ValueError(f"Invalid seance_id (path traversal): {seance_id!r}")


def _session_dir(project_root: Path, seance_id: str) -> Path:
    _validate_seance_id(seance_id)
    return project_root / "seances" / seance_id


def create_session(project_root: Path, corps_id: str, entry_id: str) -> dict:
    """Create a seance session from a history index entry.

    Validates that required artifacts exist, assembles context binder,
    writes session.yaml + transcript.md stub.
    """
    project_root = Path(project_root)
    entry = get_history_entry(project_root, corps_id, entry_id)

    artifacts = entry.get("artifacts", {})

    # Check required artifacts
    for req in REQUIRED_ARTIFACTS:
        if req not in artifacts:
            raise ValueError(f"Required artifact missing: {req}")

    # Build context binder — probe each artifact for existence and non-emptiness
    context_binder = []
    for artifact_type, rel_path in artifacts.items():
        abs_path = project_root / rel_path
        loaded = abs_path.exists() and abs_path.stat().st_size > 0
        context_binder.append({
            "path": rel_path,
            "type": artifact_type,
            "loaded": loaded,
        })

    seance_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()

    session = {
        "seance_id": seance_id,
        "corps_id": corps_id,
        "entry_id": entry_id,
        "season_id": entry["season_id"],
        "show_slug": entry.get("show_slug"),
        "participant": "executive_director",
        "created_at": now,
        "status": "active",
        "context_binder": context_binder,
    }

    # Write to disk
    sdir = _session_dir(project_root, seance_id)
    sdir.mkdir(parents=True, exist_ok=True)
    atomic_write(sdir / "session.yaml", safe_dump_yaml(session))

    # Write transcript stub with header comment
    header = f"<!-- seance: {seance_id} | corps: {corps_id} | season: {entry['season_id']} -->\n"
    atomic_write(sdir / "transcript.md", header)

    return session


def load_session(project_root: Path, seance_id: str) -> dict:
    """Read session.yaml for a seance."""
    project_root = Path(project_root)
    sdir = _session_dir(project_root, seance_id)
    session_path = sdir / "session.yaml"
    if not session_path.exists():
        raise FileNotFoundError(f"Seance session not found: {seance_id}")
    return yaml.safe_load(session_path.read_text())


def append_transcript(project_root: Path, seance_id: str, role: str, message: str) -> None:
    """Append a conversation turn to transcript.md."""
    project_root = Path(project_root)
    sdir = _session_dir(project_root, seance_id)
    transcript_path = sdir / "transcript.md"
    with open(transcript_path, "a") as f:
        f.write(f"\n**[{role}]** {message}\n")


def read_transcript(project_root: Path, seance_id: str) -> str:
    """Read transcript.md."""
    project_root = Path(project_root)
    sdir = _session_dir(project_root, seance_id)
    return (sdir / "transcript.md").read_text()


def assemble_context(project_root: Path, session: dict) -> str:
    """Read all loaded artifacts from context binder, concatenate into context string."""
    project_root = Path(project_root)
    parts = []
    for item in session["context_binder"]:
        if not item["loaded"]:
            continue
        abs_path = project_root / item["path"]
        if not abs_path.exists():
            continue
        content = abs_path.read_text().strip()
        if content:
            parts.append(f"--- {item['type']} ---\n{content}")
    return "\n\n".join(parts)


def close_session(project_root: Path, seance_id: str) -> None:
    """Set session status to closed."""
    project_root = Path(project_root)
    sdir = _session_dir(project_root, seance_id)
    session_path = sdir / "session.yaml"
    session = yaml.safe_load(session_path.read_text())
    session["status"] = "closed"
    atomic_write(session_path, safe_dump_yaml(session))
