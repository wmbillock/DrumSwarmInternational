"""Show artifacts persistence layer.

Manages show workspaces on disk with design notes, prompts, and status tracking.
Directory structure: shows/<slug>/design_notes.md + show_prompt.md + status.yaml
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from backend.services.yaml_util import atomic_write, safe_dump_yaml, safe_load_yaml_dict

VALID_STATUSES = ("draft", "needs_review", "approved", "rejected", "published", "on_tour", "completed")


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
    return safe_load_yaml_dict((Path(show_dir) / "status.yaml").read_text(), {"status": "draft"})


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
    """Synthesize show_prompt.md from spec.md and design_notes.md.

    Reads the spec and design notes, extracts tagged sections, and assembles
    a structured prompt with the sections required by the prompt linter.
    """
    show_dir = Path(show_dir)
    spec = read_spec(show_dir)
    notes_path = show_dir / "design_notes.md"
    notes = notes_path.read_text() if notes_path.exists() else ""

    # Parse design notes into tag-grouped content
    tagged: dict[str, list[str]] = {}
    current_tags: list[str] = []
    current_lines: list[str] = []

    for line in notes.splitlines():
        tag_match = re.match(r"^<!--\s*tags:\s*(.+?)\s*-->$", line)
        if tag_match:
            if current_lines and current_tags:
                text = "\n".join(current_lines).strip()
                if text:
                    for t in current_tags:
                        tagged.setdefault(t, []).append(text)
            current_tags = [t.strip() for t in tag_match.group(1).split(",")]
            current_lines = []
        else:
            current_lines.append(line)

    # Flush last block
    if current_lines and current_tags:
        text = "\n".join(current_lines).strip()
        if text:
            for t in current_tags:
                tagged.setdefault(t, []).append(text)

    # Extract title from spec front matter or first heading
    title = "Show Prompt"
    if spec:
        heading_match = re.match(r"^#\s+(.+)$", spec, re.MULTILINE)
        if heading_match:
            title = heading_match.group(1).strip()

    # Map design note tags to prompt sections
    tag_to_section = {
        "music_writer": "Musical Design",
        "drill_writer": "Visual Design",
        "choreographer": "Guard Design",
        "program_coordinator": "Show Concept",
        "general_effect": "General Effect",
    }

    section_content: dict[str, list[str]] = {}
    for tag, entries in tagged.items():
        section_name = tag_to_section.get(tag)
        if section_name:
            section_content.setdefault(section_name, []).extend(entries)

    # Build prompt
    parts = [f"# {title}\n"]

    # Show Concept — from spec summary or program_coordinator notes
    concept_parts = section_content.get("Show Concept", [])
    if spec:
        # Use first paragraph of spec (after title) as concept basis
        spec_lines = spec.splitlines()
        body_lines = []
        past_title = False
        for sl in spec_lines:
            if not past_title and sl.startswith("# "):
                past_title = True
                continue
            if past_title and sl.startswith("## "):
                break
            if past_title:
                body_lines.append(sl)
        spec_intro = "\n".join(body_lines).strip()
        if spec_intro:
            concept_parts.insert(0, spec_intro)
    parts.append("## Show Concept\n")
    parts.append("\n\n".join(concept_parts) if concept_parts else "Derived from spec and design discussions.\n")

    # Musical, Visual, Guard, General Effect
    for section_name in ["Musical Design", "Visual Design", "Guard Design", "General Effect"]:
        parts.append(f"\n\n## {section_name}\n")
        entries = section_content.get(section_name, [])
        parts.append("\n\n".join(entries) if entries else f"No {section_name.lower()} notes captured yet.\n")

    # Constraints — from spec if available
    parts.append("\n\n## Constraints\n")
    constraints = []
    if spec:
        constraint_match = re.search(r"##\s+Constraints?\s*\n(.*?)(?=\n##|\Z)", spec, re.DOTALL)
        if constraint_match:
            constraints.append(constraint_match.group(1).strip())
    if not constraints:
        constraints.append("- Follow standard DCI timing and scoring guidelines\n- Adhere to corps resource limits")
    parts.append("\n".join(constraints))

    # Deliverables
    parts.append("\n\n## Deliverables\n")
    deliverables = []
    if spec:
        deliv_match = re.search(r"##\s+Deliverables?\s*\n(.*?)(?=\n##|\Z)", spec, re.DOTALL)
        if deliv_match:
            deliverables.append(deliv_match.group(1).strip())
    if not deliverables:
        deliverables.append("- Completed show design with all sections finalized\n- Performance-ready prompt for agent execution")
    parts.append("\n".join(deliverables))

    # Evaluation Rubric
    parts.append("\n\n## Evaluation Rubric\n")
    rubric = []
    if spec:
        rubric_match = re.search(r"##\s+Evaluation Rubric\s*\n(.*?)(?=\n##|\Z)", spec, re.DOTALL)
        if rubric_match:
            rubric.append(rubric_match.group(1).strip())
    if not rubric:
        rubric.append("- Judges will evaluate musical performance, visual execution, guard work, and general effect\n- Scores are 0-100 per caption with composite weighting")
    parts.append("\n".join(rubric))

    parts.append("\n")
    atomic_write(show_dir / "show_prompt.md", "\n".join(parts))


def read_summary(show_dir: Path) -> str:
    """Read the humorous summary from status.yaml. Returns empty string if none."""
    data = load_status(show_dir)
    return data.get("summary", "")


def write_summary(show_dir: Path, summary: str) -> None:
    """Write a humorous summary to status.yaml."""
    show_dir = Path(show_dir)
    data = load_status(show_dir)
    data["summary"] = summary
    atomic_write(show_dir / "status.yaml", safe_dump_yaml(data))


def check_field_ready(show_dir: Path) -> bool:
    """Return True if show status is approved or published."""
    return load_status(show_dir)["status"] in ("approved", "published")


# ---------------------------------------------------------------------------
# Spec persistence (Design Room)
# ---------------------------------------------------------------------------

def read_spec(show_dir: Path) -> str:
    """Read spec.md from a show directory. Returns empty string if not found."""
    spec_path = Path(show_dir) / "spec.md"
    if not spec_path.exists():
        return ""
    return spec_path.read_text()


def write_spec(show_dir: Path, content: str) -> None:
    """Write spec.md to a show directory."""
    atomic_write(Path(show_dir) / "spec.md", content)


def approve_spec(show_dir: Path) -> dict:
    """Freeze current spec as a versioned copy and mark show approved.

    Returns dict with version number and path.
    Raises ValueError if spec is empty or missing.
    """
    show_dir = Path(show_dir)
    content = read_spec(show_dir)
    if not content.strip():
        raise ValueError("Cannot approve an empty spec")

    # Determine next version number
    existing = list_spec_versions(show_dir)
    version = (max(existing) + 1) if existing else 1

    # Inject provenance into front matter if present
    now = datetime.now(timezone.utc).isoformat()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = safe_load_yaml_dict(parts[1])
            fm["approved_at"] = now
            fm["approved_by"] = "user"
            fm["version"] = version
            frozen_content = "---\n" + safe_dump_yaml(fm) + "---" + parts[2]
        else:
            frozen_content = content
    else:
        frozen_content = content

    # Write versioned copy
    versioned_path = show_dir / f"spec_v{version}.md"
    atomic_write(versioned_path, frozen_content)

    # Update status
    update_status(show_dir, "approved")

    return {"version": version, "path": str(versioned_path)}


def list_spec_versions(show_dir: Path) -> list[int]:
    """Return sorted list of approved spec version numbers."""
    show_dir = Path(show_dir)
    versions = []
    for f in show_dir.iterdir():
        m = re.match(r"^spec_v(\d+)\.md$", f.name)
        if m:
            versions.append(int(m.group(1)))
    return sorted(versions)


# ---------------------------------------------------------------------------
# Show CRUD helpers (used by V1 API router)
# ---------------------------------------------------------------------------

def _shows_base_dir() -> Path:
    """Return the project-level shows/ directory."""
    import os
    root = os.environ.get("DCI_PROJECT_ROOT", "")
    if root:
        return Path(root) / "shows"
    return Path("shows")


def list_shows() -> list[dict]:
    """List all shows from filesystem, returning slug + status + metadata."""
    base = _shows_base_dir()
    if not base.exists():
        return []
    results = []
    for d in sorted(base.iterdir()):
        status_file = d / "status.yaml"
        if not d.is_dir() or not status_file.exists():
            continue
        data = safe_load_yaml_dict(status_file.read_text())
        spec_text = read_spec(d)
        title = d.name
        if spec_text:
            heading = re.match(r"^#\s+(.+)$", spec_text, re.MULTILINE)
            if heading:
                title = heading.group(1).strip()
        results.append({
            "slug": d.name,
            "title": title,
            "status": data.get("status", "draft"),
            "has_spec": bool(spec_text.strip()),
            "has_prompt": (d / "show_prompt.md").exists() and (d / "show_prompt.md").stat().st_size > 0,
            "summary": data.get("summary", ""),
        })
    return results


def get_show(slug: str) -> dict | None:
    """Get a single show's details by slug."""
    show_dir = _shows_base_dir() / slug
    status_file = show_dir / "status.yaml"
    if not show_dir.exists() or not status_file.exists():
        return None
    data = safe_load_yaml_dict(status_file.read_text())
    spec_text = read_spec(show_dir)
    title = slug
    if spec_text:
        heading = re.match(r"^#\s+(.+)$", spec_text, re.MULTILINE)
        if heading:
            title = heading.group(1).strip()
    return {
        "slug": slug,
        "title": title,
        "status": data.get("status", "draft"),
        "has_spec": bool(spec_text.strip()),
        "has_prompt": (show_dir / "show_prompt.md").exists() and (show_dir / "show_prompt.md").stat().st_size > 0,
        "versions": list_spec_versions(show_dir),
    }


def update_show_status(slug: str, new_status: str) -> None:
    """Update a show's status by slug. Updates filesystem status.yaml."""
    show_dir = _shows_base_dir() / slug
    if not show_dir.exists():
        raise ValueError(f"Show '{slug}' not found")
    update_status(show_dir, new_status)
