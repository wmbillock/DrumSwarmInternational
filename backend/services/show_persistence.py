"""Show artifacts persistence layer.

Manages show workspaces on disk with design notes, prompts, and status tracking.
Directory structure: shows/<slug>/design_notes.md + show_prompt.md + status.yaml
"""

import os
import re
import tempfile
from pathlib import Path

import yaml

VALID_STATUSES = ("draft", "needs_review", "approved", "rejected")


def _atomic_write(path: Path, content: str) -> None:
    """Write content to path atomically via tmp+rename."""
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
    _atomic_write(candidate / "status.yaml", yaml.dump({"status": "draft"}, default_flow_style=False))
    _atomic_write(candidate / "design_notes.md", "")
    _atomic_write(candidate / "show_prompt.md", "")
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
    _atomic_write(show_dir / "status.yaml", yaml.dump(data, default_flow_style=False))


def append_design_notes(show_dir: Path, text: str) -> None:
    """Append text to design_notes.md."""
    path = Path(show_dir) / "design_notes.md"
    with open(path, "a") as f:
        f.write(text + "\n")


def synthesize_prompt(show_dir: Path) -> None:
    """Write a placeholder show_prompt.md."""
    _atomic_write(Path(show_dir) / "show_prompt.md", "# Show Prompt\n\nTODO: Synthesize prompt from design notes.\n")


def check_field_ready(show_dir: Path) -> bool:
    """Return True if show status is approved."""
    return load_status(show_dir)["status"] == "approved"
