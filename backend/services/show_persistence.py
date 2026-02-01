"""Show artifacts persistence layer.

Manages show workspaces on disk with design notes, prompts, and status tracking.
Directory structure: shows/<slug>/design_notes.md + show_prompt.md + status.yaml
"""

import re
from pathlib import Path

import yaml

from backend.services.yaml_util import atomic_write, safe_dump_yaml

VALID_STATUSES = ("draft", "needs_review", "approved", "rejected")


def slugify(title: str) -> str:
    """Lowercase, strip non-alnum, collapse hyphens."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def create_show(title: str, base_dir: Path) -> Path:
    """Create a show workspace directory; handles slug collisions with -2, -3, etc."""
    base_dir = Path(base_dir)
    slug = slugify(title)
    candidate = base_dir / slug
    if candidate.exists():
        n = 2
        while (base_dir / f"{slug}-{n}").exists():
            n += 1
        candidate = base_dir / f"{slug}-{n}"
    candidate.mkdir(parents=True)
    atomic_write(candidate / "status.yaml", safe_dump_yaml({"status": "draft"}))
    atomic_write(candidate / "design_notes.md", "")
    atomic_write(candidate / "show_prompt.md", "")
    return candidate


def load_status(show_dir: Path) -> dict:
    """Read and return status dict from status.yaml."""
    return yaml.safe_load((Path(show_dir) / "status.yaml").read_text())


def update_status(show_dir: Path, new_status: str) -> None:
    """Validate status and persist."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of: {', '.join(VALID_STATUSES)}")
    show_dir = Path(show_dir)
    data = load_status(show_dir)
    data["status"] = new_status
    atomic_write(show_dir / "status.yaml", safe_dump_yaml(data))


def append_design_notes(show_dir: Path, text: str) -> None:
    """Append text to design_notes.md with auto-generated routing tags."""
    from backend.services.note_router import route_note

    tags = route_note(text)
    tag_comment = f"<!-- tags: {', '.join(tags)} -->\n"
    path = Path(show_dir) / "design_notes.md"
    with open(path, "a") as f:
        f.write(tag_comment + text + "\n")


def synthesize_prompt(show_dir: Path) -> None:
    """Write a placeholder show_prompt.md."""
    atomic_write(Path(show_dir) / "show_prompt.md", "# Show Prompt\n\nTODO: Synthesize prompt from design notes.\n")


def check_field_ready(show_dir: Path) -> bool:
    """Return True if show status is approved."""
    return load_status(show_dir)["status"] == "approved"
