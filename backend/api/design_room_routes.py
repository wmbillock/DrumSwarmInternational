"""Design Room API routes — spec CRUD, conversation, and approval."""

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.services.show_persistence import (
    create_show,
    read_spec,
    write_spec,
    approve_spec,
    list_spec_versions,
    slugify,
)
from backend.services.note_router import route_note
from backend.services.yaml_util import atomic_write, safe_dump_yaml

router = APIRouter()

TAG_TO_ROLE = {
    "music": "music_writer",
    "visual": "drill_writer",
    "guard": "choreographer",
    "ge": "program_coordinator",
    "admin": "program_coordinator",
    "questions": "program_coordinator",
}


def _get_shows_dir() -> Path:
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve() / "shows"
    from backend.cli.commands.doctor import _find_project_root
    return Path(_find_project_root()) / "shows"


def _validate_slug(slug: str) -> None:
    if ".." in slug or "/" in slug or "\\" in slug:
        raise HTTPException(400, "Invalid show slug")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        raise HTTPException(400, "Invalid show slug")


def _show_dir(slug: str) -> Path:
    _validate_slug(slug)
    d = _get_shows_dir() / slug
    if not d.exists():
        raise HTTPException(404, f"Show '{slug}' not found")
    return d


# --- Pydantic models ---

class DesignShowCreate(BaseModel):
    title: str

class SpecUpdate(BaseModel):
    content: str

class ConversationMessage(BaseModel):
    message: str
    role_hint: Optional[str] = None


# --- Endpoints ---

@router.post("/api/design/shows")
def api_create_design_show(data: DesignShowCreate):
    """Create a new show workspace with an empty spec."""
    shows_dir = _get_shows_dir()
    shows_dir.mkdir(parents=True, exist_ok=True)
    show_dir = create_show(data.title, shows_dir)
    slug = show_dir.name

    # Create initial empty spec with front matter
    now = datetime.now(timezone.utc).isoformat()
    initial_spec = f"""---
show_slug: {slug}
version: 1
created_at: "{now}"
approved_at: null
approved_by: null
roles_consulted: []
model: null
run_id: null
---

# {data.title}

## Decisions

## Open Questions

## Constraints
"""
    write_spec(show_dir, initial_spec)
    return {"slug": slug, "path": str(show_dir)}


@router.get("/api/design/shows/{slug}/spec")
def api_get_spec(slug: str):
    """Read current spec.md for a show."""
    show_dir = _show_dir(slug)
    return {"content": read_spec(show_dir)}


@router.put("/api/design/shows/{slug}/spec")
def api_update_spec(slug: str, data: SpecUpdate):
    """Update spec.md content."""
    show_dir = _show_dir(slug)
    write_spec(show_dir, data.content)
    return {"status": "updated"}


@router.post("/api/design/shows/{slug}/conversation")
def api_conversation(slug: str, data: ConversationMessage):
    """Route a design message, append to design_notes, return tags + role."""
    show_dir = _show_dir(slug)

    # Tag the message
    tags = route_note(data.message)

    # Determine primary role from tags
    if data.role_hint and data.role_hint in TAG_TO_ROLE.values():
        role = data.role_hint
    else:
        role = TAG_TO_ROLE.get(tags[0], "program_coordinator") if tags else "program_coordinator"

    # Append to design_notes.md
    notes_path = show_dir / "design_notes.md"
    tag_comment = f"<!-- tags: {', '.join(tags)} -->\n"
    entry = f"\n**[user]** {data.message}\n"
    with open(notes_path, "a") as f:
        f.write(tag_comment + entry)

    return {
        "role": role,
        "tags": tags,
        "response": f"[{role}] Noted. Tags: {', '.join(tags)}.",
        "spec_updates": {
            "decisions": [],
            "open_questions": [],
            "constraints": [],
        },
    }


@router.post("/api/design/shows/{slug}/approve")
def api_approve(slug: str):
    """Freeze spec and commission show."""
    show_dir = _show_dir(slug)
    try:
        result = approve_spec(show_dir)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@router.get("/api/design/shows/{slug}/versions")
def api_list_versions(slug: str):
    """List approved spec versions."""
    show_dir = _show_dir(slug)
    return {"versions": list_spec_versions(show_dir)}
