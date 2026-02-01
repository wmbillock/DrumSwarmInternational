"""V1 API router — thin adapters over existing service modules.

All business logic lives in backend/services/. These routes only translate
HTTP ↔ service calls and enforce slug/id validation.
"""

import logging
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_root() -> Path:
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    from backend.cli.commands.doctor import _find_project_root
    return Path(_find_project_root())


def _validate_id(value: str, label: str = "id") -> None:
    """Reject path-traversal attempts and non-slug characters."""
    if ".." in value or "/" in value or "\\" in value:
        raise HTTPException(400, f"Invalid {label}: must not contain path separators")
    if not value:
        raise HTTPException(400, f"Invalid {label}: must not be empty")
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$", value):
        raise HTTPException(
            400,
            f"Invalid {label}: '{value}' must start with a letter or digit and contain only letters, digits, dots, underscores, or hyphens",
        )


# =========================================================================
# CORPS
# =========================================================================

def _get_db_session():
    """Get a SQLAlchemy session for DB fallback queries."""
    from backend.api.app import SessionFactory
    return SessionFactory()


@router.get("/corps")
def v1_list_corps(include_system: bool = False):
    """List all corps from filesystem workspaces + DB, deduplicated by display_name."""
    root = _get_root()
    corps_base = root / "corps"
    result = []
    seen_names: set[str] = set()

    # Filesystem corps
    if corps_base.exists():
        for corps_dir in sorted(corps_base.iterdir()):
            corps_path = corps_dir / "corps.yaml"
            if not corps_path.is_file():
                continue
            try:
                data = yaml.safe_load(corps_path.read_text())
                name = data.get("display_name", corps_dir.name)
                seen_names.add(name)
                result.append({
                    "corps_id": data.get("corps_id", corps_dir.name),
                    "display_name": name,
                    "philosophy": data.get("philosophy", ""),
                    "state": data.get("state", "unknown"),
                    "corps_type": data.get("corps_type", "competing"),
                })
            except Exception:
                continue

    # DB corps (merge, dedup by display_name)
    try:
        from backend.models.corps import Corps, CorpsStatus
        db = _get_db_session()
        try:
            query = db.query(Corps).filter(Corps.status != CorpsStatus.DISBANDED)
            if not include_system:
                query = query.filter(
                    (Corps.corps_type != "system") | (Corps.corps_type.is_(None))
                )
            db_corps = query.all()
            for c in db_corps:
                if c.name not in seen_names:
                    seen_names.add(c.name)
                    result.append({
                        "corps_id": c.id,
                        "display_name": c.name,
                        "philosophy": "",
                        "state": c.status.value if c.status else "unknown",
                        "corps_type": c.corps_type or "competing",
                    })
        finally:
            db.close()
    except Exception:
        pass  # DB unavailable — filesystem-only mode

    return result


MAX_CORPS = 18  # DCI semifinals cap


def _generate_color_scheme(seed: str) -> dict:
    """Generate a deterministic DCI-inspired color scheme from a seed string."""
    h = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    # Use golden ratio to spread hues
    hue = (h % 360)
    import colorsys
    # Primary: dark, saturated
    r, g, b = colorsys.hls_to_rgb(hue / 360.0, 0.25, 0.7)
    primary = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    # Secondary: medium
    r, g, b = colorsys.hls_to_rgb(((hue + 30) % 360) / 360.0, 0.45, 0.5)
    secondary = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    # Accent: bright
    r, g, b = colorsys.hls_to_rgb(((hue + 180) % 360) / 360.0, 0.55, 0.8)
    accent = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    return {"primary": primary, "secondary": secondary, "accent": accent}


_UNIFORM_STYLES = [
    "Military-inspired with braided epaulettes and sash",
    "Sleek modern design with asymmetric color blocking",
    "Classic corps style with plumed shako and gauntlets",
    "Contemporary athleisure with gradient panels",
    "Renaissance-inspired with tabard and metallic accents",
    "Space-age futuristic with reflective piping",
    "Western cavalry motif with fringe and concho details",
    "Art deco geometric patterns with gold trim",
    "Japanese-inspired hakama silhouette with obi sash",
    "Steampunk Victorian with brass fittings and goggles",
]

_ICON_THEMES = [
    "heraldic shield", "winged emblem", "celestial star burst",
    "crossed instruments", "flame and laurel wreath", "geometric mandala",
    "stylized animal crest", "art nouveau flourish", "modernist abstract mark",
    "military insignia with musical notation",
]


@router.post("/corps/generate-identity")
def v1_generate_corps_identity():
    """Auto-generate a complete corps identity for preview."""
    from backend.services.nickname_generator import generate_corps_name, generate_mascot
    import json as _json

    # Gather existing names to avoid duplicates
    existing_names: set[str] = set()
    try:
        from backend.models.corps import Corps
        db = _get_db_session()
        try:
            for c in db.query(Corps.name).all():
                existing_names.add(c[0])
        finally:
            db.close()
    except Exception:
        pass

    name = generate_corps_name(existing_names)
    mascot = generate_mascot(existing_names)
    colors = _generate_color_scheme(name)

    import random
    uniform = random.choice(_UNIFORM_STYLES)
    icon_theme = random.choice(_ICON_THEMES)

    icon_prompt = (
        f"Design a {icon_theme} logo for a drum corps called '{name}' "
        f"with mascot '{mascot}'. Use colors: {colors['primary']}, "
        f"{colors['secondary']}, and {colors['accent']}. "
        f"Style: clean vector art, suitable for embroidery on uniforms. "
        f"No text in the image."
    )

    return {
        "name": name,
        "mascot": mascot,
        "color_scheme": colors,
        "uniform_concept": uniform,
        "icon_theme": icon_theme,
        "icon_prompt": icon_prompt,
    }


class GenerateIconRequest(BaseModel):
    icon_prompt: str


@router.post("/corps/generate-icon")
def v1_generate_corps_icon(req: GenerateIconRequest):
    """Use ChatGPT CLI to generate an icon description or image."""
    import shutil
    if not shutil.which("chatgpt"):
        return {
            "source": "fallback",
            "description": (
                "A bold heraldic emblem rendered in the corps colors, "
                "featuring the mascot in a dynamic pose surrounded by "
                "musical motifs and geometric framing."
            ),
            "image_url": None,
        }

    from backend.services.llm_client import ChatGPTCLIClient, LLMMessage
    from backend.models.agent_definition import ModelTier
    client = ChatGPTCLIClient()
    resp = client.chat(
        messages=[
            LLMMessage(role="system", content=(
                "You are a visual designer. Describe a corps logo based on the prompt. "
                "Output a vivid 2-3 sentence description of the logo design. "
                "If you can generate an image, include the URL."
            )),
            LLMMessage(role="user", content=req.icon_prompt),
        ],
        model_tier=ModelTier.SONNET,
    )
    return {
        "source": "chatgpt",
        "description": resp.content,
        "image_url": None,
    }


class CreateCorpsRequest(BaseModel):
    name: str
    mascot: Optional[str] = None
    color_scheme: Optional[dict] = None
    uniform_concept: Optional[str] = None
    philosophy: Optional[str] = ""


@router.post("/corps")
def v1_create_corps(req: CreateCorpsRequest):
    """Create a new corps via the DB. Enforces an 18-corps cap."""
    from backend.models.corps import Corps, CorpsStatus, CorpsMode
    import json as _json

    db = _get_db_session()
    try:
        active_count = db.query(Corps).filter(
            Corps.status != CorpsStatus.DISBANDED
        ).count()
        if active_count >= MAX_CORPS:
            raise HTTPException(400, f"Maximum of {MAX_CORPS} active corps reached")

        # Check for name uniqueness
        existing = db.query(Corps).filter(Corps.name == req.name).first()
        if existing:
            raise HTTPException(409, f"Corps '{req.name}' already exists")

        import uuid
        corps_id = str(uuid.uuid4())

        # Store color scheme + uniform concept together
        theme_data = {}
        if req.color_scheme:
            theme_data["color_scheme"] = req.color_scheme
        if req.uniform_concept:
            theme_data["uniform_concept"] = req.uniform_concept

        corps = Corps(
            id=corps_id,
            name=req.name,
            status=CorpsStatus.WINTER_CAMPS,
            mode=CorpsMode.DESIGN_ROOM,
            mascot=req.mascot,
            uniform_concept=_json.dumps(theme_data) if theme_data else None,
        )
        db.add(corps)
        db.commit()

        return {
            "corps_id": corps_id,
            "display_name": req.name,
            "mascot": req.mascot,
            "color_scheme": req.color_scheme,
            "uniform_concept": req.uniform_concept,
            "philosophy": req.philosophy or "",
            "state": "winter_camps",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create corps: {e}")
    finally:
        db.close()


@router.get("/corps/{corps_id}")
def v1_get_corps(corps_id: str):
    """Get corps detail including roster size and history. Falls back to DB for UUID lookups."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    corps_path = root / "corps" / corps_id / "corps.yaml"
    if corps_path.is_file():
        data = yaml.safe_load(corps_path.read_text())
        roster_path = root / "corps" / corps_id / "roster.yaml"
        roster_size = 0
        if roster_path.is_file():
            roster = yaml.safe_load(roster_path.read_text())
            roster_size = len(roster.get("assignments", []))
        history = data.get("history", [])
        return {
            "corps_id": data.get("corps_id", corps_id),
            "display_name": data.get("display_name", corps_id),
            "philosophy": data.get("philosophy", ""),
            "state": data.get("state", "unknown"),
            "roster_size": roster_size,
            "history_count": len(history),
            "history": history,
        }

    # Fallback: query DB for this UUID
    try:
        from backend.models.corps import Corps
        from backend.models.show import Show
        from backend.models.agent_session import AgentSession, SessionStatus
        db = _get_db_session()
        try:
            corps = db.get(Corps, corps_id)
            if not corps:
                raise HTTPException(404, f"Corps '{corps_id}' not found")
            roster_size = db.query(AgentSession).filter(
                AgentSession.corps_id == corps_id,
                AgentSession.status == SessionStatus.ACTIVE
            ).count()

            # Find linked show
            show_info = None
            if corps.show_id:
                show = db.get(Show, corps.show_id)
                if show:
                    show_info = {
                        "show_id": show.id,
                        "title": show.title,
                        "status": show.status.value,
                        "description": show.description,
                    }
            # Also check if any show references this corps
            if not show_info:
                show = db.query(Show).filter(Show.corps_id == corps_id).first()
                if show:
                    show_info = {
                        "show_id": show.id,
                        "title": show.title,
                        "status": show.status.value,
                        "description": show.description,
                    }

            return {
                "corps_id": corps.id,
                "display_name": corps.name,
                "philosophy": "",
                "state": corps.status.value if corps.status else "unknown",
                "roster_size": roster_size,
                "history_count": 0,
                "history": [],
                "mascot": corps.mascot,
                "theme_id": corps.theme_id,
                "mode": corps.mode.value if corps.mode else None,
                "rehearsal_mode": corps.rehearsal_mode.value if corps.rehearsal_mode else None,
                "current_show": show_info,
            }
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404, f"Corps '{corps_id}' not found")


@router.post("/corps/{corps_id}/ready-for-contest")
def v1_ready_for_contest(corps_id: str):
    """Transition a corps from ON_TOUR to READY_FOR_CONTEST."""
    _validate_id(corps_id, "corps_id")
    from backend.models.corps import Corps, CorpsStatus

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, f"Corps '{corps_id}' not found")
        if corps.status != CorpsStatus.ON_TOUR:
            raise HTTPException(
                400,
                f"Corps must be ON_TOUR to become READY_FOR_CONTEST (current: {corps.status.value})",
            )
        corps.status = CorpsStatus.READY_FOR_CONTEST
        db.commit()
        return {
            "corps_id": corps.id,
            "display_name": corps.name,
            "state": corps.status.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to transition corps: {e}")
    finally:
        db.close()


@router.post("/corps/{corps_id}/return-to-tour")
def v1_return_to_tour(corps_id: str):
    """Return a corps from READY_FOR_CONTEST back to ON_TOUR for rework."""
    _validate_id(corps_id, "corps_id")
    from backend.models.corps import Corps, CorpsStatus

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, f"Corps '{corps_id}' not found")
        if corps.status != CorpsStatus.READY_FOR_CONTEST:
            raise HTTPException(
                400,
                f"Corps must be READY_FOR_CONTEST to return to tour (current: {corps.status.value})",
            )
        corps.status = CorpsStatus.ON_TOUR
        db.commit()
        return {
            "corps_id": corps.id,
            "display_name": corps.name,
            "state": corps.status.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to transition corps: {e}")
    finally:
        db.close()


@router.post("/corps/{corps_id}/complete")
def v1_complete_corps(corps_id: str):
    """Complete a corps season — transition from READY_FOR_CONTEST to COMPLETED."""
    _validate_id(corps_id, "corps_id")
    from backend.models.corps import Corps, CorpsStatus, RehearsalMode
    from backend.models.segment import Segment, SegmentStatus
    from backend.models.rep import Rep
    from backend.models.agent_session import AgentSession

    db = _get_db_session()
    try:
        from backend.services.corps_service import complete_corps as complete_corps_service
        corps = complete_corps_service(db, corps_id)
        return {
            "corps_id": corps.id,
            "display_name": corps.name,
            "state": corps.status.value,
            "message": "Corps season completed successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to complete corps: {e}")
    finally:
        db.close()


# =========================================================================
# RUNS
# =========================================================================

@router.get("/runs")
def v1_list_runs(corps_id: Optional[str] = None):
    """List all run manifests across seasons. Optionally filter by corps_id."""
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []
    if corps_id:
        _validate_id(corps_id, "corps_id")
    runs = []
    for season_dir in seasons_dir.iterdir():
        if not season_dir.is_dir():
            continue
        perf_root = season_dir / "performances"
        if not perf_root.exists():
            continue
        for corps_dir in perf_root.iterdir():
            if not corps_dir.is_dir():
                continue
            if corps_id and corps_dir.name != corps_id:
                continue
            for run_dir in corps_dir.iterdir():
                manifest_path = run_dir / "manifest.yaml"
                if not manifest_path.is_file():
                    continue
                try:
                    manifest = yaml.safe_load(manifest_path.read_text())
                    if isinstance(manifest, dict) and "run_id" in manifest:
                        runs.append(manifest)
                except Exception:
                    continue
    runs.sort(key=lambda r: r.get("started_at", ""), reverse=True)
    return runs


@router.get("/runs/{run_id}")
def v1_get_run(run_id: str):
    """Get run manifest + output."""
    _validate_id(run_id, "run_id")
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        raise HTTPException(404, f"Run '{run_id}' not found")
    for season_dir in seasons_dir.iterdir():
        if not season_dir.is_dir():
            continue
        perf_root = season_dir / "performances"
        if not perf_root.exists():
            continue
        for corps_dir in perf_root.iterdir():
            if not corps_dir.is_dir():
                continue
            run_dir = corps_dir / run_id
            manifest_path = run_dir / "manifest.yaml"
            if manifest_path.is_file():
                manifest = yaml.safe_load(manifest_path.read_text())
                output = ""
                output_path = run_dir / "output.txt"
                if output_path.is_file():
                    output = output_path.read_text()[:10000]
                return {**manifest, "output": output}
    raise HTTPException(404, f"Run '{run_id}' not found")


@router.get("/runs/{run_id}/logs")
def v1_get_run_logs(run_id: str):
    """Get run output log."""
    _validate_id(run_id, "run_id")
    root = _get_root()
    seasons_dir = root / "seasons"
    if seasons_dir.exists():
        for season_dir in seasons_dir.iterdir():
            if not season_dir.is_dir():
                continue
            perf_root = season_dir / "performances"
            if not perf_root.exists():
                continue
            for corps_dir in perf_root.iterdir():
                if not corps_dir.is_dir():
                    continue
                output_path = corps_dir / run_id / "output.txt"
                if output_path.is_file():
                    return {"run_id": run_id, "log": output_path.read_text()[:50000]}
    raise HTTPException(404, f"Run '{run_id}' not found")


class StartRunRequest(BaseModel):
    show_slug: str
    corps_id: str
    season_id: str


@router.post("/runs")
def v1_start_run(req: StartRunRequest):
    """Start a show run — creates manifest, executes stub, returns run_id."""
    root = _get_root()

    show_dir = root / "shows" / req.show_slug
    if not (show_dir / "status.yaml").exists():
        raise HTTPException(404, f"Show '{req.show_slug}' not found")
    from backend.services.show_persistence import check_field_ready
    if not check_field_ready(show_dir):
        raise HTTPException(400, f"Show '{req.show_slug}' is not approved")

    # Validate corps exists (filesystem or DB)
    corps_dir = root / "corps" / req.corps_id
    if not (corps_dir / "corps.yaml").exists():
        try:
            from backend.models.corps import Corps
            db = _get_db_session()
            try:
                if not db.get(Corps, req.corps_id):
                    raise HTTPException(404, f"Corps '{req.corps_id}' not found")
            finally:
                db.close()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(404, f"Corps '{req.corps_id}' not found")

    season_dir = root / "seasons" / req.season_id
    if not (season_dir / "season.yaml").exists():
        raise HTTPException(404, f"Season '{req.season_id}' not found")

    from backend.services.yaml_util import atomic_write, safe_dump_yaml
    from backend.services.runtime_config import get_runtime_config

    config = get_runtime_config()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = f"{req.show_slug}-{req.corps_id}-{ts}"
    run_dir = season_dir / "performances" / req.corps_id / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "run_id": run_id,
        "show_slug": req.show_slug,
        "corps_id": req.corps_id,
        "season_id": req.season_id,
        "started_at": started_at,
        "status": "running",
        "config": config,
        "inputs": {"show_dir": str(show_dir), "corps_dir": str(corps_dir)},
        "outputs": [],
    }
    atomic_write(run_dir / "manifest.yaml", safe_dump_yaml(manifest))

    # Execution stub
    (run_dir / "output.txt").write_text(f"Stub execution for show '{req.show_slug}'\n")

    manifest["status"] = "completed"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest["outputs"] = ["output.txt"]
    atomic_write(run_dir / "manifest.yaml", safe_dump_yaml(manifest))

    return {"run_id": run_id, "status": "completed"}


# =========================================================================
# DESIGN ROOM
# =========================================================================

class CreateThreadRequest(BaseModel):
    title: str


class PostMessageRequest(BaseModel):
    message: str
    role_hint: Optional[str] = None


class UpdateSpecRequest(BaseModel):
    content: str


def _shows_dir() -> Path:
    root = _get_root()
    d = root / "shows"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _validate_slug(slug: str) -> None:
    if ".." in slug or "/" in slug or "\\" in slug:
        raise HTTPException(400, "Invalid show slug")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        raise HTTPException(400, "Invalid show slug")


def _show_dir(slug: str) -> Path:
    _validate_slug(slug)
    d = _shows_dir() / slug
    if not d.exists():
        raise HTTPException(404, f"Show '{slug}' not found")
    return d


@router.post("/design/threads")
def v1_create_thread(req: CreateThreadRequest):
    """Create a new design thread (show workspace + empty spec)."""
    from backend.services.show_persistence import create_show, write_spec
    shows_dir = _shows_dir()
    show_dir = create_show(req.title, shows_dir)
    slug = show_dir.name

    now = datetime.now(timezone.utc).isoformat()
    initial_spec = (
        f"---\nshow_slug: {slug}\nversion: 1\ncreated_at: \"{now}\"\n"
        f"approved_at: null\napproved_by: null\nroles_consulted: []\n---\n\n"
        f"# {req.title}\n\n## Decisions\n\n## Open Questions\n\n## Constraints\n"
    )
    write_spec(show_dir, initial_spec)
    return {"slug": slug, "path": str(show_dir)}


@router.get("/design/threads")
def v1_list_threads():
    """List all design threads (show workspaces that have a status file)."""
    shows_dir = _shows_dir()
    threads = []
    for d in sorted(shows_dir.iterdir()):
        if not d.is_dir():
            continue
        status_path = d / "status.yaml"
        if not status_path.exists():
            continue
        status = yaml.safe_load(status_path.read_text())
        threads.append({
            "slug": d.name,
            "status": status.get("status", "unknown"),
            "has_spec": (d / "spec.md").exists(),
            "summary": status.get("summary", ""),
        })
    return threads


@router.get("/design/threads/{slug}/messages")
def v1_get_thread_messages(slug: str):
    """Get design notes for a thread (parsed as messages)."""
    show_dir = _show_dir(slug)
    notes_path = show_dir / "design_notes.md"
    if not notes_path.exists():
        return {"slug": slug, "messages": []}
    content = notes_path.read_text()
    messages = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("<!-- tags:"):
            tags_str = line.replace("<!-- tags:", "").replace("-->", "").strip()
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines):
                msg_line = lines[i].strip()
                m = re.match(r"\*\*\[(\w+)\]\*\*\s*(.*)", msg_line)
                if m:
                    messages.append({
                        "role": m.group(1),
                        "content": m.group(2),
                        "tags": tags,
                    })
        i += 1
    return {"slug": slug, "messages": messages}


_DESIGN_ROLE_PROMPTS = {
    "music_writer": (
        "You are the Music Arranger — the person who hears a director say 'I want something epic' "
        "and comes back with keys, tempos, and a brass book. Talk like a colleague in a planning "
        "meeting, not a spec document. When the director is vague, pitch a specific idea "
        "('What about a ballad in Db at 72 bpm?') and let them react."
    ),
    "drill_writer": (
        "You are the Drill Designer — you think in formations, transitions, and spatial flow. "
        "Talk like you're sketching on a whiteboard with the director, not narrating a manual. "
        "When something is vague, propose a concrete visual ('Company front into a pinwheel "
        "at the brass hit?') and let the director react."
    ),
    "choreographer": (
        "You are the Guard Choreographer — you live in the world of silk, sabre, and movement. "
        "Talk like a creative partner brainstorming in a gym, not writing a rubric. "
        "When the director is vague, propose something specific ('Triple on the downbeat of "
        "measure 16, rifle exchange into the closer?') and let them steer."
    ),
    "program_coordinator": (
        "You are the Program Coordinator — the person who keeps the whole show coherent. "
        "You track what's decided vs. what's still foggy, and you push for the details agents "
        "will need. Talk like a lead designer in a production meeting: direct, practical, no fluff."
    ),
}

_DESIGN_ROLE_DISPLAY = {
    "music_writer": "Music Arranger",
    "drill_writer": "Drill Designer",
    "choreographer": "Guard Choreographer",
    "program_coordinator": "Program Coordinator",
}

_DESIGN_SYSTEM_TEMPLATE = """You're on the design staff for show "{slug}". Have a natural conversation with the director.

{role_prompt}

WHAT YOU KNOW SO FAR (the Brief):
{spec_content}

You're working toward two things:
- A **Brief** (the spec) with enough detail that agents can build from it
- A **Swarm Prompt** that tells the agent swarm exactly what to do

HOW TO TALK:
- 2-4 sentences, like a colleague in a planning meeting
- If the director is vague, pitch a specific idea and let them react
- Build on what's already decided — don't restart from scratch
- When your area is solid, suggest Swarm Prompt language for it
- Never recap what the director just said
"""

_PC_MARSHAL_TEMPLATE = """You're the Program Coordinator for "{slug}".

Here's the Brief so far:
{spec_content}

Recent conversation:
{notes_content}

Director just said: "{user_message}"

Respond in 2-4 sentences. Pick ONE move:
- Turn their input into a concrete Brief update (name the section, state the detail)
- Call out a section that's too vague for agents and propose specific language
- If the Brief is solid, draft Swarm Prompt language
- Ask ONE question only if you're genuinely stuck

Don't recap what they said. Be direct about what's ready and what's not.
"""

_SPEC_UPDATE_TEMPLATE = """Update the show spec (Brief) based on the design conversation.

CURRENT SPEC:
{spec_content}

RECENT CONVERSATION:
{notes_content}

MANDATORY SECTIONS (every spec must have these):
- ## Show Concept
- ## Musical Design
- ## Visual Design
- ## Guard Design
- ## General Effect
- ## Constraints
- ## Deliverables
- ## Swarm Prompt

Write the COMPLETE updated spec in markdown.
- Keep existing content that's still valid
- Incorporate all design decisions from the conversation
- Use professional DCI show design language
- If a section hasn't been discussed, write "TBD — awaiting design input"
- ## Swarm Prompt: synthesize decided sections into an actionable prompt for the agent swarm. Note what's still missing.
- Output ONLY the spec markdown, no preamble
"""


def _get_llm_client():
    """Get the shared LLM client from the task manager.

    The task manager is initialized at app startup (see app.py lifespan)
    with the best available client: Claude CLI > ChatGPT CLI > Anthropic API > Mock.
    """
    try:
        from backend.api.app import get_task_manager
        tm = get_task_manager()
        if tm and hasattr(tm, "llm_client"):
            return tm.llm_client
    except (ImportError, AttributeError):
        pass
    return None


def _llm_chat(llm_client, system_prompt: str, user_message: str) -> str | None:
    """Send a chat to the LLM client and return the response text, or None on failure."""
    try:
        from backend.services.llm_client import LLMMessage
        from backend.models.agent_definition import ModelTier

        resp = llm_client.chat(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_message),
            ],
            model_tier=ModelTier.HAIKU,
        )
        if resp.content and resp.stop_reason != "error":
            return resp.content.strip()
    except Exception:
        pass
    return None


@router.post("/design/threads/{slug}/messages")
def v1_post_thread_message(slug: str, req: PostMessageRequest):
    """Post a message to a design thread — PC marshals the conversation, specialists contribute."""
    show_dir = _show_dir(slug)
    from backend.services.note_router import route_note
    from backend.services.show_persistence import read_spec

    tags = route_note(req.message)

    TAG_TO_ROLE = {
        "music": "music_writer", "visual": "drill_writer",
        "guard": "choreographer", "ge": "program_coordinator",
        "admin": "program_coordinator", "questions": "program_coordinator",
    }

    # Determine which specialists to involve based on tags
    specialist_roles = set()
    for tag in tags:
        role = TAG_TO_ROLE.get(tag)
        if role and role != "program_coordinator":
            specialist_roles.add(role)

    # If user explicitly requested a role, include it
    if req.role_hint and req.role_hint in _DESIGN_ROLE_PROMPTS and req.role_hint != "program_coordinator":
        specialist_roles.add(req.role_hint)

    # Persist user message to design notes
    notes_path = show_dir / "design_notes.md"
    tag_comment = f"<!-- tags: {', '.join(tags)} -->\n"
    entry = f"\n**[user]** {req.message}\n"
    with open(notes_path, "a") as f:
        f.write(tag_comment + entry)

    # Build context
    spec_content = read_spec(show_dir) or "(no spec yet)"
    notes_content = notes_path.read_text() if notes_path.exists() else "(no notes yet)"
    if len(notes_content) > 4000:
        notes_content = "...\n" + notes_content[-4000:]

    responses: list[dict] = []
    llm_client = _get_llm_client()

    if llm_client:
        # 1. Program Coordinator always speaks first — marshals the discussion
        pc_prompt = _PC_MARSHAL_TEMPLATE.format(
            slug=slug,
            spec_content=spec_content[:2000],
            notes_content=notes_content,
            user_message=req.message,
        )
        pc_text = _llm_chat(llm_client, pc_prompt, req.message)
        if pc_text:
            pc_entry = f"\n<!-- tags: {', '.join(tags)} -->\n**[program_coordinator]** {pc_text}\n"
            with open(notes_path, "a") as f:
                f.write(pc_entry)
            responses.append({
                "role": "program_coordinator",
                "display_name": _DESIGN_ROLE_DISPLAY["program_coordinator"],
                "tags": tags,
                "response": pc_text,
            })
            # Re-read notes so specialists see PC's response
            notes_content = notes_path.read_text()
            if len(notes_content) > 4000:
                notes_content = "...\n" + notes_content[-4000:]

        # 2. Specialists contribute if their domain was tagged
        for spec_role in sorted(specialist_roles):
            role_prompt = _DESIGN_ROLE_PROMPTS[spec_role]
            system_prompt = _DESIGN_SYSTEM_TEMPLATE.format(
                role_prompt=role_prompt,
                slug=slug,
                spec_content=spec_content[:2000],
                notes_content=notes_content,
            )
            spec_text = _llm_chat(llm_client, system_prompt, req.message)
            if spec_text:
                spec_entry = f"\n<!-- tags: {', '.join(tags)} -->\n**[{spec_role}]** {spec_text}\n"
                with open(notes_path, "a") as f:
                    f.write(spec_entry)
                responses.append({
                    "role": spec_role,
                    "display_name": _DESIGN_ROLE_DISPLAY.get(spec_role, spec_role),
                    "tags": tags,
                    "response": spec_text,
                })
                # Update notes for subsequent specialists
                notes_content = notes_path.read_text()
                if len(notes_content) > 4000:
                    notes_content = "...\n" + notes_content[-4000:]

    # Fallback if no LLM responses were generated
    if not responses:
        fallback_text = (
            f"I hear you on that. Let me think about how this fits into the overall design. "
            f"(LLM unavailable — connect an LLM backend for full collaborative design sessions.)"
        )
        fb_entry = f"\n<!-- tags: {', '.join(tags)} -->\n**[program_coordinator]** {fallback_text}\n"
        with open(notes_path, "a") as f:
            f.write(fb_entry)
        responses.append({
            "role": "program_coordinator",
            "display_name": _DESIGN_ROLE_DISPLAY["program_coordinator"],
            "tags": tags,
            "response": fallback_text,
        })

    # Auto-update the spec based on the conversation so far
    if llm_client and responses:
        try:
            from backend.services.show_persistence import write_spec
            notes_for_spec = notes_path.read_text() if notes_path.exists() else ""
            if len(notes_for_spec) > 5000:
                notes_for_spec = "...\n" + notes_for_spec[-5000:]
            spec_prompt = _SPEC_UPDATE_TEMPLATE.format(
                spec_content=spec_content,
                notes_content=notes_for_spec,
            )
            updated_spec = _llm_chat(llm_client, spec_prompt, "Update the spec now.")
            if updated_spec and len(updated_spec) > 50:
                write_spec(show_dir, updated_spec)
        except Exception:
            pass  # Spec update is best-effort

    # Return backward-compatible single response + full responses array
    return {
        "role": responses[0]["role"],
        "tags": tags,
        "response": responses[0]["response"],
        "responses": responses,
    }


@router.get("/design/threads/{slug}/artifacts/brief")
def v1_get_brief(slug: str):
    """Get the current show spec (brief)."""
    show_dir = _show_dir(slug)
    from backend.services.show_persistence import read_spec
    content = read_spec(show_dir)
    return {"slug": slug, "content": content}


@router.put("/design/threads/{slug}/artifacts/brief")
def v1_update_brief(slug: str, req: UpdateSpecRequest):
    """Update the show spec (brief)."""
    show_dir = _show_dir(slug)
    from backend.services.show_persistence import write_spec
    write_spec(show_dir, req.content)
    return {"status": "updated"}


@router.get("/design/threads/{slug}/artifacts/prompt")
def v1_get_prompt(slug: str):
    """Get the finalized show prompt markdown."""
    show_dir = _show_dir(slug)
    prompt_path = show_dir / "show_prompt.md"
    content = prompt_path.read_text() if prompt_path.exists() else ""
    return {"slug": slug, "content": content}


@router.put("/design/threads/{slug}/artifacts/prompt")
def v1_update_prompt(slug: str, req: UpdateSpecRequest):
    """Update the show prompt markdown."""
    show_dir = _show_dir(slug)
    from backend.services.yaml_util import atomic_write
    atomic_write(show_dir / "show_prompt.md", req.content)
    return {"status": "updated"}


@router.post("/design/threads/{slug}/lint")
def v1_lint_prompt(slug: str):
    """Run prompt linter on current show_prompt.md."""
    show_dir = _show_dir(slug)
    prompt_path = show_dir / "show_prompt.md"
    content = prompt_path.read_text() if prompt_path.exists() else ""
    from backend.services.prompt_linter import lint_prompt
    report = lint_prompt(content)
    return {
        "required_fix": [{"section": f.section, "message": f.message} for f in report.required_fix],
        "nice_to_have": [{"section": f.section, "message": f.message} for f in report.nice_to_have],
        "acceptable_risk": [{"section": f.section, "message": f.message} for f in report.acceptable_risk],
    }


@router.post("/design/threads/{slug}/publish")
def v1_publish_thread(slug: str):
    """Publish a thread — guards: status must be approved, lint must have zero required_fix items."""
    show_dir = _show_dir(slug)
    from backend.services.show_persistence import load_status, update_status
    status = load_status(show_dir)
    if status.get("status") != "approved":
        raise HTTPException(400, "Thread must be approved before publishing")

    prompt_path = show_dir / "show_prompt.md"
    content = prompt_path.read_text() if prompt_path.exists() else ""
    from backend.services.prompt_linter import lint_prompt
    report = lint_prompt(content)
    if report.required_fix:
        raise HTTPException(400, f"Prompt has {len(report.required_fix)} required fixes")

    update_status(show_dir, "published")
    return {"status": "published"}


@router.post("/design/threads/{slug}/generate-summary")
def v1_generate_summary(slug: str):
    """Generate a humorous 5-6 word summary for a show card."""
    show_dir = _show_dir(slug)
    from backend.services.show_persistence import read_spec, write_summary
    from backend.services.llm_client import LLMMessage
    from backend.models.agent_definition import ModelTier

    spec = read_spec(show_dir)
    if not spec.strip():
        raise HTTPException(400, "No spec to summarize")

    llm = _get_llm_client()
    if not llm:
        summary = slug.replace("-", " ").title()
        write_summary(show_dir, summary)
        return {"summary": summary}

    system = (
        "You write witty show summaries. Write exactly 5-6 words. "
        "Think movie tagline meets inside joke. No quotes, no punctuation at the end. "
        "Examples: 'Brass goes brrr with feelings', 'Guard throws things really well', "
        "'Existential dread but make it jazz'."
    )
    try:
        resp = llm.chat(
            messages=[
                LLMMessage(role="system", content=system),
                LLMMessage(role="user", content=f"Write a summary for this show:\n\n{spec[:2000]}"),
            ],
            model_tier=ModelTier.HAIKU,
        )
        summary = (resp.content or "").strip().strip('"').strip("'")[:80]
        if not summary:
            summary = slug.replace("-", " ").title()
    except Exception:
        summary = slug.replace("-", " ").title()

    write_summary(show_dir, summary)
    return {"summary": summary}


@router.post("/design/threads/{slug}/approve")
def v1_approve_thread(slug: str):
    """Approve spec — freezes versioned copy, marks show approved."""
    show_dir = _show_dir(slug)
    from backend.services.show_persistence import approve_spec
    try:
        result = approve_spec(show_dir)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@router.get("/design/threads/{slug}/versions")
def v1_list_versions(slug: str):
    """List approved spec versions."""
    show_dir = _show_dir(slug)
    from backend.services.show_persistence import list_spec_versions
    return {"versions": list_spec_versions(show_dir)}


# =========================================================================
# CORPS HISTORY / SEANCE
# =========================================================================

class CreateSeanceRequest(BaseModel):
    corps_id: str
    entry_id: str


class SeanceMessageRequest(BaseModel):
    message: str
    mode: str = "strict"


@router.get("/corps/{corps_id}/history")
def v1_get_corps_history(corps_id: str):
    """List past shows for a corps (builds/returns history index). Falls back to empty for DB-only corps."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    from backend.services.corps_history import build_history_index
    try:
        index = build_history_index(root, corps_id)
        return index
    except FileNotFoundError:
        pass

    # Fallback: build history from filesystem scan for DB-only corps
    try:
        from backend.models.corps import Corps
        db = _get_db_session()
        try:
            corps = db.get(Corps, corps_id)
        finally:
            db.close()
        if not corps:
            raise HTTPException(404, f"Corps '{corps_id}' not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404, f"Corps '{corps_id}' not found")

    # Scan seasons for performances/standings referencing this corps
    from backend.services.corps_history import _probe_artifacts, _discover_runs
    entries = []
    seasons_dir = root / "seasons"
    if seasons_dir.exists():
        for season_dir in sorted(seasons_dir.iterdir()):
            if not season_dir.is_dir():
                continue
            season_id = season_dir.name
            # Check if this corps has any presence in this season
            perf_dir = season_dir / "performances" / corps_id
            standings_path = season_dir / "standings.yaml"
            has_perf = perf_dir.is_dir()
            has_standing = False
            placement = 0
            final_score = 0.0
            show_slug = None

            # Check standings for this corps
            if standings_path.exists():
                try:
                    standings = yaml.safe_load(standings_path.read_text()) or {}
                    for result in standings.get("results", []):
                        if result.get("corps_id") == corps_id:
                            has_standing = True
                            placement = result.get("rank", 0)
                            final_score = result.get("final_score", 0.0)
                            break
                except Exception:
                    pass

            # Check scores.yaml for show_slug
            scores_path = perf_dir / "scores.yaml" if has_perf else None
            if scores_path and scores_path.exists():
                try:
                    scores = yaml.safe_load(scores_path.read_text()) or {}
                    show_slug = scores.get("show_slug")
                except Exception:
                    pass

            # Discover show_slug from run manifests if not in scores
            if not show_slug and has_perf:
                runs = _discover_runs(root, corps_id, season_id)
                for run_id in runs:
                    manifest_path = season_dir / "performances" / corps_id / run_id / "manifest.yaml"
                    if manifest_path.exists():
                        try:
                            m = yaml.safe_load(manifest_path.read_text()) or {}
                            if m.get("show_slug"):
                                show_slug = m["show_slug"]
                                break
                        except Exception:
                            pass

            if has_perf or has_standing:
                entry_id = f"{corps_id}-{season_id}"
                artifacts = _probe_artifacts(root, corps_id, season_id, show_slug)
                runs = _discover_runs(root, corps_id, season_id)
                entries.append({
                    "entry_id": entry_id,
                    "season_id": season_id,
                    "show_slug": show_slug,
                    "placement": placement,
                    "final_score": final_score,
                    "artifacts": artifacts,
                    "runs": runs,
                })

    entries.sort(key=lambda e: e["entry_id"])
    return {
        "corps_id": corps_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }


@router.post("/seances")
def v1_create_seance(req: CreateSeanceRequest):
    """Start a seance session bound to a specific past show."""
    _validate_id(req.corps_id, "corps_id")
    root = _get_root()
    from backend.services.seance_session import create_session
    try:
        session = create_session(root, req.corps_id, req.entry_id)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(400, str(e))
    return session


@router.get("/seances/{seance_id}")
def v1_get_seance(seance_id: str):
    """Get seance session metadata + context binder."""
    _validate_id(seance_id, "seance_id")
    root = _get_root()
    from backend.services.seance_session import load_session
    try:
        session = load_session(root, seance_id)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(404, str(e))
    return session


@router.post("/seances/{seance_id}/messages")
def v1_post_seance_message(seance_id: str, req: SeanceMessageRequest):
    """Post a message to a seance session, get ED response."""
    _validate_id(seance_id, "seance_id")
    if req.mode not in ("strict", "relaxed"):
        raise HTTPException(400, "mode must be 'strict' or 'relaxed'")
    root = _get_root()
    from backend.services.seance_session import load_session
    from backend.services.ed_chat import ed_respond

    try:
        session = load_session(root, seance_id)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(404, str(e))

    if session.get("status") == "closed":
        raise HTTPException(400, "Seance session is closed")

    # Get LLM client — try to reuse app state, fall back to mock
    try:
        from backend.api.app import _task_manager
        if _task_manager and hasattr(_task_manager, "llm_client"):
            llm_client = _task_manager.llm_client
        else:
            raise AttributeError
    except (ImportError, AttributeError):
        from backend.services.llm_client import MockLLMClient
        llm_client = MockLLMClient()

    result = ed_respond(root, session, req.message, llm_client, mode=req.mode)
    return result


@router.get("/seances/{seance_id}/transcript")
def v1_get_seance_transcript(seance_id: str):
    """Read full seance transcript."""
    _validate_id(seance_id, "seance_id")
    root = _get_root()
    from backend.services.seance_session import read_transcript
    try:
        transcript = read_transcript(root, seance_id)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(404, str(e))
    return {"seance_id": seance_id, "transcript": transcript}


@router.get("/seances/{seance_id}/artifact-preview")
def v1_preview_artifact(seance_id: str, path: str = ""):
    """Preview an artifact file from the context binder (read-only, truncated)."""
    _validate_id(seance_id, "seance_id")
    if ".." in path:
        raise HTTPException(400, "Invalid path")
    root = _get_root()
    from backend.services.seance_session import load_session
    try:
        session = load_session(root, seance_id)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(404, str(e))

    binder_paths = {item["path"] for item in session["context_binder"]}
    if path not in binder_paths:
        raise HTTPException(403, "Path not in context binder")

    abs_path = root / path
    if not abs_path.is_file():
        raise HTTPException(404, "Artifact file not found")

    content = abs_path.read_text()
    max_chars = 10_000
    truncated = len(content) > max_chars
    return {"path": path, "content": content[:max_chars], "truncated": truncated}


@router.get("/corps/{corps_id}/seances")
def v1_list_corps_seances(corps_id: str):
    """List seance sessions for a corps by scanning seances/ directory."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    seances_dir = root / "seances"
    if not seances_dir.exists():
        return []
    results = []
    for sdir in seances_dir.iterdir():
        if not sdir.is_dir():
            continue
        session_path = sdir / "session.yaml"
        if not session_path.is_file():
            continue
        try:
            data = yaml.safe_load(session_path.read_text())
            if isinstance(data, dict) and data.get("corps_id") == corps_id:
                results.append({
                    "seance_id": data.get("seance_id", sdir.name),
                    "corps_id": data.get("corps_id"),
                    "entry_id": data.get("entry_id", ""),
                    "season_id": data.get("season_id", ""),
                    "show_slug": data.get("show_slug"),
                    "participant": data.get("participant", "user"),
                    "created_at": data.get("created_at", ""),
                    "status": data.get("status", "active"),
                    "context_binder": data.get("context_binder", []),
                })
        except Exception:
            continue
    results.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return results


# =========================================================================
# ADMIN / CLEANUP
# =========================================================================

@router.post("/admin/cleanup")
def v1_admin_cleanup():
    """Clean up stale agent sessions and orphan corps."""
    from backend.models.corps import Corps, CorpsStatus
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.work_log import WorkLog
    from sqlalchemy import func, select, exists

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        two_hours_ago = now - timedelta(hours=2)
        four_hours_ago = now - timedelta(hours=4)

        # 1. Stale agent sessions: ACTIVE but started > 2h ago with no recent work log
        stale_sessions = db.query(AgentSession).filter(
            AgentSession.status == SessionStatus.ACTIVE,
            AgentSession.started_at < two_hours_ago,
            ~exists(
                select(WorkLog.id).where(
                    WorkLog.session_id == AgentSession.id,
                    WorkLog.timestamp > two_hours_ago
                ).correlate(AgentSession)
            )
        ).all()

        for s in stale_sessions:
            s.status = SessionStatus.TIMED_OUT
            s.ended_at = now

        # 2. Orphan corps: INITIALIZING or WINTER_CAMPS with 0 active sessions and no recent work log
        orphan_corps = db.query(Corps).filter(
            Corps.status.in_([CorpsStatus.INITIALIZING, CorpsStatus.WINTER_CAMPS]),
            ~exists(
                select(AgentSession.id).where(
                    AgentSession.corps_id == Corps.id,
                    AgentSession.status == SessionStatus.ACTIVE
                ).correlate(Corps)
            ),
            ~exists(
                select(WorkLog.id).where(
                    WorkLog.corps_id == Corps.id,
                    WorkLog.timestamp > four_hours_ago
                ).correlate(Corps)
            )
        ).all()

        for c in orphan_corps:
            c.status = CorpsStatus.DISBANDED

        db.commit()
        return {
            "timed_out_sessions": len(stale_sessions),
            "disbanded_corps": len(orphan_corps),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Cleanup failed: {e}")
    finally:
        db.close()


# =========================================================================
# SEASONS
# =========================================================================

@router.get("/seasons")
def v1_list_seasons():
    """List all available seasons."""
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []
    results = []
    for season_dir in sorted(seasons_dir.iterdir()):
        if not season_dir.is_dir():
            continue
        season_yaml = season_dir / "season.yaml"
        if not season_yaml.is_file():
            continue
        data = yaml.safe_load(season_yaml.read_text())
        season_id = data.get("season_id", season_dir.name)
        meta = data.get("metadata", {})
        results.append({
            "season_id": season_id,
            "name": meta.get("name", season_id),
            "dir_name": season_dir.name,
            "metadata": meta,
        })
    return results


class CreateSeasonRequest(BaseModel):
    season_id: Optional[str] = None
    name: Optional[str] = None
    metadata: Optional[dict] = None


def _slugify(text: str) -> str:
    """Convert a descriptive name to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "season"


@router.post("/seasons")
def v1_create_season(req: CreateSeasonRequest):
    """Create a new season workspace. Provide name (auto-generates ID) or season_id directly."""
    if not req.season_id and not req.name:
        raise HTTPException(400, "Provide either 'name' or 'season_id'")
    season_id = req.season_id or _slugify(req.name)
    _validate_id(season_id, "season_id")
    metadata = dict(req.metadata or {})
    if req.name:
        metadata["name"] = req.name
    root = _get_root()
    from backend.services.season_persistence import create_season
    try:
        season_dir = create_season(root, season_id, metadata)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {
        "season_id": season_id,
        "name": req.name or season_id,
        "dir_name": season_dir.name,
        "metadata": metadata,
    }


@router.get("/seasons/{season_id}")
def v1_get_season(season_id: str):
    """Get season details including registered corps."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    from backend.services.season_persistence import load_season
    data = load_season(season_dir)
    meta = data.get("metadata", {})
    data["name"] = meta.get("name", season_id)
    return data


class UpdateSeasonRequest(BaseModel):
    metadata: Optional[dict] = None


@router.put("/seasons/{season_id}")
def v1_update_season(season_id: str, req: UpdateSeasonRequest):
    """Update season metadata."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    season_yaml = season_dir / "season.yaml"
    if not season_yaml.is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")
    data = yaml.safe_load(season_yaml.read_text())
    if req.metadata is not None:
        data["metadata"] = req.metadata
    from backend.services.yaml_util import atomic_write, safe_dump_yaml
    atomic_write(season_yaml, safe_dump_yaml(data))
    return data


class RegisterCorpsRequest(BaseModel):
    corps_id: str


@router.post("/seasons/{season_id}/corps")
def v1_register_season_corps(season_id: str, req: RegisterCorpsRequest):
    """Register a corps for this season (creates performance directory)."""
    _validate_id(season_id, "season_id")
    root = _get_root()
    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").is_file():
        raise HTTPException(404, f"Season '{season_id}' not found")

    # Check corps exists (filesystem or DB)
    corps_dir = root / "corps" / req.corps_id
    if (corps_dir / "corps.yaml").exists():
        from backend.services.season_persistence import register_corps
        register_corps(season_dir, req.corps_id, root / "corps")
    else:
        try:
            from backend.models.corps import Corps
            db = _get_db_session()
            try:
                corps_obj = db.get(Corps, req.corps_id)
                if not corps_obj:
                    raise HTTPException(404, f"Corps '{req.corps_id}' not found")
                if getattr(corps_obj, 'corps_type', None) == 'system':
                    raise HTTPException(400, f"System corps cannot be registered for seasons")
                perf_dir = season_dir / "performances" / req.corps_id
                perf_dir.mkdir(parents=True, exist_ok=True)
            finally:
                db.close()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(404, f"Corps '{req.corps_id}' not found")

    return {"status": "registered", "season_id": season_id, "corps_id": req.corps_id}


# =========================================================================
# COMPETITIONS
# =========================================================================

class CreateCompetitionRequest(BaseModel):
    season_id: str
    show_slug: str
    corps_ids: list[str]


# --- Messaging Request Models ---


class MessagingCreateThreadRequest(BaseModel):
    originator_role: str
    subject: str
    initial_message_body: str
    initial_sender_name: Optional[str] = "Agent"
    user_role: str  # Role of the user creating the thread (for permission check)


class MessagingAddMessageRequest(BaseModel):
    sender_type: str
    sender_role: str
    sender_name: str
    body: str


class MessagingMarkThreadCompleteRequest(BaseModel):
    completed_by_user_id: str
    completed_by_user_role: str  # Role of the user marking complete (for permission check)


class MessagingBulkArchiveRequest(BaseModel):
    thread_ids: list[str]
    archived_by_user_id: str
    archived_by_user_role: str  # Role of the user archiving (must be admin)


def _parse_competition_id(competition_id: str, root: Path) -> tuple[str, str]:
    """Parse competition_id into (season_id, show_slug).

    Tries matching against existing season directory names to handle
    season IDs that contain hyphens (e.g. 'tour-s1-demo' → ('tour-s1', 'demo')).
    Falls back to simple first-hyphen split.
    """
    seasons_dir = root / "seasons"
    if seasons_dir.exists():
        # Try matching longest season_id prefix first
        season_names = sorted(
            (d.name for d in seasons_dir.iterdir() if d.is_dir() and (d / "season.yaml").is_file()),
            key=len, reverse=True
        )
        # Also check season_id from yaml (may differ from dir name)
        for sdir_name in season_names:
            sdir = seasons_dir / sdir_name
            try:
                data = yaml.safe_load((sdir / "season.yaml").read_text())
                sid = data.get("season_id", sdir_name)
            except Exception:
                sid = sdir_name
            prefix = f"{sid}-"
            if competition_id.startswith(prefix) and len(competition_id) > len(prefix):
                return sid, competition_id[len(prefix):]
    # Fallback: split on first hyphen
    parts = competition_id.split("-", 1)
    if len(parts) != 2:
        raise HTTPException(400, "Invalid competition_id format (expected season_id-show_slug)")
    return parts[0], parts[1]


@router.get("/competitions")
def v1_list_competitions():
    """List all competitions (season-show pairs with registered corps)."""
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []
    results = []
    for season_dir in sorted(seasons_dir.iterdir()):
        if not season_dir.is_dir():
            continue
        season_yaml = season_dir / "season.yaml"
        if not season_yaml.is_file():
            continue
        season_data = yaml.safe_load(season_yaml.read_text())
        season_id = season_data.get("season_id", season_dir.name)
        from backend.services.season_persistence import list_registered_corps
        corps_ids = list_registered_corps(season_dir)
        # Find shows used in this season by scanning performances
        show_slugs: set[str] = set()
        perf_root = season_dir / "performances"
        if perf_root.exists():
            for corps_dir in perf_root.iterdir():
                if not corps_dir.is_dir():
                    continue
                for run_dir in corps_dir.iterdir():
                    manifest_path = run_dir / "manifest.yaml"
                    if manifest_path.is_file():
                        try:
                            m = yaml.safe_load(manifest_path.read_text())
                            if isinstance(m, dict) and m.get("show_slug"):
                                show_slugs.add(m["show_slug"])
                        except Exception:
                            pass
        # Also check standings for show_slug
        standings_path = season_dir / "standings.yaml"
        if standings_path.exists():
            try:
                st = yaml.safe_load(standings_path.read_text())
                if isinstance(st, dict) and st.get("show_slug"):
                    show_slugs.add(st["show_slug"])
            except Exception:
                pass
        # Also check per-corps scores.yaml for show_slug
        if perf_root.exists():
            for corps_dir in perf_root.iterdir():
                if not corps_dir.is_dir():
                    continue
                scores_path = corps_dir / "scores.yaml"
                if scores_path.is_file():
                    try:
                        sc = yaml.safe_load(scores_path.read_text())
                        if isinstance(sc, dict) and sc.get("show_slug"):
                            show_slugs.add(sc["show_slug"])
                    except Exception:
                        pass
        if not show_slugs:
            # No shows found — list season as a competition with no show
            results.append({
                "competition_id": season_id,
                "season_id": season_id,
                "show_slug": "",
                "corps_ids": corps_ids,
                "status": "ready",
            })
            continue
        for show_slug in show_slugs:
            competition_id = f"{season_id}-{show_slug}"
            results.append({
                "competition_id": competition_id,
                "season_id": season_id,
                "show_slug": show_slug,
                "corps_ids": corps_ids,
                "status": "completed" if (season_dir / "standings.yaml").exists() else "ready",
            })
    return results


@router.post("/competitions")
def v1_create_competition(req: CreateCompetitionRequest):
    """Create a competition — validates and registers corps in season."""
    root = _get_root()

    season_dir = root / "seasons" / req.season_id
    if not (season_dir / "season.yaml").exists():
        raise HTTPException(404, f"Season '{req.season_id}' not found")

    show_dir = root / "shows" / req.show_slug
    if not (show_dir / "status.yaml").exists():
        raise HTTPException(404, f"Show '{req.show_slug}' not found")
    from backend.services.show_persistence import check_field_ready
    if not check_field_ready(show_dir):
        raise HTTPException(400, f"Show '{req.show_slug}' is not approved")

    # Validate corps exist (filesystem or DB) and register in season
    for cid in req.corps_ids:
        corps_dir = root / "corps" / cid
        if (corps_dir / "corps.yaml").exists():
            from backend.services.season_persistence import register_corps
            register_corps(season_dir, cid, root / "corps")
        else:
            # Check DB for this corps
            try:
                from backend.models.corps import Corps
                db = _get_db_session()
                try:
                    corps = db.get(Corps, cid)
                    if not corps:
                        raise HTTPException(404, f"Corps '{cid}' not found")
                    # Create performance directory directly (skip filesystem corps check)
                    perf_dir = season_dir / "performances" / cid
                    perf_dir.mkdir(parents=True, exist_ok=True)
                finally:
                    db.close()
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(404, f"Corps '{cid}' not found")

    competition_id = f"{req.season_id}-{req.show_slug}"
    return {
        "competition_id": competition_id,
        "season_id": req.season_id,
        "show_slug": req.show_slug,
        "corps_ids": req.corps_ids,
        "status": "ready",
    }


@router.post("/competitions/{competition_id}/run")
def v1_run_competition(competition_id: str):
    """Run a competition heat — deterministic stub scoring + standings."""
    root = _get_root()
    season_id, show_slug = _parse_competition_id(competition_id, root)

    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").exists():
        raise HTTPException(404, f"Season '{season_id}' not found")

    show_dir = root / "shows" / show_slug
    if not (show_dir / "status.yaml").exists():
        raise HTTPException(404, f"Show '{show_slug}' not found")

    from backend.services.season_persistence import list_registered_corps
    corps_ids = list_registered_corps(season_dir)
    if not corps_ids:
        raise HTTPException(400, "No corps registered for this season")

    # Filter to corps that still exist (filesystem or DB), skip stale entries
    valid_corps_ids = []
    for cid in corps_ids:
        if (root / "corps" / cid / "corps.yaml").exists():
            valid_corps_ids.append(cid)
        else:
            try:
                from backend.models.corps import Corps as CorpsModel
                db = _get_db_session()
                try:
                    if db.get(CorpsModel, cid):
                        valid_corps_ids.append(cid)
                finally:
                    db.close()
            except Exception:
                pass  # Skip corps that can't be found
    corps_ids = valid_corps_ids
    if not corps_ids:
        raise HTTPException(400, "No valid corps remaining for this competition")

    from backend.models.score import JudgeType
    from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS
    from backend.services.scoring_engine import compute_standings
    from backend.services.yaml_util import atomic_write, safe_dump_yaml

    from backend.services.judge_service import judge_corps_performance

    # Get LLM client for real judging
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    composites = {}
    judge_results_all = {}
    db = None
    try:
        db = _get_db_session()
        for cid in corps_ids:
            judge_results = judge_corps_performance(db, cid, show_slug, llm_client)
            judge_results_all[cid] = judge_results
            caption_scores = {jt: jr.total_score for jt, jr in judge_results.items()}
            raw_total = sum(caption_scores[jt] * DEFAULT_WEIGHTS.get(jt, 0) for jt in caption_scores)
            composites[cid] = CompositeScore(
                caption_scores=caption_scores,
                raw_total=raw_total,
                penalties_total=0.0,
                final_score=raw_total,
                needs_rework=False,
                needs_escalation=False,
            )

            # Store scores in DB with rep/perf split
            from backend.services.scoring_service import record_score
            for jt, jr in judge_results.items():
                record_score(
                    db, corps_id=cid, judge_type=jt,
                    value=jr.total_score, box=max(1, min(5, int(jr.total_score / 20))),
                    feedback=jr.feedback,
                    rep_score=jr.rep_score, perf_score=jr.perf_score,
                )
    finally:
        if db:
            db.close()

    standings = compute_standings(season_id, DEFAULT_WEIGHTS, composites)

    standings_data = {
        "season_id": standings.season_id,
        "generated_at": standings.generated_at,
        "results": [
            {
                "corps_id": r.corps_id,
                "rank": r.rank,
                "final_score": r.final_score,
                "raw_score": r.raw_score,
                "caption_scores": {jt.value: v for jt, v in r.caption_scores.items()},
            }
            for r in standings.results
        ],
    }
    atomic_write(season_dir / "standings.yaml", safe_dump_yaml(standings_data))

    for cid in corps_ids:
        composite = composites[cid]
        scores_data = {
            "corps_id": cid,
            "show_slug": show_slug,
            "caption_scores": {jt.value: v for jt, v in composite.caption_scores.items()},
            "raw_total": composite.raw_total,
            "final_score": composite.final_score,
        }
        perf_dir = season_dir / "performances" / cid
        atomic_write(perf_dir / "scores.yaml", safe_dump_yaml(scores_data))

    from backend.services.reputation import record_corps_placement
    for r in standings.results:
        corps_dir = root / "corps" / r.corps_id
        if corps_dir.exists():
            record_corps_placement(corps_dir, season_id, r.rank, r.final_score,
                                   notes=f"show:{show_slug}")

    # Auto-critique bottom 75% corps
    auto_critique_summary = {}
    try:
        from backend.services.auto_critique import run_auto_critique
        critique_db = _get_db_session()
        try:
            auto_critique_summary = run_auto_critique(
                critique_db, competition_id, standings_data["results"], llm_client
            )
        finally:
            critique_db.close()
    except Exception as e:
        logger.warning("Auto-critique failed: %s", e)

    return {
        "competition_id": competition_id,
        "status": "completed",
        "standings": standings_data["results"],
        "auto_critique_summary": auto_critique_summary,
    }


@router.post("/competitions/{competition_id}/dispatch")
async def v1_dispatch_competition(competition_id: str):
    """Dispatch agents to execute the show prompt for a competition.

    For each registered corps, finds the executive_director session and dispatches
    it with the show_prompt.md as the task. This is the step that turns a competition
    from "scored" to "actually executed by agents writing code."
    """
    root = _get_root()
    season_id, show_slug = _parse_competition_id(competition_id, root)

    season_dir = root / "seasons" / season_id
    if not (season_dir / "season.yaml").exists():
        raise HTTPException(404, f"Season '{season_id}' not found")

    show_dir = root / "shows" / show_slug
    prompt_path = show_dir / "show_prompt.md"
    if not prompt_path.exists() or prompt_path.stat().st_size == 0:
        raise HTTPException(400, f"Show '{show_slug}' has no show_prompt.md — run Design Room first")

    show_prompt = prompt_path.read_text()

    from backend.services.season_persistence import list_registered_corps
    corps_ids = list_registered_corps(season_dir)
    if not corps_ids:
        raise HTTPException(400, "No corps registered for this season")

    from backend.api.app import get_task_manager
    tm = get_task_manager()
    if not tm:
        raise HTTPException(503, "Task manager not initialized")

    dispatched = []
    skipped = []
    for cid in corps_ids:
        db = _get_db_session()
        try:
            ed_session = tm.get_session_for_role(db, cid, "executive_director")
            if not ed_session:
                skipped.append({"corps_id": cid, "reason": "no ED session found"})
                continue
            if tm.is_active(ed_session):
                skipped.append({"corps_id": cid, "reason": "ED already active"})
                continue

            task_desc = (
                f"COMPETITION DISPATCH — Execute this show for competition {competition_id}.\n\n"
                f"Your corps has been assigned to implement the following show. "
                f"Read the prompt carefully and coordinate your corps to write the code.\n\n"
                f"---\n\n{show_prompt}"
            )
            tm.start_agent(
                session_id=ed_session,
                task_description=task_desc,
                corps_id=cid,
            )
            dispatched.append({"corps_id": cid, "session_id": ed_session})
        finally:
            db.close()

    return {
        "competition_id": competition_id,
        "show_slug": show_slug,
        "dispatched": dispatched,
        "skipped": skipped,
        "total_dispatched": len(dispatched),
        "total_skipped": len(skipped),
    }


@router.get("/competitions/{competition_id}/scores")
def v1_get_competition_scores(competition_id: str):
    """Retrieve scores/standings for a completed competition."""
    root = _get_root()
    season_id, _show_slug = _parse_competition_id(competition_id, root)

    standings_path = root / "seasons" / season_id / "standings.yaml"
    if not standings_path.exists():
        raise HTTPException(404, "Standings not found — competition may not have run yet")
    standings = yaml.safe_load(standings_path.read_text())
    standings["competition_id"] = competition_id
    standings["show_slug"] = _show_slug

    # Resolve corps_id → display_name for each result
    if "results" in standings:
        corps_name_cache: dict[str, str] = {}
        for result in standings["results"]:
            cid = result.get("corps_id", "")
            if cid not in corps_name_cache:
                # Try filesystem
                corps_yaml = root / "corps" / cid / "corps.yaml"
                if corps_yaml.is_file():
                    try:
                        data = yaml.safe_load(corps_yaml.read_text())
                        corps_name_cache[cid] = data.get("display_name", cid)
                    except Exception:
                        corps_name_cache[cid] = cid
                else:
                    # Try DB
                    try:
                        from backend.models.corps import Corps as CorpsModel
                        db = _get_db_session()
                        try:
                            corps = db.get(CorpsModel, cid)
                            corps_name_cache[cid] = corps.name if corps else cid
                        finally:
                            db.close()
                    except Exception:
                        corps_name_cache[cid] = cid
            result["display_name"] = corps_name_cache[cid]

    return standings


@router.get("/competitions/{competition_id}/corps/{corps_id}/breakdown")
def v1_get_corps_breakdown(competition_id: str, corps_id: str):
    """Per-caption score breakdown with weights and synthetic commentary."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    season_id, show_slug = _parse_competition_id(competition_id, root)

    scores_path = root / "seasons" / season_id / "performances" / corps_id / "scores.yaml"
    if not scores_path.exists():
        raise HTTPException(404, "Scores not found for this corps in this competition")

    data = yaml.safe_load(scores_path.read_text())
    caption_scores_raw = data.get("caption_scores", {})

    from backend.services.scoring_service import DEFAULT_WEIGHTS
    from backend.models.score import JudgeType

    weight_map = {jt.value: w for jt, w in DEFAULT_WEIGHTS.items()}

    caption_detail: dict = {}
    commentary: dict = {}
    for caption, score in caption_scores_raw.items():
        w = weight_map.get(caption, 0.0)
        caption_detail[caption] = {
            "score": score,
            "weight": w,
            "weighted": round(score * w, 2),
        }
        if score >= 85:
            commentary[caption] = f"Excellent {caption} performance — top-tier execution."
        elif score >= 70:
            commentary[caption] = f"Solid {caption} showing with room for refinement."
        elif score >= 60:
            commentary[caption] = f"{caption.capitalize()} section needs focused reps — approaching rework threshold."
        else:
            commentary[caption] = f"{caption.capitalize()} section below standards — rework recommended."

    return {
        "corps_id": corps_id,
        "caption_scores": caption_detail,
        "penalties_total": data.get("penalties_total", 0.0),
        "final_score": data.get("final_score", 0.0),
        "commentary": commentary,
    }


@router.get("/competitions/{competition_id}/reports/{corps_id}")
def v1_get_judge_report(competition_id: str, corps_id: str):
    """Get automated judge report for a corps in a competition."""
    _validate_id(corps_id, "corps_id")
    from backend.services.scoring_service import generate_judge_report
    db = _get_db_session()
    try:
        report = generate_judge_report(db, corps_id, competition_id)
        return report
    finally:
        db.close()


@router.post("/competitions/{competition_id}/reports/generate-all")
def v1_generate_all_reports(competition_id: str):
    """Generate judge reports for all corps in a competition."""
    root = _get_root()
    season_id, show_slug = _parse_competition_id(competition_id, root)
    perf_dir = root / "seasons" / season_id / "performances"

    if not perf_dir.exists():
        return {"reports": [], "count": 0}

    from backend.services.scoring_service import generate_judge_report
    db = _get_db_session()
    try:
        reports = []
        for corps_dir in perf_dir.iterdir():
            if corps_dir.is_dir():
                corps_id = corps_dir.name
                report = generate_judge_report(db, corps_id, competition_id)
                reports.append(report)
        return {"reports": reports, "count": len(reports)}
    finally:
        db.close()


# =========================================================================
# JUDGES TAPES & RECAP
# =========================================================================


@router.get("/competitions/{competition_id}/tapes")
def v1_list_tapes(competition_id: str):
    """List all judges tapes for a competition."""
    from backend.models.judges_tape import JudgesTape
    db = _get_db_session()
    try:
        tapes = db.query(JudgesTape).filter(
            JudgesTape.competition_id == competition_id
        ).all()
        return [
            {
                "id": t.id,
                "competition_id": t.competition_id,
                "corps_id": t.corps_id,
                "overall_assessment": t.overall_assessment,
                "caption_count": len(t.caption_feedbacks or {}),
                "created_at": str(t.created_at),
            }
            for t in tapes
        ]
    finally:
        db.close()


@router.get("/competitions/{competition_id}/tapes/{corps_id}")
def v1_get_tape(competition_id: str, corps_id: str):
    """Get detailed judges tape for a corps in a competition."""
    _validate_id(corps_id, "corps_id")
    from backend.models.judges_tape import JudgesTape
    db = _get_db_session()
    try:
        tape = db.query(JudgesTape).filter(
            JudgesTape.competition_id == competition_id,
            JudgesTape.corps_id == corps_id,
        ).order_by(JudgesTape.created_at.desc()).first()

        if not tape:
            # Generate on-demand
            from backend.services.judge_service import generate_judges_tape
            from backend.api.app import get_task_manager
            tm = get_task_manager()
            llm_client = tm.llm_client if tm else None
            tape = generate_judges_tape(db, competition_id, corps_id, llm_client)

        return {
            "id": tape.id,
            "competition_id": tape.competition_id,
            "corps_id": tape.corps_id,
            "caption_feedbacks": tape.caption_feedbacks,
            "overall_assessment": tape.overall_assessment,
            "created_at": str(tape.created_at),
        }
    finally:
        db.close()


@router.get("/competitions/{competition_id}/tapes/{corps_id}/export")
def v1_export_tape(competition_id: str, corps_id: str):
    """Export judges tape as markdown."""
    _validate_id(corps_id, "corps_id")
    from backend.models.judges_tape import JudgesTape
    from backend.services.judge_service import export_tape_markdown, generate_judges_tape
    db = _get_db_session()
    try:
        tape = db.query(JudgesTape).filter(
            JudgesTape.competition_id == competition_id,
            JudgesTape.corps_id == corps_id,
        ).order_by(JudgesTape.created_at.desc()).first()

        if not tape:
            from backend.api.app import get_task_manager
            tm = get_task_manager()
            llm_client = tm.llm_client if tm else None
            tape = generate_judges_tape(db, competition_id, corps_id, llm_client)

        return {"markdown": export_tape_markdown(tape), "corps_id": corps_id}
    finally:
        db.close()


@router.get("/competitions/{competition_id}/recap")
def v1_get_recap(competition_id: str, format: str = "json"):
    """Get recap sheet for a competition. format: json, markdown, csv."""
    root = _get_root()
    season_id, show_slug = _parse_competition_id(competition_id, root)

    from backend.services.recap_sheet import (
        generate_recap_sheet, export_recap_markdown, export_recap_csv,
    )

    rows = generate_recap_sheet(season_id, show_slug)
    if not rows:
        raise HTTPException(404, "No standings data for this competition")

    if format == "markdown":
        return {"markdown": export_recap_markdown(rows)}
    elif format == "csv":
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=export_recap_csv(rows),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=recap_{competition_id}.csv"},
        )
    else:
        return [
            {
                "rank": r.rank,
                "corps_id": r.corps_id,
                "corps_name": r.corps_name,
                "caption_scores": r.caption_scores,
                "penalties_total": r.penalties_total,
                "raw_total": r.raw_total,
                "final_score": r.final_score,
            }
            for r in rows
        ]


# =========================================================================
# CRITIQUE SESSIONS
# =========================================================================


class StartCritiqueRequest(BaseModel):
    corps_id: str
    judge_type: str


@router.post("/competitions/{competition_id}/critique")
def v1_start_critique(competition_id: str, req: StartCritiqueRequest):
    """Start a critique session between a judge and staff member."""
    _validate_id(req.corps_id, "corps_id")
    from backend.services.critique_service import start_critique
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    db = _get_db_session()
    try:
        session = start_critique(db, competition_id, req.corps_id, req.judge_type, llm_client)
        return {
            "id": session.id,
            "competition_id": session.competition_id,
            "corps_id": session.corps_id,
            "judge_type": session.judge_type,
            "staff_role": session.staff_role,
            "status": session.status.value,
            "conversation": session.conversation,
            "action_items": session.action_items,
            "created_at": str(session.created_at),
            "is_automated": getattr(session, "is_automated", False),
        }
    finally:
        db.close()


@router.get("/critique/{session_id}")
def v1_get_critique(session_id: str):
    """Get critique session conversation."""
    from backend.models.critique_session import CritiqueSession
    db = _get_db_session()
    try:
        session = db.get(CritiqueSession, session_id)
        if not session:
            raise HTTPException(404, "Critique session not found")
        return {
            "id": session.id,
            "competition_id": session.competition_id,
            "corps_id": session.corps_id,
            "judge_type": session.judge_type,
            "staff_role": session.staff_role,
            "status": session.status.value,
            "conversation": session.conversation,
            "action_items": session.action_items,
            "created_at": str(session.created_at),
            "is_automated": getattr(session, "is_automated", False),
        }
    finally:
        db.close()


class CritiqueMessageRequest(BaseModel):
    message: str


@router.post("/critique/{session_id}/message")
def v1_send_critique_message(session_id: str, req: CritiqueMessageRequest):
    """Send a message in a critique session."""
    from backend.services.critique_service import send_message
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    db = _get_db_session()
    try:
        session = send_message(db, session_id, req.message, llm_client)
        return {
            "id": session.id,
            "competition_id": session.competition_id,
            "corps_id": session.corps_id,
            "judge_type": session.judge_type,
            "staff_role": session.staff_role,
            "status": session.status.value,
            "conversation": session.conversation,
            "action_items": session.action_items,
            "created_at": str(session.created_at),
            "is_automated": getattr(session, "is_automated", False),
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.post("/critique/{session_id}/complete")
def v1_complete_critique(session_id: str):
    """Complete a critique session — extract action items."""
    from backend.services.critique_service import complete_critique
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    db = _get_db_session()
    try:
        session = complete_critique(db, session_id, llm_client)
        return {
            "id": session.id,
            "competition_id": session.competition_id,
            "corps_id": session.corps_id,
            "judge_type": session.judge_type,
            "staff_role": session.staff_role,
            "status": session.status.value,
            "conversation": session.conversation,
            "action_items": session.action_items,
            "created_at": str(session.created_at),
            "completed_at": str(session.completed_at) if session.completed_at else None,
            "is_automated": getattr(session, "is_automated", False),
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


class CorpsFeedbackRequest(BaseModel):
    feedback: str


@router.post("/corps/{corps_id}/feedback")
def v1_send_corps_feedback(corps_id: str, req: CorpsFeedbackRequest):
    """Deliver user feedback as directive to corps ED via auto-completing critique session."""
    _validate_id(corps_id, "corps_id")
    from backend.services.critique_service import start_critique, complete_critique
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    db = _get_db_session()
    try:
        from backend.models.corps import Corps
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, "Corps not found")

        # Create a critique session with user feedback as the opening message
        session = start_critique(
            db, competition_id=f"feedback-{corps_id}",
            corps_id=corps_id, judge_type="user_feedback",
            llm_client=None,  # No LLM for opening — we use the user's feedback directly
        )
        # Replace the auto-generated opening with the user's feedback
        session.conversation = [{"role": "judge", "content": req.feedback}]
        db.commit()

        # Auto-complete to extract action items
        completed = complete_critique(db, session.id, llm_client=llm_client)
        return {"status": "delivered", "session_id": completed.id}
    finally:
        db.close()


@router.post("/corps/{corps_id}/ed-chat")
def v1_start_ed_chat(corps_id: str):
    """Start a multi-turn chat with the corps Executive Director."""
    _validate_id(corps_id, "corps_id")
    from backend.services.critique_service import start_critique
    from backend.api.app import get_task_manager
    tm = get_task_manager()
    llm_client = tm.llm_client if tm else None

    db = _get_db_session()
    try:
        from backend.models.corps import Corps
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, "Corps not found")

        session = start_critique(
            db, competition_id=f"ed-chat-{corps_id}",
            corps_id=corps_id, judge_type="user",
            llm_client=llm_client,
        )
        # Override staff_role to executive_director
        session.staff_role = "executive_director"
        db.commit()
        db.refresh(session)

        return {
            "id": session.id,
            "competition_id": session.competition_id,
            "corps_id": session.corps_id,
            "judge_type": session.judge_type,
            "staff_role": session.staff_role,
            "status": session.status.value,
            "conversation": session.conversation,
            "action_items": session.action_items,
            "created_at": str(session.created_at),
        }
    finally:
        db.close()


@router.get("/corps/{corps_id}/adaptation-history")
def v1_get_adaptation_history(corps_id: str):
    """View agent adaptation attempts and outcomes for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.services.agent_adaptation import get_adaptation_history
    db = _get_db_session()
    try:
        return get_adaptation_history(db, corps_id)
    finally:
        db.close()


class ContestEvaluateRequest(BaseModel):
    season_id: str
    show_slug: str


@router.post("/contest/evaluate")
def v1_contest_evaluate(req: ContestEvaluateRequest):
    """Find all READY_FOR_CONTEST corps and run a competition between them.

    After scoring, transitions each participating corps to COMPLETED.
    """
    from backend.models.corps import Corps, CorpsStatus
    from backend.models.score import JudgeType
    from backend.services.scoring_service import CompositeScore, DEFAULT_WEIGHTS
    from backend.services.scoring_engine import compute_standings
    from backend.services.yaml_util import atomic_write, safe_dump_yaml

    root = _get_root()

    season_dir = root / "seasons" / req.season_id
    if not (season_dir / "season.yaml").exists():
        raise HTTPException(404, f"Season '{req.season_id}' not found")

    show_dir = root / "shows" / req.show_slug
    if not (show_dir / "status.yaml").exists():
        raise HTTPException(404, f"Show '{req.show_slug}' not found")

    db = _get_db_session()
    try:
        ready_corps = db.query(Corps).filter(
            Corps.status == CorpsStatus.READY_FOR_CONTEST
        ).all()
        if not ready_corps:
            raise HTTPException(400, "No corps in READY_FOR_CONTEST state")

        corps_ids = [c.id for c in ready_corps]

        # Ensure performance directories exist
        for cid in corps_ids:
            perf_dir = season_dir / "performances" / cid
            perf_dir.mkdir(parents=True, exist_ok=True)

        # Score using real LLM judging (falls back to stubs if unavailable)
        from backend.services.judge_service import judge_corps_performance
        from backend.api.app import get_task_manager
        tm = get_task_manager()
        llm_client = tm.llm_client if tm else None

        composites = {}
        for cid in corps_ids:
            judge_results = judge_corps_performance(db, cid, req.show_slug, llm_client)
            caption_scores = {jt: jr.total_score for jt, jr in judge_results.items()}
            raw_total = sum(caption_scores[jt] * DEFAULT_WEIGHTS.get(jt, 0) for jt in caption_scores)
            composites[cid] = CompositeScore(
                caption_scores=caption_scores,
                raw_total=raw_total,
                penalties_total=0.0,
                final_score=raw_total,
                needs_rework=False,
                needs_escalation=False,
            )

            # Persist individual judge scores
            from backend.services.scoring_service import record_score
            for jt, jr in judge_results.items():
                record_score(
                    db, corps_id=cid, judge_type=jt,
                    value=jr.total_score, box=max(1, min(5, int(jr.total_score / 20))),
                    feedback=jr.feedback,
                    rep_score=jr.rep_score, perf_score=jr.perf_score,
                )

        standings = compute_standings(req.season_id, DEFAULT_WEIGHTS, composites)

        standings_data = {
            "season_id": standings.season_id,
            "generated_at": standings.generated_at,
            "show_slug": req.show_slug,
            "results": [
                {
                    "corps_id": r.corps_id,
                    "rank": r.rank,
                    "final_score": r.final_score,
                    "raw_score": r.raw_score,
                    "caption_scores": {jt.value: v for jt, v in r.caption_scores.items()},
                }
                for r in standings.results
            ],
        }
        atomic_write(season_dir / "standings.yaml", safe_dump_yaml(standings_data))

        # Write per-corps scores
        for cid in corps_ids:
            composite = composites[cid]
            scores_data = {
                "corps_id": cid,
                "show_slug": req.show_slug,
                "caption_scores": {jt.value: v for jt, v in composite.caption_scores.items()},
                "raw_total": composite.raw_total,
                "final_score": composite.final_score,
            }
            perf_dir = season_dir / "performances" / cid
            atomic_write(perf_dir / "scores.yaml", safe_dump_yaml(scores_data))

        # Transition all participating corps to COMPLETED
        for c in ready_corps:
            c.status = CorpsStatus.COMPLETED
        db.commit()

        # Record reputation for filesystem corps
        from backend.services.reputation import record_corps_placement
        for r in standings.results:
            corps_dir = root / "corps" / r.corps_id
            if corps_dir.exists():
                record_corps_placement(
                    corps_dir, req.season_id, r.rank, r.final_score,
                    notes=f"show:{req.show_slug}",
                )

        return {
            "status": "completed",
            "corps_evaluated": len(corps_ids),
            "standings": standings_data["results"],
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Contest evaluation failed: {e}")
    finally:
        db.close()


def _stub_caption_scores(corps_id: str, show_slug: str) -> dict:
    """Deterministic scores per caption, seeded from corps_id + show_slug."""
    from backend.models.score import JudgeType
    scores = {}
    for jtype in [JudgeType.BRASS, JudgeType.PERCUSSION, JudgeType.GUARD,
                  JudgeType.VISUAL, JudgeType.GENERAL_EFFECT]:
        seed = hashlib.sha256(f"{corps_id}:{show_slug}:{jtype.value}".encode()).hexdigest()
        scores[jtype] = (int(seed[:8], 16) % 30) + 60
    return scores


# =========================================================================
# STAFF MARKETPLACE
# =========================================================================


class HireStaffRequest(BaseModel):
    performer_id: str
    role: str


class ReleaseStaffRequest(BaseModel):
    performer_id: str
    trust_penalty: float = 0.0


@router.get("/staff/marketplace")
def v1_list_staff_marketplace():
    """List all non-retired performers available in the marketplace."""
    from backend.models.performer import Performer, PerformerStatus

    db = _get_db_session()
    try:
        performers = (
            db.query(Performer)
            .filter(Performer.status != PerformerStatus.RETIRED)
            .order_by(Performer.trust_score.desc())
            .all()
        )
        return {
            "performers": [
                {
                    "id": p.id,
                    "name": p.name,
                    "role_type": p.role_type,
                    "trust_score": p.trust_score,
                    "total_sessions": p.total_sessions,
                    "successful_sessions": p.successful_sessions,
                    "failed_sessions": p.failed_sessions,
                    "status": p.status.value if p.status else None,
                    "age": p.age,
                    "experience_seasons": p.experience_seasons,
                    "specialties": p.specialties,
                }
                for p in performers
            ],
            "count": len(performers),
        }
    finally:
        db.close()


@router.get("/staff/{performer_id}/profile")
def v1_get_staff_profile(performer_id: str):
    """Detailed performer profile including capability ledger and experience."""
    from backend.models.performer import Performer
    from backend.models.capability_ledger import CapabilityLedger
    from backend.models.agent_experience import AgentExperience

    _validate_id(performer_id, "performer_id")

    db = _get_db_session()
    try:
        performer = db.query(Performer).filter(Performer.id == performer_id).first()
        if not performer:
            raise HTTPException(404, f"Performer {performer_id} not found")

        ledger_entries = (
            db.query(CapabilityLedger)
            .filter(CapabilityLedger.performer_id == performer_id)
            .order_by(CapabilityLedger.created_at.desc())
            .limit(20)
            .all()
        )

        experiences = (
            db.query(AgentExperience)
            .filter(AgentExperience.performer_id == performer_id)
            .all()
        )

        return {
            "id": performer.id,
            "name": performer.name,
            "role_type": performer.role_type,
            "trust_score": performer.trust_score,
            "total_sessions": performer.total_sessions,
            "successful_sessions": performer.successful_sessions,
            "failed_sessions": performer.failed_sessions,
            "status": performer.status.value if performer.status else None,
            "age": performer.age,
            "experience_seasons": performer.experience_seasons,
            "specialties": performer.specialties,
            "capability_ledger": [
                {
                    "id": entry.id,
                    "capability": entry.capability,
                    "delta": entry.delta,
                    "reason": entry.reason,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                }
                for entry in ledger_entries
            ],
            "experiences": [
                {
                    "id": exp.id,
                    "corps_id": exp.corps_id,
                    "role": exp.role,
                    "season": exp.season,
                    "outcome": exp.outcome,
                    "notes": exp.notes,
                }
                for exp in experiences
            ],
        }
    finally:
        db.close()


@router.post("/corps/{corps_id}/staff/hire")
def v1_hire_staff(corps_id: str, req: HireStaffRequest):
    """Hire a performer to a corps by creating an agent definition and session."""
    from backend.models.performer import Performer
    from backend.models.agent_definition import AgentDefinition
    from backend.models.agent_session import AgentSession, SessionStatus

    _validate_id(corps_id, "corps_id")
    _validate_id(req.performer_id, "performer_id")

    db = _get_db_session()
    try:
        performer = db.query(Performer).filter(Performer.id == req.performer_id).first()
        if not performer:
            raise HTTPException(404, f"Performer {req.performer_id} not found")

        # Create an AgentDefinition for this role in the corps
        agent_def = AgentDefinition(
            id=str(uuid.uuid4()),
            corps_id=corps_id,
            role=req.role,
            performer_id=req.performer_id,
        )
        db.add(agent_def)

        # Spawn an active AgentSession linked to the performer
        session = AgentSession(
            id=str(uuid.uuid4()),
            agent_definition_id=agent_def.id,
            performer_id=req.performer_id,
            corps_id=corps_id,
            status=SessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()

        return {
            "agent_definition_id": agent_def.id,
            "session_id": session.id,
            "corps_id": corps_id,
            "performer_id": req.performer_id,
            "role": req.role,
            "status": session.status.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to hire staff: {e}")
    finally:
        db.close()


@router.post("/corps/{corps_id}/staff/release")
def v1_release_staff(corps_id: str, req: ReleaseStaffRequest):
    """Release a performer from a corps, ending their active session."""
    from backend.models.performer import Performer
    from backend.models.agent_session import AgentSession, SessionStatus

    _validate_id(corps_id, "corps_id")
    _validate_id(req.performer_id, "performer_id")

    db = _get_db_session()
    try:
        # Find the active session for this performer in this corps
        session = (
            db.query(AgentSession)
            .filter(
                AgentSession.performer_id == req.performer_id,
                AgentSession.corps_id == corps_id,
                AgentSession.status == SessionStatus.ACTIVE,
            )
            .first()
        )
        if not session:
            raise HTTPException(
                404,
                f"No active session for performer {req.performer_id} in corps {corps_id}",
            )

        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.now(timezone.utc)

        # Apply optional trust penalty
        if req.trust_penalty:
            performer = db.query(Performer).filter(Performer.id == req.performer_id).first()
            if performer and performer.trust_score is not None:
                performer.trust_score = max(0.0, performer.trust_score - req.trust_penalty)

        db.commit()

        return {
            "session_id": session.id,
            "corps_id": corps_id,
            "performer_id": req.performer_id,
            "status": session.status.value,
            "completed_at": session.ended_at.isoformat(),
            "trust_penalty_applied": req.trust_penalty,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to release staff: {e}")
    finally:
        db.close()


@router.get("/corps/{corps_id}/staff")
def v1_list_corps_staff(corps_id: str):
    """List current active staff for a corps."""
    from backend.models.performer import Performer
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition

    _validate_id(corps_id, "corps_id")

    db = _get_db_session()
    try:
        results = (
            db.query(AgentSession, Performer, AgentDefinition)
            .join(Performer, AgentSession.performer_id == Performer.id)
            .join(AgentDefinition, AgentSession.agent_definition_id == AgentDefinition.id)
            .filter(
                AgentSession.corps_id == corps_id,
                AgentSession.status == SessionStatus.ACTIVE,
            )
            .all()
        )

        return {
            "corps_id": corps_id,
            "staff": [
                {
                    "session_id": session.id,
                    "performer_id": performer.id,
                    "performer_name": performer.name,
                    "role": agent_def.role,
                    "trust_score": performer.trust_score,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "status": session.status.value,
                }
                for session, performer, agent_def in results
            ],
            "count": len(results),
        }
    finally:
        db.close()


# =========================================================================
# ASYNCHRONOUS MESSAGING
# =========================================================================


@router.get("/messaging/unread-count")
def v1_get_unread_message_count():
    """Get count of unread messages (pending threads)."""
    from backend.services.messaging_service import MessagingService

    db = _get_db_session()
    try:
        service = MessagingService(db)
        count = service.get_unread_count()
        return {"unread_count": count}
    finally:
        db.close()


@router.post("/messaging/threads")
def v1_create_messaging_thread(req: MessagingCreateThreadRequest):
    """Create a new messaging thread with an initial message.

    Permission: Only EDs and PCs can create threads.
    """
    from backend.services.messaging_service import MessagingService
    from backend.services.messaging_permissions import MessagingPermissions

    # Check permissions
    if not MessagingPermissions.can_create_thread(req.user_role):
        raise HTTPException(
            403,
            f"User role '{req.user_role}' cannot create threads. "
            "Only Executive Directors and Program Coordinators may initiate threads.",
        )

    db = _get_db_session()
    try:
        service = MessagingService(db)
        thread = service.create_thread(
            originator_role=req.originator_role,
            subject=req.subject,
            initial_message_body=req.initial_message_body,
            initial_sender_name=req.initial_sender_name or "Agent",
        )
        return {
            "thread_id": thread.id,
            "originator_role": thread.originator_role.value,
            "subject": thread.subject,
            "status": thread.status.value,
            "created_at": thread.created_at.isoformat(),
            "message_count": len(thread.messages),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create thread: {e}")
    finally:
        db.close()


@router.get("/messaging/threads")
def v1_list_messaging_threads(
    status: Optional[str] = None,
    originator_role: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List active messaging threads with optional filtering."""
    from backend.services.messaging_service import MessagingService

    db = _get_db_session()
    try:
        service = MessagingService(db)
        threads, total = service.list_threads(
            status=status,
            originator_role=originator_role,
            limit=limit,
            offset=offset,
        )
        return {
            "threads": [
                {
                    "thread_id": t.id,
                    "originator_role": t.originator_role.value,
                    "subject": t.subject,
                    "status": t.status.value,
                    "created_at": t.created_at.isoformat(),
                    "updated_at": t.updated_at.isoformat(),
                    "message_count": len(t.messages),
                    "archive_candidate_at": t.archive_candidate_at.isoformat()
                    if t.archive_candidate_at
                    else None,
                }
                for t in threads
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        db.close()


@router.get("/messaging/threads/{thread_id}")
def v1_get_messaging_thread(thread_id: str):
    """Get a messaging thread with all its messages."""
    from backend.services.messaging_service import MessagingService

    _validate_id(thread_id, "thread_id")

    db = _get_db_session()
    try:
        service = MessagingService(db)
        thread = service.get_thread(thread_id)
        if not thread:
            raise HTTPException(404, f"Thread {thread_id} not found")

        return {
            "thread_id": thread.id,
            "originator_role": thread.originator_role.value,
            "subject": thread.subject,
            "status": thread.status.value,
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat(),
            "completed_at": thread.completed_at.isoformat()
            if thread.completed_at
            else None,
            "completed_by": thread.completed_by,
            "messages": [
                {
                    "message_id": m.id,
                    "sender_type": m.sender_type.value,
                    "sender_role": m.sender_role,
                    "sender_name": m.sender_name,
                    "body": m.body,
                    "created_at": m.created_at.isoformat(),
                }
                for m in sorted(thread.messages, key=lambda x: x.created_at)
            ],
        }
    finally:
        db.close()


@router.post("/messaging/threads/{thread_id}/messages")
def v1_add_messaging_thread_message(thread_id: str, req: MessagingAddMessageRequest):
    """Add a message to an existing thread."""
    from backend.services.messaging_service import MessagingService

    _validate_id(thread_id, "thread_id")

    db = _get_db_session()
    try:
        service = MessagingService(db)
        message = service.add_message_to_thread(
            thread_id=thread_id,
            sender_type=req.sender_type,
            sender_role=req.sender_role,
            sender_name=req.sender_name,
            body=req.body,
        )
        return {
            "message_id": message.id,
            "thread_id": message.thread_id,
            "sender_type": message.sender_type.value,
            "sender_role": message.sender_role,
            "sender_name": message.sender_name,
            "body": message.body,
            "created_at": message.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to add message: {e}")
    finally:
        db.close()


@router.patch("/messaging/threads/{thread_id}")
def v1_mark_messaging_thread_complete(
    thread_id: str, req: MessagingMarkThreadCompleteRequest
):
    """Mark a messaging thread as completed.

    Permission: Only the user who received the thread or the ED/PC originator
    can mark it complete.
    """
    from backend.services.messaging_service import MessagingService
    from backend.services.messaging_permissions import MessagingPermissions

    _validate_id(thread_id, "thread_id")

    db = _get_db_session()
    try:
        service = MessagingService(db)
        thread = service.get_thread(thread_id)
        if not thread:
            raise HTTPException(404, f"Thread {thread_id} not found")

        # Check permissions: only receiver or originator can mark complete
        # For now, we assume is_message_receiver=True (simplification)
        # In production, would track thread recipients in a separate table
        if not MessagingPermissions.can_mark_thread_complete(
            user_role=req.completed_by_user_role,
            thread_originator_role=thread.originator_role.value,
            is_message_receiver=True,  # Simplified: user is receiver
        ):
            raise HTTPException(
                403,
                "Only the message receiver or thread originator (ED/PC) can mark threads complete.",
            )

        thread = service.mark_thread_complete(thread_id, req.completed_by_user_id)
        return {
            "thread_id": thread.id,
            "status": thread.status.value,
            "completed_at": thread.completed_at.isoformat(),
            "completed_by": thread.completed_by,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to mark thread complete: {e}")
    finally:
        db.close()


@router.get("/messaging/archive")
def v1_list_archived_threads(
    search: Optional[str] = None,
    originator_role: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user_role: Optional[str] = None,
):
    """List archived messaging threads with optional search and filtering.

    Permission: Admins (full access) and EDs (read-only).
    """
    from backend.services.messaging_service import MessagingService
    from backend.services.messaging_permissions import MessagingPermissions

    # Check permissions
    if user_role and not MessagingPermissions.can_search_archive(user_role):
        raise HTTPException(
            403,
            f"User role '{user_role}' cannot search archives. "
            "Only Admins and Executive Directors may access archived threads.",
        )

    db = _get_db_session()
    try:
        service = MessagingService(db)
        threads, total = service.list_archived_threads(
            search_query=search,
            originator_role=originator_role,
            limit=limit,
            offset=offset,
        )
        return {
            "archived_threads": [
                {
                    "archived_thread_id": t.id,
                    "original_thread_id": t.original_thread_id,
                    "originator_role": t.originator_role,
                    "subject": t.subject,
                    "summary": t.summary,
                    "message_count": t.message_count,
                    "created_at": t.created_at.isoformat(),
                    "archived_at": t.archived_at.isoformat(),
                    "tags": t.tags.split(",") if t.tags else [],
                    "decision": t.decision,
                }
                for t in threads
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        db.close()


@router.get("/messaging/archive/{archived_thread_id}")
def v1_get_archived_messaging_thread(archived_thread_id: str):
    """Get an archived messaging thread (read-only view)."""
    from backend.services.messaging_service import MessagingService

    _validate_id(archived_thread_id, "archived_thread_id")

    db = _get_db_session()
    try:
        service = MessagingService(db)
        thread = service.get_archived_thread(archived_thread_id)
        if not thread:
            raise HTTPException(404, f"Archived thread {archived_thread_id} not found")

        return {
            "archived_thread_id": thread.id,
            "original_thread_id": thread.original_thread_id,
            "originator_role": thread.originator_role,
            "subject": thread.subject,
            "summary": thread.summary,
            "message_count": thread.message_count,
            "created_at": thread.created_at.isoformat(),
            "archived_at": thread.archived_at.isoformat(),
            "archived_by": thread.archived_by,
            "full_text": thread.full_text,
            "tags": thread.tags.split(",") if thread.tags else [],
            "decision": thread.decision,
        }
    finally:
        db.close()


@router.post("/messaging/archive/bulk-archive")
def v1_bulk_archive_messaging_threads(req: MessagingBulkArchiveRequest):
    """Bulk-archive completed threads with LLM-generated summaries.

    Returns operation summary with count and metadata of archived threads.
    Permission: Admins only.
    """
    from backend.services.messaging_service import MessagingService
    from backend.services.messaging_permissions import MessagingPermissions

    # Check permissions
    if not MessagingPermissions.can_bulk_archive_threads(req.archived_by_user_role):
        raise HTTPException(
            403,
            "Only Admins can bulk-archive threads. "
            "Agents cannot archive to prevent accidental data loss.",
        )

    db = _get_db_session()
    try:
        service = MessagingService(db)

        # Get threads to archive
        threads_to_archive = []
        for thread_id in req.thread_ids:
            thread = service.get_thread(thread_id)
            if thread:
                threads_to_archive.append(thread)

        if not threads_to_archive:
            raise HTTPException(400, "No valid threads found to archive")

        # Generate LLM-based summaries and extract decisions + tags
        from backend.services.messaging_summary_service import generate_thread_summary

        summaries = {}
        decisions = {}
        tags_dict = {}

        for thread in threads_to_archive:
            # Prepare message data for LLM
            message_data = [
                {
                    "sender_name": m.sender_name,
                    "body": m.body,
                    "created_at": m.created_at.isoformat(),
                }
                for m in thread.messages
            ]

            # Generate summary via LLM (with fallback)
            summary, decision, tags = generate_thread_summary(
                subject=thread.subject, messages=message_data
            )
            summaries[thread.id] = summary
            decisions[thread.id] = decision
            tags_dict[thread.id] = tags

        # Archive threads
        archived = service.archive_threads(
            thread_ids=req.thread_ids,
            archived_by_user_id=req.archived_by_user_id,
            summaries=summaries,
            decisions=decisions,
            tags_dict=tags_dict,
        )

        return {
            "operation_id": str(uuid.uuid4()),
            "count_archived": len(archived),
            "archived_threads": [
                {
                    "archived_thread_id": at.id,
                    "original_thread_id": at.original_thread_id,
                    "subject": at.subject,
                    "summary": at.summary,
                }
                for at in archived
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to bulk-archive threads: {e}")
    finally:
        db.close()


# =========================================================================
# SCOREBOARDS & METRICS
# =========================================================================


@router.get("/metrics/scoreboard/corps")
def api_metrics_corps_scoreboard(
    period_days: int = 7,
    limit: int = 20,
):
    """Corps scoreboard: rank corps by composite score.

    Composite score = 40% completion + 30% throughput + 20% efficiency + 10% error_penalty.
    """
    from backend.models.corps import Corps, CorpsStatus
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.rep import Rep, RepStatus
    from backend.models.segment import Segment
    from backend.models.show import Show
    from datetime import timedelta

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=period_days)

        corps_list = (
            db.query(Corps)
            .filter(Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]))
            .all()
        )

        scores = []
        for corps in corps_list:
            # Sessions in period
            sessions = (
                db.query(AgentSession)
                .filter(
                    AgentSession.corps_id == corps.id,
                    AgentSession.started_at >= cutoff,
                )
                .all()
            )
            total_sessions = len(sessions)
            completed_sessions = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
            failed_sessions = sum(1 for s in sessions if s.status == SessionStatus.FAILED)

            # Reps via Show → Segments
            show = db.query(Show).filter(Show.corps_id == corps.id).first()
            total_reps = 0
            completed_reps = 0
            failed_reps = 0
            if show and show.segment_root_id:
                all_reps = (
                    db.query(Rep)
                    .join(Segment)
                    .filter(Rep.created_at >= cutoff)
                    .all()
                )
                # Filter to this corps' segments (simple: match via show)
                total_reps = len(all_reps)
                completed_reps = sum(1 for r in all_reps if r.status == RepStatus.COMPLETED)
                failed_reps = sum(1 for r in all_reps if r.status == RepStatus.FAILED)

            # Compute scores (0-100 each dimension)
            completion = (completed_reps / max(total_reps, 1)) * 100
            throughput = min(completed_sessions / max(1, period_days), 100)  # sessions/day, capped
            efficiency = (completed_sessions / max(total_sessions, 1)) * 100
            error_penalty = (1 - (failed_sessions + failed_reps) / max(total_sessions + total_reps, 1)) * 100

            composite = (
                0.40 * completion
                + 0.30 * throughput
                + 0.20 * efficiency
                + 0.10 * error_penalty
            )

            scores.append({
                "corps_id": corps.id,
                "corps_name": corps.name,
                "corps_status": corps.status.value,
                "composite_score": round(composite, 2),
                "completion_score": round(completion, 2),
                "throughput_score": round(throughput, 2),
                "efficiency_score": round(efficiency, 2),
                "error_penalty_score": round(error_penalty, 2),
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "failed_sessions": failed_sessions,
                "total_reps": total_reps,
                "completed_reps": completed_reps,
                "failed_reps": failed_reps,
                "period_days": period_days,
            })

        scores.sort(key=lambda x: x["composite_score"], reverse=True)
        for rank, s in enumerate(scores[:limit], 1):
            s["rank"] = rank

        return {
            "period_days": period_days,
            "generated_at": now.isoformat(),
            "scoreboard": scores[:limit],
        }
    finally:
        db.close()


@router.get("/metrics/scoreboard/agents")
def api_metrics_agent_leaderboard(
    corps_id: Optional[str] = None,
    period_days: int = 7,
    limit: int = 30,
):
    """Agent leaderboard: rank agents by session count and success rate."""
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    from datetime import timedelta
    from collections import defaultdict

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=period_days)

        query = (
            db.query(AgentSession, AgentDefinition.role, AgentDefinition.nickname)
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .filter(AgentSession.started_at >= cutoff)
        )
        if corps_id:
            query = query.filter(AgentSession.corps_id == corps_id)

        # Aggregate in Python to avoid SQLite cast issues
        buckets: dict[tuple, dict] = {}
        for session, role, nickname in query.all():
            key = (role, nickname, session.corps_id)
            if key not in buckets:
                buckets[key] = {"total": 0, "completed": 0, "failed": 0}
            buckets[key]["total"] += 1
            if session.status == SessionStatus.COMPLETED:
                buckets[key]["completed"] += 1
            elif session.status == SessionStatus.FAILED:
                buckets[key]["failed"] += 1

        leaders = []
        for (role, nickname, cid), counts in buckets.items():
            total = counts["total"]
            completed = counts["completed"]
            failed = counts["failed"]
            success_rate = (completed / max(total, 1)) * 100

            leaders.append({
                "role": role,
                "nickname": nickname,
                "corps_id": cid,
                "total_sessions": total,
                "completed_sessions": completed,
                "failed_sessions": failed,
                "success_rate": round(success_rate, 1),
                "period_days": period_days,
            })

        leaders.sort(key=lambda x: (-x["completed_sessions"], -x["success_rate"]))
        for rank, l in enumerate(leaders[:limit], 1):
            l["rank"] = rank

        return {
            "period_days": period_days,
            "corps_id": corps_id,
            "generated_at": now.isoformat(),
            "leaderboard": leaders[:limit],
        }
    finally:
        db.close()


@router.get("/metrics/bottlenecks")
def api_metrics_bottlenecks(
    corps_id: Optional[str] = None,
    period_days: int = 7,
):
    """Detect bottlenecks: roles and operations exceeding p95 latency thresholds."""
    from backend.services.metrics import MetricsCollector, MetricType
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    from datetime import timedelta

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=period_days)

        # Latency bottlenecks from metrics events (table may not exist yet)
        latency_bottlenecks = []
        try:
            collector = MetricsCollector(db)
            latency_types = [MetricType.QUERY_LATENCY, MetricType.TASK_LATENCY]
            for lt in latency_types:
                percs = collector.get_latency_percentiles(lt, start_time=cutoff, corps_id=corps_id)
                if percs["count"] > 0:
                    latency_bottlenecks.append({
                        "metric": lt.value,
                        "count": percs["count"],
                        "p50_ms": round(percs["p50"] or 0, 2),
                        "p95_ms": round(percs["p95"] or 0, 2),
                        "p99_ms": round(percs["p99"] or 0, 2),
                        "max_ms": round(percs["max"] or 0, 2),
                    })
        except Exception:
            pass  # metrics_events table may not exist yet

        # Session duration bottlenecks by role
        query = (
            db.query(
                AgentDefinition.role,
                AgentSession.corps_id,
            )
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .filter(
                AgentSession.started_at >= cutoff,
                AgentSession.ended_at.isnot(None),
                AgentSession.status.in_([SessionStatus.COMPLETED, SessionStatus.FAILED]),
            )
        )
        if corps_id:
            query = query.filter(AgentSession.corps_id == corps_id)

        # Get all completed sessions with durations
        sessions = (
            db.query(AgentSession, AgentDefinition.role)
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .filter(
                AgentSession.started_at >= cutoff,
                AgentSession.ended_at.isnot(None),
            )
        )
        if corps_id:
            sessions = sessions.filter(AgentSession.corps_id == corps_id)

        role_durations: dict[str, list[float]] = {}
        for session, role in sessions.all():
            if session.started_at and session.ended_at:
                dur = (session.ended_at - session.started_at).total_seconds()
                role_durations.setdefault(role, []).append(dur)

        role_bottlenecks = []
        for role, durations in role_durations.items():
            durations.sort()
            n = len(durations)
            if n < 3:
                continue
            p50_idx = int(0.5 * (n - 1))
            p95_idx = int(0.95 * (n - 1))
            role_bottlenecks.append({
                "role": role,
                "session_count": n,
                "p50_duration_s": round(durations[p50_idx], 1),
                "p95_duration_s": round(durations[p95_idx], 1),
                "max_duration_s": round(durations[-1], 1),
                "mean_duration_s": round(sum(durations) / n, 1),
            })

        role_bottlenecks.sort(key=lambda x: x["p95_duration_s"], reverse=True)

        return {
            "period_days": period_days,
            "corps_id": corps_id,
            "generated_at": now.isoformat(),
            "latency_bottlenecks": latency_bottlenecks,
            "role_bottlenecks": role_bottlenecks,
        }
    finally:
        db.close()


@router.get("/metrics/trends")
def api_metrics_trends(
    metric_type: Optional[str] = None,
    corps_id: Optional[str] = None,
    period_days: int = 7,
):
    """Get velocity trends for metrics over time."""
    from backend.services.metrics import MetricType
    from backend.services.metrics_aggregation import MetricsAggregator

    db = _get_db_session()
    try:
        aggregator = MetricsAggregator(db)
        types_to_query = [metric_type] if metric_type else [mt.value for mt in MetricType]

        trends = []
        try:
            for mt in types_to_query:
                trend = aggregator.calculate_trends(
                    metric_type=mt,
                    period_days=period_days,
                    corps_id=corps_id,
                )
                if trend:
                    trends.append({
                        "metric_type": trend.metric_type,
                        "period_days": trend.period_days,
                        "avg_value": round(trend.avg_value, 4) if trend.avg_value else None,
                        "prev_period_avg": round(trend.prev_period_avg, 4) if trend.prev_period_avg else None,
                        "rate_of_change": round(trend.rate_of_change, 2) if trend.rate_of_change else None,
                        "direction": trend.trend_direction,
                        "corps_id": trend.corps_id,
                    })
        except Exception:
            pass  # metrics_events/trends tables may not exist yet

        return {
            "period_days": period_days,
            "corps_id": corps_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "trends": trends,
        }
    finally:
        db.close()


@router.get("/metrics/timeseries")
def api_metrics_timeseries(
    metric_types: Optional[str] = None,
    corps_id: Optional[str] = None,
    period_days: int = 7,
    granularity: str = "1h",
):
    """Get time-series metrics data for charting.

    Args:
        metric_types: Comma-separated metric types to fetch (e.g. "rep_completed,query_latency")
        corps_id: Filter by corps_id
        period_days: Number of days of history
        granularity: Bucket size: "1m", "5m", "1h", "1d"

    Returns:
        List of time buckets with metric aggregations.
    """
    from backend.services.metrics import MetricType
    from datetime import timedelta

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(days=period_days)

        # Parse requested metric types
        requested_types = []
        if metric_types:
            for mt_str in metric_types.split(","):
                mt_str = mt_str.strip().upper()
                try:
                    requested_types.append(mt_str)
                except ValueError:
                    pass  # Skip invalid metric types

        if not requested_types:
            requested_types = [mt.value for mt in MetricType]

        # Determine bucket size in seconds
        granularity_map = {"1m": 60, "5m": 300, "1h": 3600, "1d": 86400}
        bucket_seconds = granularity_map.get(granularity, 3600)

        # Query metrics events (if table exists)
        timeseries_data = []
        try:
            from backend.models.metrics import MetricsEvent

            query = db.query(MetricsEvent).filter(
                MetricsEvent.recorded_at >= start_time,
                MetricsEvent.metric_type.in_(requested_types),
            )
            if corps_id:
                query = query.filter(MetricsEvent.corps_id == corps_id)

            events = query.all()

            # Bucket events by granularity
            buckets = {}
            for event in events:
                # Calculate bucket key
                timestamp_seconds = int(event.recorded_at.timestamp())
                bucket_key = (timestamp_seconds // bucket_seconds) * bucket_seconds
                bucket_ts = datetime.fromtimestamp(bucket_key, tz=timezone.utc).isoformat()

                if bucket_ts not in buckets:
                    buckets[bucket_ts] = {
                        "timestamp": bucket_ts,
                    }

                # Aggregate by metric type
                metric_key = event.metric_type
                if metric_key not in buckets[bucket_ts]:
                    buckets[bucket_ts][metric_key] = 0
                buckets[bucket_ts][metric_key] += 1

            # Sort by timestamp and convert to list
            timeseries_data = sorted(
                buckets.values(),
                key=lambda x: x["timestamp"]
            )

        except Exception:
            pass  # metrics_events table may not exist yet

        return {
            "period_days": period_days,
            "granularity": granularity,
            "corps_id": corps_id,
            "metric_types": requested_types,
            "generated_at": now.isoformat(),
            "data": timeseries_data,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# System Health & Overview
# ---------------------------------------------------------------------------


@router.get("/system/health")
def v1_system_health():
    """Get swarm-wide health metrics."""
    from backend.services.system_health import get_swarm_health
    import dataclasses
    db = _get_db_session()
    try:
        health = get_swarm_health(db)
        return dataclasses.asdict(health)
    finally:
        db.close()


@router.get("/system/llm-usage")
def v1_llm_usage():
    """Get LLM provider usage statistics from the SmartRouter."""
    from backend.services.llm_client import SmartRouter

    llm_client = _get_llm_client()
    if llm_client is None:
        raise HTTPException(503, "LLM client not available")

    if isinstance(llm_client, SmartRouter):
        return llm_client.get_usage_stats()

    # Single provider (no SmartRouter) — return minimal info
    return {
        "active_provider": type(llm_client).__name__,
        "started_at": None,
        "providers": [{
            "name": type(llm_client).__name__,
            "capabilities": {
                "supports_images": llm_client.supports_images,
                "supports_native_tools": llm_client.supports_native_tools,
                "supports_caching": llm_client.supports_caching,
            },
            "stats": {"requests": 0, "successes": 0, "failures": 0,
                      "total_input_tokens": 0, "total_output_tokens": 0, "total_cached_tokens": 0},
        }],
        "failover_events": [],
        "total_requests": 0,
        "total_failures": 0,
    }


@router.get("/system/agents")
def v1_agents_overview():
    """Get all active agent sessions across all corps."""
    from sqlalchemy.orm import joinedload
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    from backend.models.corps import Corps

    db = _get_db_session()
    try:
        sessions = (
            db.query(AgentSession)
            .options(joinedload(AgentSession.definition))
            .filter(AgentSession.status == SessionStatus.ACTIVE)
            .all()
        )

        corps_ids = {s.corps_id for s in sessions if s.corps_id}
        corps_map = {}
        if corps_ids:
            corps_records = db.query(Corps).filter(Corps.id.in_(corps_ids)).all()
            corps_map = {c.id: c for c in corps_records}

        return [{
            "id": s.id,
            "definition_id": s.definition_id,
            "role": s.definition.role if s.definition else "unknown",
            "nickname": s.definition.nickname if s.definition else None,
            "classification": s.definition.classification.value if s.definition and s.definition.classification else None,
            "model_tier": s.definition.model_tier.value if s.definition else "unknown",
            "status": s.status.value,
            "corps_id": s.corps_id,
            "corps_name": corps_map[s.corps_id].name if s.corps_id and s.corps_id in corps_map else None,
            "started_at": s.started_at.isoformat() if s.started_at else None,
        } for s in sessions]
    finally:
        db.close()


@router.get("/system/work-log")
def v1_global_work_log(limit: int = 100, event_type: Optional[str] = None):
    """Get work log across all corps."""
    from backend.models.work_log import WorkLog
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition

    db = _get_db_session()
    try:
        query = db.query(WorkLog)
        if event_type:
            query = query.filter(WorkLog.event_type == event_type)
        logs = query.order_by(WorkLog.timestamp.desc()).limit(limit).all()

        # Build nickname lookup
        session_ids = {log.session_id for log in logs if log.session_id}
        nicknames = {}
        if session_ids:
            sessions = db.query(AgentSession).filter(AgentSession.id.in_(session_ids)).all()
            defn_ids = {s.definition_id for s in sessions if s.definition_id}
            defns = {d.id: d for d in db.query(AgentDefinition).filter(AgentDefinition.id.in_(defn_ids)).all()} if defn_ids else {}
            for s in sessions:
                defn = defns.get(s.definition_id)
                if defn and defn.nickname:
                    nicknames[s.id] = defn.nickname

        return [{
            "id": log.id,
            "session_id": log.session_id,
            "corps_id": log.corps_id,
            "role": log.role,
            "nickname": nicknames.get(log.session_id),
            "event_type": log.event_type,
            "phase": log.phase,
            "details": log.details,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        } for log in logs]
    finally:
        db.close()


@router.get("/corps/{corps_id}/work-log")
def v1_corps_work_log(corps_id: str, limit: int = 100, event_type: Optional[str] = None):
    """Get structured work log for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.models.work_log import WorkLog
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition

    db = _get_db_session()
    try:
        query = db.query(WorkLog).filter(WorkLog.corps_id == corps_id)
        if event_type:
            query = query.filter(WorkLog.event_type == event_type)
        logs = query.order_by(WorkLog.timestamp.desc()).limit(limit).all()

        session_ids = {log.session_id for log in logs if log.session_id}
        nicknames = {}
        if session_ids:
            sessions = db.query(AgentSession).filter(AgentSession.id.in_(session_ids)).all()
            defn_ids = {s.definition_id for s in sessions if s.definition_id}
            defns = {d.id: d for d in db.query(AgentDefinition).filter(AgentDefinition.id.in_(defn_ids)).all()} if defn_ids else {}
            for s in sessions:
                defn = defns.get(s.definition_id)
                if defn and defn.nickname:
                    nicknames[s.id] = defn.nickname

        return [{
            "id": log.id,
            "session_id": log.session_id,
            "corps_id": log.corps_id,
            "role": log.role,
            "nickname": nicknames.get(log.session_id),
            "event_type": log.event_type,
            "phase": log.phase,
            "details": log.details,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        } for log in logs]
    finally:
        db.close()


@router.get("/corps/{corps_id}/work-log/analysis")
def v1_work_log_analysis(corps_id: str):
    """Aggregate work log analysis: event distribution, tool usage, failure patterns."""
    _validate_id(corps_id, "corps_id")
    from backend.models.work_log import WorkLog
    from sqlalchemy import func

    db = _get_db_session()
    try:
        # Event type distribution
        event_counts = (
            db.query(WorkLog.event_type, func.count(WorkLog.id))
            .filter(WorkLog.corps_id == corps_id)
            .group_by(WorkLog.event_type)
            .all()
        )

        # Tool usage counts (from details JSON containing "tool" key)
        tool_logs = (
            db.query(WorkLog.details)
            .filter(WorkLog.corps_id == corps_id, WorkLog.event_type.in_(["tool_call", "tool_success", "tool_error"]))
            .all()
        )
        tool_usage: dict[str, dict] = {}
        for (details_str,) in tool_logs:
            if not details_str:
                continue
            try:
                details = json.loads(details_str) if details_str.startswith("{") else {}
            except (json.JSONDecodeError, TypeError):
                details = {}
            tool_name = details.get("tool", "unknown")
            if tool_name not in tool_usage:
                tool_usage[tool_name] = {"calls": 0, "successes": 0, "errors": 0}
            tool_usage[tool_name]["calls"] += 1
            if details.get("success"):
                tool_usage[tool_name]["successes"] += 1
            elif details.get("success") is False:
                tool_usage[tool_name]["errors"] += 1

        # Failure patterns (error details)
        failures = (
            db.query(WorkLog.role, WorkLog.details)
            .filter(WorkLog.corps_id == corps_id, WorkLog.event_type.in_(["agent_fail", "tool_error"]))
            .order_by(WorkLog.timestamp.desc())
            .limit(20)
            .all()
        )
        failure_details = []
        for role, details_str in failures:
            try:
                details = json.loads(details_str) if details_str and details_str.startswith("{") else {}
            except (json.JSONDecodeError, TypeError):
                details = {}
            failure_details.append({"role": role, "error": details.get("error", str(details_str)[:200])})

        # Total count
        total = db.query(func.count(WorkLog.id)).filter(WorkLog.corps_id == corps_id).scalar()

        return {
            "corps_id": corps_id,
            "total_events": total,
            "event_distribution": {et: count for et, count in event_counts},
            "tool_usage": tool_usage,
            "recent_failures": failure_details,
            "failure_rate": (
                sum(1 for f in failure_details) / max(total, 1) * 100
            ),
        }
    finally:
        db.close()


@router.get("/corps/{corps_id}/roster")
def v1_corps_roster(corps_id: str):
    """Get agent roster for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.models.agent_session import AgentSession
    from backend.models.agent_definition import AgentDefinition

    db = _get_db_session()
    try:
        sessions = (
            db.query(AgentSession)
            .filter(AgentSession.corps_id == corps_id)
            .all()
        )
        results = []
        for s in sessions:
            defn = db.get(AgentDefinition, s.definition_id) if s.definition_id else None
            results.append({
                "id": s.id,
                "definition_id": s.definition_id,
                "role": defn.role if defn else "unknown",
                "nickname": defn.nickname if defn else None,
                "model_tier": defn.model_tier.value if defn else "unknown",
                "status": s.status.value,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            })
        return results
    finally:
        db.close()


@router.put("/corps/{corps_id}/mode")
def v1_switch_corps_mode(corps_id: str, data: dict):
    """Switch corps operational mode."""
    _validate_id(corps_id, "corps_id")
    from backend.models.corps import Corps, CorpsMode

    mode_str = data.get("mode", "")
    try:
        new_mode = CorpsMode(mode_str)
    except ValueError:
        valid = [m.value for m in CorpsMode]
        raise HTTPException(400, f"Invalid mode '{mode_str}'. Valid: {valid}")

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, f"Corps '{corps_id}' not found")
        corps.mode = new_mode
        db.commit()
        return {"corps_id": corps_id, "mode": new_mode.value}
    finally:
        db.close()


@router.get("/shows")
def v1_list_shows():
    """List all shows from the database."""
    from backend.models.show import Show

    db = _get_db_session()
    try:
        shows = db.query(Show).all()
        return [{
            "id": s.id,
            "title": s.title,
            "status": s.status.value,
            "corps_id": s.corps_id,
            "description": s.description,
        } for s in shows]
    finally:
        db.close()


@router.get("/corps/{corps_id}/chat")
def v1_get_chat_history(corps_id: str, limit: int = 100):
    """Get chat message history for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.models.message import Message

    db = _get_db_session()
    try:
        messages = (
            db.query(Message)
            .filter(Message.corps_id == corps_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{
            "id": m.id,
            "type": m.type.value if m.type else "directive",
            "from_role": m.from_role,
            "to_role": m.to_role,
            "subject": m.subject,
            "body": m.body,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in reversed(messages)]
    finally:
        db.close()


@router.get("/corps/{corps_id}/scoresheet")
def v1_get_scoresheet(corps_id: str):
    """Get latest scoresheet for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.models.scoresheet import Scoresheet

    db = _get_db_session()
    try:
        scoresheet = (
            db.query(Scoresheet)
            .filter(Scoresheet.corps_id == corps_id)
            .order_by(Scoresheet.created_at.desc())
            .first()
        )
        if not scoresheet:
            return {"corps_id": corps_id, "scores": {}, "total": 0}
        return {
            "corps_id": corps_id,
            "id": scoresheet.id,
            "scores": scoresheet.scores if isinstance(scoresheet.scores, dict) else {},
            "total": scoresheet.total_score or 0,
            "created_at": scoresheet.created_at.isoformat() if scoresheet.created_at else None,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Performers
# ---------------------------------------------------------------------------


@router.get("/performers")
def v1_list_performers(status: Optional[str] = None):
    """List all performers with optional status filter."""
    from backend.models.performer import Performer, PerformerStatus
    from backend.services.performer_service import list_performers

    ps = None
    if status:
        try:
            ps = PerformerStatus(status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    db = _get_db_session()
    try:
        performers = list_performers(db, status=ps)
        return [{
            "id": p.id,
            "name": p.name,
            "role_type": p.role_type,
            "trust_score": round(p.trust_score, 1),
            "total_sessions": p.total_sessions,
            "successful_sessions": p.successful_sessions,
            "failed_sessions": p.failed_sessions,
            "status": p.status.value,
            "retirement_reason": p.retirement_reason,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        } for p in performers]
    finally:
        db.close()


@router.get("/performers/{performer_id}")
def v1_get_performer(performer_id: str):
    """Get performer detail."""
    from backend.services.performer_service import get_performer

    db = _get_db_session()
    try:
        p = get_performer(db, performer_id)
        if not p:
            raise HTTPException(404, "Performer not found")
        return {
            "id": p.id,
            "name": p.name,
            "role_type": p.role_type,
            "trust_score": round(p.trust_score, 1),
            "total_sessions": p.total_sessions,
            "successful_sessions": p.successful_sessions,
            "failed_sessions": p.failed_sessions,
            "status": p.status.value,
            "specialties": p.specialties,
            "retirement_reason": p.retirement_reason,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
    finally:
        db.close()


@router.post("/performers/{performer_id}/retire")
def v1_retire_performer(performer_id: str):
    """Retire a performer."""
    from backend.services.performer_service import retire_performer

    db = _get_db_session()
    try:
        p = retire_performer(db, performer_id, reason="Manual retirement via API")
        return {"id": p.id, "name": p.name, "status": p.status.value}
    except ValueError as e:
        raise HTTPException(404, str(e))
    finally:
        db.close()


@router.get("/performers/{performer_id}/ledger")
def v1_performer_ledger(performer_id: str):
    """Get capability ledger entries for a performer."""
    from backend.services.capability_ledger_service import get_entries_for_performer

    db = _get_db_session()
    try:
        entries = get_entries_for_performer(db, performer_id)
        return [{
            "id": e.id,
            "entry_type": e.entry_type.value,
            "role_type": e.role_type,
            "score": e.score,
            "trust_before": e.trust_before,
            "trust_after": e.trust_after,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        } for e in entries]
    finally:
        db.close()


@router.get("/performers/{performer_id}/stats")
def v1_performer_stats(performer_id: str):
    """Get aggregate stats from the capability ledger."""
    from backend.services.capability_ledger_service import get_performer_stats

    db = _get_db_session()
    try:
        return get_performer_stats(db, performer_id)
    finally:
        db.close()


@router.get("/performers/{performer_id}/genome")
def v1_performer_genome(performer_id: str):
    """Get performer genome (evolution traits)."""
    from backend.models.performer import Performer

    db = _get_db_session()
    try:
        p = db.get(Performer, performer_id)
        if not p:
            raise HTTPException(404, "Performer not found")
        return {
            "id": p.id,
            "name": p.name,
            "role_type": p.role_type,
            "trust_score": round(p.trust_score, 1),
            "specialties": p.specialties,
            "genome": p.genome if hasattr(p, "genome") else {},
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Segments
# ---------------------------------------------------------------------------


@router.get("/segments/{segment_id}")
def v1_get_segment(segment_id: str):
    """Get a segment by ID."""
    from backend.services.segment_service import get_segment

    db = _get_db_session()
    try:
        seg = get_segment(db, segment_id)
        if not seg:
            raise HTTPException(404, "Segment not found")
        return {
            "id": seg.id,
            "type": seg.type.value,
            "title": seg.title,
            "status": seg.status.value,
            "parent_id": seg.parent_id,
            "caption": seg.caption,
            "description": seg.description,
        }
    finally:
        db.close()


@router.get("/segments/{segment_id}/children")
def v1_get_segment_children(segment_id: str):
    """Get child segments of a given segment."""
    from backend.services.segment_service import get_children

    db = _get_db_session()
    try:
        children = get_children(db, segment_id)
        return [{
            "id": c.id,
            "type": c.type.value,
            "title": c.title,
            "status": c.status.value,
        } for c in children]
    finally:
        db.close()


@router.get("/segments/{segment_id}/reps")
def v1_get_reps_for_segment(segment_id: str):
    """Get reps for a specific segment."""
    from backend.services.rep_service import get_reps_for_segment

    db = _get_db_session()
    try:
        reps = get_reps_for_segment(db, segment_id)
        return [{"id": r.id, "status": r.status.value, "assigned_to": r.assigned_to,
                 "result": r.result, "error": r.error} for r in reps]
    finally:
        db.close()


@router.get("/segments/{segment_id}/tree")
def v1_get_segment_tree(segment_id: str):
    """Get full segment tree with reps."""
    from backend.services.segment_service import get_segment, get_children
    from backend.services.rep_service import get_reps_for_segment

    db = _get_db_session()
    try:
        def _build(sid):
            seg = get_segment(db, sid)
            if not seg:
                return None
            reps = get_reps_for_segment(db, sid)
            ch = get_children(db, sid)
            return {
                "id": seg.id,
                "type": seg.type.value,
                "title": seg.title,
                "description": seg.description,
                "status": seg.status.value,
                "caption": seg.caption,
                "reps": [{
                    "id": r.id,
                    "status": r.status.value,
                    "result": r.result,
                    "error": r.error,
                    "assigned_to": r.assigned_to,
                } for r in reps],
                "children": [_build(c.id) for c in ch],
            }

        tree = _build(segment_id)
        if not tree:
            raise HTTPException(404, "Segment not found")
        return tree
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Metronome, Chat send, Templates, Judging, Evolution
# ---------------------------------------------------------------------------


@router.post("/corps/{corps_id}/chat")
def v1_send_chat(corps_id: str, data: dict):
    """Send a chat message to a corps agent."""
    _validate_id(corps_id, "corps_id")
    from backend.api.app import get_task_manager

    content = data.get("content", "")
    to_role = data.get("to_role", "executive_director")
    if not content:
        raise HTTPException(400, "content is required")

    tm = get_task_manager()
    if not tm:
        raise HTTPException(503, "Task manager not available")

    db = _get_db_session()
    try:
        # Record user message
        from backend.models.message import Message, MessageType
        msg = Message(
            corps_id=corps_id,
            type=MessageType.DIRECTIVE,
            from_role="user",
            to_role=to_role,
            subject="User chat",
            body=content,
        )
        db.add(msg)
        db.commit()

        # Find and trigger the target agent
        session_id = tm.get_session_for_role(db, corps_id, to_role)
        if session_id:
            tm.start_agent(
                session_id=session_id,
                task_description=f"Respond to user message: {content[:200]}",
            )

        return {
            "id": msg.id,
            "status": "sent",
            "to_role": to_role,
        }
    finally:
        db.close()


@router.post("/corps/{corps_id}/metronome/tick")
def v1_metronome_tick(corps_id: str):
    """Manual metronome tick for a corps."""
    _validate_id(corps_id, "corps_id")
    from backend.tools.metronome import tick

    db = _get_db_session()
    try:
        result = tick(db, corps_id)
        return {
            "checked": result.checked,
            "reclaimed": result.reclaimed,
            "reclaimed_rep_ids": result.reclaimed_rep_ids,
        }
    finally:
        db.close()


@router.get("/evolution/selection-events")
def v1_selection_events(performer_id: Optional[str] = None, limit: int = 50):
    """Get selection/drafting events."""
    from backend.models.performer import Performer

    db = _get_db_session()
    try:
        # Selection events are stored in performer audit trail
        # Return recent performer status changes as selection events
        query = db.query(Performer)
        if performer_id:
            query = query.filter(Performer.id == performer_id)
        performers = query.order_by(Performer.updated_at.desc()).limit(limit).all()
        return [{
            "performer_id": p.id,
            "name": p.name,
            "role_type": p.role_type,
            "status": p.status.value,
            "trust_score": round(p.trust_score, 1),
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        } for p in performers]
    finally:
        db.close()


@router.get("/evolution/mutations")
def v1_mutations(limit: int = 50):
    """Get recent mutation/ledger entries across all performers."""
    from backend.models.capability_ledger import CapabilityLedgerEntry

    db = _get_db_session()
    try:
        entries = (
            db.query(CapabilityLedgerEntry)
            .order_by(CapabilityLedgerEntry.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{
            "id": e.id,
            "performer_id": e.performer_id,
            "entry_type": e.entry_type.value,
            "role_type": e.role_type,
            "score": e.score,
            "trust_before": e.trust_before,
            "trust_after": e.trust_after,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        } for e in entries]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Improvement: Basics, Critique, Banquet
# ---------------------------------------------------------------------------

@router.post("/corps/{corps_id}/basics/{caption}")
def v1_run_basics(corps_id: str, caption: str):
    """Run basics drill for a caption section."""
    from backend.services.improvement import run_basics
    db = _get_db_session()
    try:
        result = run_basics(db, corps_id, caption)
        return result
    finally:
        db.close()


@router.get("/reps/{rep_id}/critique")
def v1_get_critique(rep_id: str):
    """Get critique/feedback for a rep."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        rep = db.query(Reputation).filter(Reputation.id == rep_id).first()
        if not rep:
            raise HTTPException(404, "Rep not found")
        return {
            "id": rep.id,
            "corps_id": rep.corps_id,
            "agent_id": rep.agent_id,
            "score": rep.score,
            "critique": rep.critique,
            "dimension": rep.dimension,
            "created_at": rep.created_at.isoformat() if rep.created_at else None,
        }
    finally:
        db.close()


@router.get("/corps/{corps_id}/banquet")
def v1_get_banquet(corps_id: str):
    """Get banquet/awards data for a corps."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        reps = (
            db.query(Reputation)
            .filter(Reputation.corps_id == corps_id)
            .order_by(Reputation.score.desc())
            .limit(50)
            .all()
        )
        return [{
            "id": r.id,
            "agent_id": r.agent_id,
            "score": r.score,
            "dimension": r.dimension,
            "critique": r.critique,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in reps]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Messages: Polling
# ---------------------------------------------------------------------------

@router.get("/corps/{corps_id}/messages/poll")
def v1_poll_messages(corps_id: str, since: str = None):
    """Poll for new messages since a timestamp."""
    from backend.models.message import Message
    db = _get_db_session()
    try:
        q = db.query(Message).filter(Message.corps_id == corps_id)
        if since:
            from datetime import datetime
            q = q.filter(Message.created_at > datetime.fromisoformat(since))
        messages = q.order_by(Message.created_at.asc()).limit(100).all()
        return [{
            "id": m.id,
            "from_agent": m.from_agent,
            "to_agent": m.to_agent,
            "content": m.content,
            "msg_type": m.msg_type,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in messages]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Shows: CRUD
# ---------------------------------------------------------------------------

@router.get("/shows")
def v1_list_shows():
    """List all shows from filesystem."""
    from backend.services.show_persistence import list_shows
    shows = list_shows()
    return shows


@router.post("/shows")
def v1_create_show(payload: dict):
    """Create a new show."""
    from backend.services.show_persistence import create_show
    from pathlib import Path
    title = payload.get("title", "untitled")
    description = payload.get("description", "")
    show_path = create_show(title, Path("shows"))
    slug = show_path.name
    # Write description to spec if provided
    if description:
        from backend.services.show_persistence import write_spec
        write_spec(show_path, f"# {title}\n\n{description}\n")
    return {"slug": slug, "title": title, "status": "draft"}


@router.post("/shows/{slug}/activate")
def v1_activate_show(slug: str):
    """Activate a show (spawn corps, begin immediately)."""
    from backend.services.show_persistence import get_show
    show = get_show(slug)
    if not show:
        raise HTTPException(404, "Show not found")
    from backend.services.show_persistence import update_show_status
    update_show_status(slug, "published")
    return {"status": "activated", "slug": slug}


@router.delete("/shows/{slug}")
def v1_delete_show(slug: str):
    """Delete/archive a show."""
    import shutil
    from pathlib import Path
    show_dir = Path("shows") / slug
    if not show_dir.exists():
        raise HTTPException(404, "Show not found")
    shutil.rmtree(show_dir)
    return {"status": "deleted", "slug": slug}


# ---------------------------------------------------------------------------
# Judging: Tapes
# ---------------------------------------------------------------------------

@router.get("/judging/tapes")
def v1_list_judging_tapes(corps_id: str = None, limit: int = 50):
    """List judging tapes (score records)."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        q = db.query(Reputation)
        if corps_id:
            q = q.filter(Reputation.corps_id == corps_id)
        tapes = q.order_by(Reputation.created_at.desc()).limit(limit).all()
        return [{
            "id": t.id,
            "corps_id": t.corps_id,
            "agent_id": t.agent_id,
            "dimension": t.dimension,
            "score": t.score,
            "critique": t.critique,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in tapes]
    finally:
        db.close()


@router.get("/judging/tapes/{tape_id}")
def v1_get_judging_tape(tape_id: str):
    """Get a single judging tape."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        tape = db.query(Reputation).filter(Reputation.id == tape_id).first()
        if not tape:
            raise HTTPException(404, "Tape not found")
        return {
            "id": tape.id,
            "corps_id": tape.corps_id,
            "agent_id": tape.agent_id,
            "dimension": tape.dimension,
            "score": tape.score,
            "critique": tape.critique,
            "created_at": tape.created_at.isoformat() if tape.created_at else None,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

@router.get("/templates")
def v1_list_templates():
    """List available show templates."""
    from pathlib import Path
    import yaml
    templates_dir = Path("templates")
    if not templates_dir.exists():
        return []
    results = []
    for t in templates_dir.iterdir():
        if t.is_dir() and (t / "template.yaml").exists():
            with open(t / "template.yaml") as f:
                data = yaml.safe_load(f)
            results.append({"id": t.name, **data})
    return results


@router.get("/templates/{template_id}")
def v1_get_template(template_id: str):
    """Get a single template."""
    from pathlib import Path
    import yaml
    template_path = Path("templates") / template_id / "template.yaml"
    if not template_path.exists():
        raise HTTPException(404, "Template not found")
    with open(template_path) as f:
        data = yaml.safe_load(f)
    return {"id": template_id, **data}


@router.post("/templates/{template_id}/instantiate")
def v1_instantiate_template(template_id: str, payload: dict):
    """Create a new show from a template."""
    from pathlib import Path
    import yaml
    import shutil
    template_dir = Path("templates") / template_id
    if not template_dir.exists():
        raise HTTPException(404, "Template not found")
    slug = payload.get("slug", template_id + "-instance")
    show_dir = Path("shows") / slug
    if show_dir.exists():
        raise HTTPException(409, "Show already exists")
    shutil.copytree(template_dir, show_dir)
    status_path = show_dir / "status.yaml"
    if status_path.exists():
        with open(status_path) as f:
            status = yaml.safe_load(f) or {}
        status["status"] = "draft"
        status["title"] = payload.get("title", slug)
        with open(status_path, "w") as f:
            yaml.dump(status, f)
    return {"slug": slug, "status": "created"}


# ---------------------------------------------------------------------------
# Seance
# ---------------------------------------------------------------------------

@router.post("/seance/query")
def v1_seance_query(payload: dict):
    """Query the seance system (ED retrospective chat)."""
    from backend.services.ed_chat import query_ed
    corps_id = payload.get("corps_id")
    question = payload.get("question", "")
    if not corps_id or not question:
        raise HTTPException(400, "corps_id and question required")
    db = _get_db_session()
    try:
        result = query_ed(db, corps_id, question)
        return result
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@router.get("/admin/corps")
def v1_admin_list_corps():
    """Admin view of all corps with full DB details."""
    from backend.models.corps import Corps
    db = _get_db_session()
    try:
        corps_list = db.query(Corps).all()
        return [{
            "id": c.id,
            "name": c.name,
            "status": c.status.value if c.status else None,
            "mode": c.mode.value if c.mode else None,
            "theme_id": c.theme_id,
            "mascot": c.mascot,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        } for c in corps_list]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Shows: Additional operations
# ---------------------------------------------------------------------------

@router.get("/shows-overview")
def v1_shows_overview():
    """Get shows overview with status counts and recent activity."""
    from backend.services.show_persistence import list_shows
    shows = list_shows()
    status_counts = {}
    for s in shows:
        st = s.get("status", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1
    return {
        "shows": shows,
        "total": len(shows),
        "status_counts": status_counts,
    }


@router.get("/shows/{slug}/detail")
def v1_get_show(slug: str):
    """Get a single show's full detail."""
    from backend.services.show_persistence import get_show
    show = get_show(slug)
    if not show:
        raise HTTPException(404, "Show not found")
    return show


@router.post("/shows/{slug}/tour")
def v1_toggle_tour(slug: str, payload: dict):
    """Toggle tour mode for a show."""
    from backend.services.show_persistence import get_show, update_show_status
    show = get_show(slug)
    if not show:
        raise HTTPException(404, "Show not found")
    enable = payload.get("enable", True)
    new_status = "on_tour" if enable else "published"
    update_show_status(slug, new_status)
    return {"slug": slug, "status": new_status}


@router.post("/shows/{slug}/complete")
def v1_complete_show(slug: str):
    """Mark a show as completed."""
    from backend.services.show_persistence import get_show, update_show_status
    show = get_show(slug)
    if not show:
        raise HTTPException(404, "Show not found")
    update_show_status(slug, "completed")
    return {"slug": slug, "status": "completed"}


# ---------------------------------------------------------------------------
# Admin: Corps detail (singleton admin corps)
# ---------------------------------------------------------------------------

@router.get("/admin/admin-corps")
def v1_get_admin_corps():
    """Get the admin/bar corps with its roster."""
    from backend.models.corps import Corps
    from backend.models.agent_definition import AgentDefinition
    db = _get_db_session()
    try:
        # Find the admin corps (typically "the-bar" or first corps)
        admin = db.query(Corps).filter(Corps.id == "the-bar").first()
        if not admin:
            admin = db.query(Corps).first()
        if not admin:
            raise HTTPException(404, "No admin corps found")
        agents = db.query(AgentDefinition).filter(
            AgentDefinition.corps_id == admin.id
        ).all()
        return {
            "id": admin.id,
            "name": admin.name,
            "status": admin.status.value if admin.status else None,
            "mode": admin.mode.value if admin.mode else None,
            "roster": [{
                "id": a.id,
                "role": a.role,
                "name": a.nickname or a.role,
            } for a in agents],
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Judging: Critique actions & tape export
# ---------------------------------------------------------------------------

@router.get("/judging/corps/{corps_id}/actions")
def v1_critique_actions(corps_id: str):
    """Get critique action items for a corps."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        reps = (
            db.query(Reputation)
            .filter(Reputation.corps_id == corps_id)
            .filter(Reputation.critique.isnot(None))
            .order_by(Reputation.created_at.desc())
            .limit(20)
            .all()
        )
        return [{
            "id": r.id,
            "agent_id": r.agent_id,
            "dimension": r.dimension,
            "score": r.score,
            "critique": r.critique,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in reps]
    finally:
        db.close()


@router.get("/judging/corps/{corps_id}/tapes/{rep_id}/export")
def v1_export_judge_tape(corps_id: str, rep_id: str):
    """Export a judging tape as markdown."""
    from backend.models.reputation import Reputation
    db = _get_db_session()
    try:
        rep = db.query(Reputation).filter(
            Reputation.id == rep_id,
            Reputation.corps_id == corps_id,
        ).first()
        if not rep:
            raise HTTPException(404, "Tape not found")
        md = f"# Judging Tape: {rep.id}\n\n"
        md += f"**Corps:** {rep.corps_id}\n"
        md += f"**Agent:** {rep.agent_id}\n"
        md += f"**Dimension:** {rep.dimension}\n"
        md += f"**Score:** {rep.score}\n\n"
        md += f"## Critique\n\n{rep.critique or 'No critique recorded.'}\n"
        return {"markdown": md}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Evolution: Simulate mutation
# ---------------------------------------------------------------------------

@router.post("/evolution/simulate-mutation")
def v1_simulate_mutation(payload: dict):
    """Simulate a mutation on an agent definition."""
    from backend.models.agent_definition import AgentDefinition
    db = _get_db_session()
    try:
        def_id = payload.get("definition_id")
        changes = payload.get("changes", {})
        reason = payload.get("reason", "manual simulation")
        defn = db.query(AgentDefinition).filter(AgentDefinition.id == def_id).first()
        if not defn:
            raise HTTPException(404, "Agent definition not found")
        # Return a preview of what the mutation would produce
        preview = {
            "definition_id": def_id,
            "current_role": defn.role,
            "current_system_prompt": defn.system_prompt[:200] if defn.system_prompt else None,
            "proposed_changes": changes,
            "reason": reason,
            "status": "simulated",
        }
        return preview
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Sessions: Activity
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/activity")
def v1_session_activity(session_id: str):
    """Get activity log for a session."""
    from backend.models.agent_session import AgentSession
    from backend.models.work_log import WorkLog
    db = _get_db_session()
    try:
        session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
        if not session:
            raise HTTPException(404, "Session not found")
        logs = (
            db.query(WorkLog)
            .filter(WorkLog.session_id == session_id)
            .order_by(WorkLog.created_at.asc())
            .all()
        )
        return {
            "session_id": session_id,
            "status": session.status.value if session.status else None,
            "entries": [{
                "id": w.id,
                "action": w.action,
                "details": w.details,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            } for w in logs],
        }
    finally:
        db.close()


# =========================================================================
# PORTED LEGACY ENDPOINTS (Phase 1)
# =========================================================================

# ---------------------------------------------------------------------------
# Corps Commands (ported from legacy corps_routes.py)
# ---------------------------------------------------------------------------

CORPS_COMMANDS = {
    "resume_hut": {"label": "Resume, Hut!", "description": "Wake all agents and begin/resume work", "category": "control"},
    "attention": {"label": "Attention!", "description": "All agents pause and report current status", "category": "control"},
    "at_ease": {"label": "At Ease", "description": "Finish current tasks then idle", "category": "control"},
    "dismissed": {"label": "Dismissed", "description": "Stop all agents, disband the corps", "category": "control"},
    "basics": {"label": "Basics", "description": "Switch to basics rehearsal mode (manual override)", "category": "rehearsal"},
    "sectionals": {"label": "Sectionals", "description": "Switch to sectionals rehearsal mode (manual override)", "category": "rehearsal"},
    "full_ensemble": {"label": "Full Ensemble", "description": "Switch to full ensemble rehearsal (manual override)", "category": "rehearsal"},
    "run_through": {"label": "Run Through", "description": "Full run-through rehearsal mode (manual override)", "category": "rehearsal"},
    "go_on_tour": {"label": "Go On Tour", "description": "Autonomous execution — agents work independently", "category": "execution"},
    "return_to_camps": {"label": "Return to Camps", "description": "Back to planning phase", "category": "execution"},
    "metronome_tick": {"label": "Metronome Tick", "description": "Manual metronome tick — reclaim stale work", "category": "system"},
    "merge_check": {"label": "Merge Check", "description": "Check and merge completed work", "category": "system"},
}


@router.get("/corps-commands")
def v1_list_corps_commands():
    """List all available corps commands."""
    return CORPS_COMMANDS


class CorpsCommandRequest(BaseModel):
    command: str


@router.post("/corps/{corps_id}/command")
async def v1_execute_corps_command(corps_id: str, data: CorpsCommandRequest):
    """Execute a corps command."""
    from backend.models.corps import Corps, CorpsStatus, RehearsalMode
    from backend.services.corps_service import (
        go_on_tour, return_to_camps, set_rehearsal_mode, disband_corps, merge_monitor_check, CorpsError,
    )
    from backend.tools.metronome import tick
    from backend.api.app import get_task_manager, manager

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, "Corps not found")

        cmd = data.command
        if cmd not in CORPS_COMMANDS:
            raise HTTPException(400, f"Unknown command: {cmd}")

        result = {"command": cmd, "corps_id": corps_id, "status": "ok", "detail": ""}
        tm = get_task_manager()

        if cmd == "resume_hut":
            if tm:
                from backend.models.agent_session import AgentSession, SessionStatus
                from backend.models.agent_definition import AgentDefinition
                unique_roles = (
                    db.query(AgentDefinition.role)
                    .join(AgentSession)
                    .filter(AgentSession.corps_id == corps_id)
                    .distinct()
                    .all()
                )
                woken = 0
                for (role,) in unique_roles:
                    sid = tm.get_session_for_role(db, corps_id, role)
                    if sid and not tm.is_active(sid):
                        tm.start_agent(
                            session_id=sid,
                            task_description=(
                                f"RESUME HUT! The corps has been called to attention and work is resuming. "
                                f"Check your current assignments and continue working. Corps ID: {corps_id}"
                            ),
                            corps_id=corps_id,
                        )
                        woken += 1
                result["detail"] = f"Woke {woken} agents"
            await manager.broadcast(corps_id, {
                "type": "command", "command": "resume_hut",
                "content": "Resume, Hut! All agents resuming work.",
            })

        elif cmd == "attention":
            if tm:
                ed_session = tm.get_session_for_role(db, corps_id, "executive_director")
                if ed_session and not tm.is_active(ed_session):
                    tm.start_agent(
                        session_id=ed_session,
                        task_description=(
                            f"ATTENTION! The director has called the corps to attention. "
                            f"Report the current status of all work in progress. Corps ID: {corps_id}. "
                            f"Check all segments and reps, then provide a full status report."
                        ),
                        corps_id=corps_id,
                    )
            await manager.broadcast(corps_id, {
                "type": "command", "command": "attention",
                "content": "Attention! Status report requested.",
            })
            result["detail"] = "Status report requested from ED"

        elif cmd == "at_ease":
            corps.status = CorpsStatus.WINTER_CAMPS
            db.commit()
            await manager.broadcast(corps_id, {
                "type": "command", "command": "at_ease",
                "content": "At ease. Returning to Winter Camps. Finishing current tasks, then standing by.",
            })
            result["detail"] = "Corps returned to Winter Camps"

        elif cmd == "dismissed":
            try:
                disband_corps(db, corps_id)
                await manager.broadcast(corps_id, {
                    "type": "command", "command": "dismissed",
                    "content": "Corps dismissed. All agents standing down.",
                })
                result["detail"] = "Corps disbanded"
            except CorpsError as e:
                raise HTTPException(400, str(e))

        elif cmd in ("basics", "sectionals", "full_ensemble", "run_through"):
            try:
                mode = RehearsalMode(cmd)
                set_rehearsal_mode(db, corps_id, mode)
                await manager.broadcast(corps_id, {
                    "type": "command", "command": cmd,
                    "content": f"Rehearsal mode set to: {cmd.replace('_', ' ')}",
                })
                result["detail"] = f"Rehearsal mode: {cmd}"
            except (ValueError, CorpsError) as e:
                raise HTTPException(400, str(e))

        elif cmd == "go_on_tour":
            try:
                go_on_tour(db, corps_id)
                await manager.broadcast(corps_id, {
                    "type": "command", "command": "go_on_tour",
                    "content": "On Tour — autonomous execution active.",
                })
                result["detail"] = "On Tour"
            except CorpsError as e:
                raise HTTPException(400, str(e))

        elif cmd == "return_to_camps":
            try:
                return_to_camps(db, corps_id)
                await manager.broadcast(corps_id, {
                    "type": "command", "command": "return_to_camps",
                    "content": "Returned to Winter Camps — planning phase.",
                })
                result["detail"] = "Returned to Winter Camps"
            except CorpsError as e:
                raise HTTPException(400, str(e))

        elif cmd == "metronome_tick":
            tick_result = tick(db, corps_id)
            await manager.broadcast(corps_id, {
                "type": "metronome_tick", "corps_id": corps_id,
                "checked": tick_result.checked, "reclaimed": tick_result.reclaimed,
            })
            result["detail"] = f"Checked {tick_result.checked}, reclaimed {tick_result.reclaimed}"

        elif cmd == "merge_check":
            merge_result = merge_monitor_check(db, corps_id)
            await manager.broadcast(corps_id, {
                "type": "merge_check", "corps_id": corps_id,
                "merged": merge_result.merged, "conflicts": merge_result.conflicts,
            })
            result["detail"] = f"Merged {merge_result.merged}, conflicts {merge_result.conflicts}"

        return result
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Corps Theme
# ---------------------------------------------------------------------------

class CorpsThemeUpdateRequest(BaseModel):
    theme_id: Optional[str] = None
    mascot: Optional[str] = None
    uniform_concept: Optional[str] = None


@router.get("/corps/{corps_id}/theme")
def v1_get_corps_theme(corps_id: str):
    from backend.models.corps import Corps
    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, "Corps not found")
        return {"corps_id": corps.id, "theme_id": corps.theme_id,
                "mascot": corps.mascot, "uniform_concept": corps.uniform_concept}
    finally:
        db.close()


@router.put("/corps/{corps_id}/theme")
def v1_update_corps_theme(corps_id: str, data: CorpsThemeUpdateRequest):
    from backend.services.corps_service import update_corps_theme, CorpsError
    db = _get_db_session()
    try:
        corps = update_corps_theme(db, corps_id, theme_id=data.theme_id,
                                   mascot=data.mascot, uniform_concept=data.uniform_concept)
        return {"corps_id": corps.id, "theme_id": corps.theme_id,
                "mascot": corps.mascot, "uniform_concept": corps.uniform_concept}
    except CorpsError as e:
        raise HTTPException(404, str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Corps Progression & Rehearsal
# ---------------------------------------------------------------------------

@router.get("/corps/{corps_id}/progression")
def v1_get_progression(corps_id: str):
    """Current rehearsal mode, milestones, and what's needed to advance."""
    from backend.models.corps import Corps, RehearsalMode
    from backend.services.rehearsal_progression import (
        _basics_met, _sectionals_met, _full_ensemble_met, _next_mode,
    )
    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, "Corps not found")
        current = corps.rehearsal_mode
        checks = {
            RehearsalMode.BASICS: ("basics_met", _basics_met),
            RehearsalMode.SECTIONALS: ("sectionals_met", _sectionals_met),
            RehearsalMode.FULL_ENSEMBLE: ("full_ensemble_met", _full_ensemble_met),
        }
        milestones = {}
        for mode, (key, fn) in checks.items():
            milestones[key] = fn(db, corps_id)
        return {
            "corps_id": corps_id,
            "status": corps.status.value,
            "current_mode": current.value if current else None,
            "next_mode": _next_mode(current).value if current and _next_mode(current) else None,
            "milestones": milestones,
        }
    finally:
        db.close()


class RehearsalModeSetRequest(BaseModel):
    mode: str


@router.post("/corps/{corps_id}/rehearsal-mode")
def v1_set_rehearsal_mode(corps_id: str, data: RehearsalModeSetRequest):
    from backend.models.corps import RehearsalMode
    from backend.services.corps_service import set_rehearsal_mode, CorpsError
    db = _get_db_session()
    try:
        mode = RehearsalMode(data.mode)
        corps = set_rehearsal_mode(db, corps_id, mode)
        return {"id": corps.id, "rehearsal_mode": corps.rehearsal_mode.value}
    except (ValueError, CorpsError) as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Corps Metrics, Evaluate, Season Transition, Ageouts, Merge Check
# ---------------------------------------------------------------------------

@router.get("/corps/{corps_id}/metrics")
def v1_corps_metrics(corps_id: str):
    """Get aggregate metrics for a corps."""
    from backend.services.metrics_collector import collect_corps_metrics
    import dataclasses
    db = _get_db_session()
    try:
        metrics = collect_corps_metrics(db, corps_id)
        return dataclasses.asdict(metrics)
    finally:
        db.close()


@router.post("/corps/{corps_id}/evaluate")
def v1_evaluate_corps(corps_id: str):
    """Run post-show evaluation on all performers in a corps."""
    from backend.services.evaluation_service import evaluate_corps
    db = _get_db_session()
    try:
        return evaluate_corps(db, corps_id)
    finally:
        db.close()


@router.post("/corps/{corps_id}/season-transition")
def v1_season_transition(corps_id: str):
    """Run end-of-season lifecycle: age performers, check ageouts."""
    from backend.services.lifecycle_manager import conduct_season_transition
    db = _get_db_session()
    try:
        return conduct_season_transition(db, corps_id)
    finally:
        db.close()


@router.get("/corps/{corps_id}/ageouts")
def v1_get_ageouts(corps_id: str):
    """Get performers approaching ageout for this corps."""
    from backend.services.lifecycle_manager import check_ageouts
    db = _get_db_session()
    try:
        ageouts = check_ageouts(db)
        return [{"id": p.id, "name": p.name, "age": p.age, "role_type": p.role_type} for p in ageouts]
    finally:
        db.close()


@router.post("/corps/{corps_id}/merge-check")
def v1_merge_check(corps_id: str):
    from backend.services.corps_service import merge_monitor_check
    db = _get_db_session()
    try:
        result = merge_monitor_check(db, corps_id)
        return {
            "checked": result.checked,
            "merged": result.merged,
            "conflicts": result.conflicts,
            "merged_segment_ids": result.merged_segment_ids,
            "conflict_segment_ids": result.conflict_segment_ids,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Heartbeat & System Metronome Tick
# ---------------------------------------------------------------------------

@router.post("/heartbeat")
async def v1_heartbeat():
    """External heartbeat endpoint for cron-based wakeup."""
    import json as _json
    from pathlib import Path as _Path
    from backend.services.metronome_heartbeat import heartbeat_tick
    from backend.tools.metronome_orchestrator import gather_corps_health, get_active_corps
    from datetime import datetime as _dt, timezone as _tz

    db = _get_db_session()
    try:
        tick_timestamp = _dt.now(_tz.utc)
        brass_result = heartbeat_tick(db)

        alerts = []
        try:
            active_corps = get_active_corps(db)
            corps_health_list = []
            for corps in active_corps:
                try:
                    health = gather_corps_health(db, corps)
                    if not health.ed_responding and not health.pc_responding:
                        alert = f"RED FLAG: Corps {health.corps_id[:8]} ({health.corps_name}) - No ED/PC response"
                        alerts.append(alert)
                    corps_health_list.append({
                        "corps_id": health.corps_id,
                        "corps_name": health.corps_name,
                        "status": health.status,
                        "rehearsal_mode": health.rehearsal_mode,
                        "active_sessions": health.active_sessions,
                        "completed_sessions": health.completed_sessions,
                        "failed_sessions": health.failed_sessions,
                        "stalled_reps": len(health.stalled_reps),
                        "ed_responding": health.ed_responding,
                        "pc_responding": health.pc_responding,
                        "tick_duration_ms": health.tick_duration_ms,
                    })
                except Exception as e:
                    alerts.append(f"Failed to gather health for corps {corps.id}: {e}")

            visual_result = {"total_corps": len(active_corps), "corps_health": corps_health_list}
        except Exception as e:
            visual_result = {"total_corps": 0, "corps_health": [], "error": str(e)}
            alerts.append(f"Failed to gather swarm status: {e}")

        heartbeat_result = {
            "status": "ok",
            "timestamp": brass_result["timestamp"],
            "ten_hut_sent": brass_result["ten_hut"]["sent"],
            "resume_hut_sent": brass_result["resume_hut"]["sent"],
            "corps_pinged": brass_result["ten_hut"]["corps"],
            "stalled_corps": brass_result["resume_hut"]["stalled_corps"],
            "swarm_status": visual_result,
            "errors": brass_result["errors"] + alerts,
        }

        # Write structured logs
        try:
            log_dir = _Path("logs/metronome")
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp_clean = tick_timestamp.isoformat().replace(":", "-").replace(".", "-")
            json_log_path = log_dir / f"{timestamp_clean}.json"
            with open(json_log_path, "w") as f:
                _json.dump(heartbeat_result, f, indent=2)
            if alerts:
                alert_log_path = log_dir / "alerts.log"
                with open(alert_log_path, "a") as f:
                    for alert in alerts:
                        f.write(f"[{tick_timestamp.isoformat()}] {alert}\n")
        except Exception:
            pass

        return heartbeat_result
    finally:
        db.close()


@router.post("/metronome/tick")
def v1_metronome_system_tick():
    """System-wide metronome tick."""
    from backend.tools.metronome import tick
    from backend.services.corps_service import merge_monitor_check
    from backend.models.corps import Corps, CorpsStatus
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition
    from backend.models.rep import Rep, RepStatus
    from backend.models.show import Show
    from backend.models.segment import Segment
    from datetime import datetime as _dt, timezone as _tz

    STALLED_THRESHOLD_SECONDS = 300

    db = _get_db_session()
    try:
        active_corps = (
            db.query(Corps)
            .filter(Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]))
            .all()
        )
        corps_results = []
        for corps in active_corps:
            met_result = tick(db, corps.id)
            merge_result = merge_monitor_check(db, corps.id)

            sessions = db.query(AgentSession).filter(AgentSession.corps_id == corps.id).all()
            active_sessions = sum(1 for s in sessions if s.status == SessionStatus.ACTIVE)
            completed_sessions = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
            failed_sessions = sum(1 for s in sessions if s.status == SessionStatus.FAILED)

            show = db.query(Show).filter(Show.corps_id == corps.id).first()
            reps: list = []
            if show and show.segment_root_id:
                def _collect_segment_ids(seg_id):
                    ids = [seg_id]
                    children = db.query(Segment).filter(Segment.parent_id == seg_id).all()
                    for c in children:
                        ids.extend(_collect_segment_ids(c.id))
                    return ids
                seg_ids = _collect_segment_ids(show.segment_root_id)
                reps = db.query(Rep).filter(Rep.segment_id.in_(seg_ids)).all() if seg_ids else []

            rep_counts = {
                "pending": sum(1 for r in reps if r.status == RepStatus.PENDING),
                "assigned": sum(1 for r in reps if r.status == RepStatus.ASSIGNED),
                "in_progress": sum(1 for r in reps if r.status == RepStatus.IN_PROGRESS),
                "completed": sum(1 for r in reps if r.status == RepStatus.COMPLETED),
                "failed": sum(1 for r in reps if r.status == RepStatus.FAILED),
            }

            now = _dt.now(_tz.utc)
            stalled_reps = []
            for r in reps:
                if r.status in (RepStatus.PENDING, RepStatus.ASSIGNED) and r.updated_at:
                    idle_secs = (now - r.updated_at.replace(tzinfo=_tz.utc)).total_seconds()
                    if idle_secs > STALLED_THRESHOLD_SECONDS:
                        stalled_reps.append({
                            "rep_id": r.id, "status": r.status.value,
                            "idle_seconds": round(idle_secs),
                            "last_updated": r.updated_at.isoformat(),
                        })

            staff_roles = ["executive_director", "program_coordinator", "brass_caption_head",
                           "percussion_caption_head", "guard_caption_head", "visual_caption_head"]
            liveness = {}
            for role in staff_roles:
                role_sessions = (
                    db.query(AgentSession)
                    .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
                    .filter(AgentSession.corps_id == corps.id, AgentDefinition.role == role)
                    .all()
                )
                liveness[role] = any(s.status == SessionStatus.ACTIVE for s in role_sessions)

            corps_results.append({
                "corps_id": corps.id, "corps_name": corps.name,
                "corps_status": corps.status.value,
                "rehearsal_mode": corps.rehearsal_mode.value if corps.rehearsal_mode else None,
                "metronome": {
                    "checked": met_result.checked, "reclaimed": met_result.reclaimed,
                    "reclaimed_rep_ids": met_result.reclaimed_rep_ids,
                    "idle_kicked": met_result.idle_kicked,
                    "idle_kicked_rep_ids": met_result.idle_kicked_rep_ids,
                    "watchdog_respawned": met_result.watchdog_respawned,
                },
                "merge": {"checked": merge_result.checked, "merged": merge_result.merged, "conflicts": merge_result.conflicts},
                "sessions": {"active": active_sessions, "completed": completed_sessions, "failed": failed_sessions},
                "reps": rep_counts, "stalled_reps": stalled_reps, "is_stalled": len(stalled_reps) > 0,
                "liveness": liveness,
            })

        return {
            "timestamp": _dt.now(_tz.utc).isoformat(),
            "total_corps": len(active_corps),
            "corps": corps_results,
            "summary": {
                "total_active_sessions": sum(r["sessions"]["active"] for r in corps_results),
                "total_stalled_corps": sum(1 for r in corps_results if r["is_stalled"]),
                "total_reclaimed": sum(r["metronome"]["reclaimed"] for r in corps_results),
                "total_idle_kicked": sum(r["metronome"]["idle_kicked"] for r in corps_results),
            },
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Segments & Reps (create/transition — ported from legacy)
# ---------------------------------------------------------------------------

class SegmentCreateRequest(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    caption: Optional[str] = None


class RepCreateRequest(BaseModel):
    segment_id: str


class RepTransitionRequest(BaseModel):
    new_status: str
    assigned_to: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None


@router.post("/segments")
def v1_create_segment(data: SegmentCreateRequest):
    from backend.models.segment import SegmentType
    from backend.services.segment_service import create_segment, InvalidSegmentStructure
    db = _get_db_session()
    try:
        coord = create_segment(
            db, type=SegmentType(data.type), title=data.title,
            description=data.description, parent_id=data.parent_id, caption=data.caption,
        )
        return {"id": coord.id, "type": coord.type.value, "title": coord.title, "status": coord.status.value}
    except (ValueError, InvalidSegmentStructure) as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.post("/reps")
def v1_create_rep(data: RepCreateRequest):
    from backend.services.rep_service import create_rep
    db = _get_db_session()
    try:
        rep = create_rep(db, segment_id=data.segment_id)
        return {"id": rep.id, "status": rep.status.value, "segment_id": rep.segment_id}
    finally:
        db.close()


@router.post("/reps/{rep_id}/transition")
def v1_transition_rep(rep_id: str, data: RepTransitionRequest):
    from backend.models.rep import RepStatus
    from backend.services.rep_service import transition_rep, InvalidRepTransition
    db = _get_db_session()
    try:
        rep = transition_rep(
            db, rep_id=rep_id, new_status=RepStatus(data.new_status),
            assigned_to=data.assigned_to, result=data.result, error=data.error,
        )
        return {"id": rep.id, "status": rep.status.value}
    except (ValueError, InvalidRepTransition) as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Scoring (ported from legacy)
# ---------------------------------------------------------------------------

class ScoreCreateRequest(BaseModel):
    judge_type: str
    value: float
    box: int
    rep_id: Optional[str] = None
    segment_id: Optional[str] = None
    feedback: Optional[str] = None


@router.post("/scores")
def v1_create_score(data: ScoreCreateRequest):
    from backend.models.score import JudgeType
    from backend.services.scoring_service import record_score, InvalidScore
    db = _get_db_session()
    try:
        score = record_score(
            db, corps_id="default", judge_type=JudgeType(data.judge_type),
            value=data.value, box=data.box, rep_id=data.rep_id,
            segment_id=data.segment_id, feedback=data.feedback,
        )
        return {"id": score.id, "value": score.value, "box": score.box}
    except (ValueError, InvalidScore) as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.get("/reps/{rep_id}/scores")
def v1_get_scores_for_rep(rep_id: str):
    from backend.services.scoring_service import get_scores_for_rep
    db = _get_db_session()
    try:
        scores = get_scores_for_rep(db, rep_id)
        return [{"id": s.id, "judge_type": s.judge_type.value, "value": s.value,
                 "box": s.box, "feedback": s.feedback} for s in scores]
    finally:
        db.close()


@router.get("/reps/{rep_id}/composite")
def v1_get_composite(rep_id: str):
    from backend.services.scoring_service import compute_composite
    db = _get_db_session()
    try:
        result = compute_composite(db, corps_id="default", rep_id=rep_id)
        return {
            "raw_total": result.raw_total,
            "penalties_total": result.penalties_total,
            "final_score": result.final_score,
            "needs_rework": result.needs_rework,
            "needs_escalation": result.needs_escalation,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Corps Mode Switch (ported — separate from PUT /corps/{id}/mode above)
# ---------------------------------------------------------------------------

class CorpsModeSwitchRequest(BaseModel):
    mode: str


@router.post("/corps/{corps_id}/mode")
async def v1_switch_corps_mode(corps_id: str, data: CorpsModeSwitchRequest):
    """Switch a corps to a new operational mode."""
    from backend.models.corps import CorpsMode
    from backend.services.mode_manager import switch_mode, ModeError
    from backend.api.app import manager

    db = _get_db_session()
    try:
        new_mode = CorpsMode(data.mode)
        corps = switch_mode(db, corps_id, new_mode)
        await manager.broadcast(corps_id, {
            "type": "mode_switch", "corps_id": corps_id, "mode": new_mode.value,
        })
        return {"id": corps.id, "mode": corps.mode.value}
    except ValueError:
        raise HTTPException(400, f"Invalid mode: {data.mode}")
    except ModeError as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Theme API (ported from legacy)
# ---------------------------------------------------------------------------

@router.get("/theme")
def v1_get_theme():
    from backend.config.theme import get_theme
    theme = get_theme()
    return {
        "name": theme.name, "display_name": theme.display_name,
        "org_unit": theme.org_unit, "org_unit_plural": theme.org_unit_plural,
        "project": theme.project, "project_plural": theme.project_plural,
        "work_levels": theme.work_levels, "work_item": theme.work_item,
        "work_item_plural": theme.work_item_plural,
        "execution_modes": theme.execution_modes, "admin_name": theme.admin_name,
        "color_palette": theme.color_palette,
        "commands": {
            k: {"label": v.label, "description": v.description, "category": v.category}
            for k, v in theme.commands.items()
        },
    }


@router.get("/themes")
def v1_list_themes():
    from backend.config.theme import list_themes
    return list_themes()


# ---------------------------------------------------------------------------
# Self-Improvement (ported from legacy)
# ---------------------------------------------------------------------------

class SelfImprovementProposalRequest(BaseModel):
    definition_id: str
    changes: dict
    reason: str


class ImprovementActionRequest(BaseModel):
    approver_session_id: str


@router.post("/self-improvement/propose")
def v1_propose_improvement(data: SelfImprovementProposalRequest):
    from backend.services.lifecycle_manager import propose_self_improvement
    db = _get_db_session()
    try:
        log = propose_self_improvement(db, data.definition_id, data.changes, data.reason)
        return {"id": log.id, "status": log.status.value}
    finally:
        db.close()


@router.post("/self-improvement/{proposal_id}/approve")
def v1_approve_improvement(proposal_id: str, data: ImprovementActionRequest):
    from backend.services.lifecycle_manager import approve_self_improvement
    db = _get_db_session()
    try:
        defn = approve_self_improvement(db, proposal_id, data.approver_session_id)
        return {"id": defn.id, "role": defn.role, "version": defn.version}
    finally:
        db.close()


@router.post("/self-improvement/{proposal_id}/reject")
def v1_reject_improvement(proposal_id: str, data: ImprovementActionRequest):
    from backend.services.lifecycle_manager import reject_self_improvement
    db = _get_db_session()
    try:
        log = reject_self_improvement(db, proposal_id, data.approver_session_id)
        return {"id": log.id, "status": log.status.value}
    finally:
        db.close()


@router.get("/self-improvement/pending")
def v1_pending_improvements():
    from backend.models.self_improvement_log import SelfImprovementLog, ImprovementStatus
    from backend.models.agent_definition import AgentDefinition
    db = _get_db_session()
    try:
        logs = db.query(SelfImprovementLog).filter(
            SelfImprovementLog.status == ImprovementStatus.PENDING
        ).all()
        result = []
        for log in logs:
            defn = db.get(AgentDefinition, log.agent_definition_id)
            result.append({
                "id": log.id,
                "role": defn.role if defn else "unknown",
                "nickname": defn.nickname if defn else None,
                "old_version": log.old_version,
                "new_version": log.new_version,
                "changes": log.changes,
                "reason": log.reason,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })
        return result
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Memory endpoints (ported from legacy)
# ---------------------------------------------------------------------------

class MemoryUpdateRequest(BaseModel):
    content: str


@router.get("/agents/{agent_identity}/memories")
def v1_get_memories(agent_identity: str, memory_type: Optional[str] = None):
    from backend.services.memory_manager import MemoryManager
    db = _get_db_session()
    try:
        mgr = MemoryManager(db)
        memories = mgr.get_memories(agent_identity, memory_type=memory_type)
        return [
            {"id": m.id, "memory_type": m.memory_type, "title": m.title,
             "content": m.content, "confidence": m.confidence, "version": m.version,
             "created_at": m.created_at.isoformat() if m.created_at else None}
            for m in memories
        ]
    finally:
        db.close()


@router.get("/agents/{agent_identity}/memory-stats")
def v1_memory_stats(agent_identity: str):
    from backend.services.memory_manager import MemoryManager
    db = _get_db_session()
    try:
        mgr = MemoryManager(db)
        return mgr.get_memory_stats(agent_identity)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Communication: Messages (ported from legacy)
# ---------------------------------------------------------------------------

class MessageCreateV1Request(BaseModel):
    from_role: str
    type: str
    subject: str
    body: Optional[str] = None
    to_role: Optional[str] = None
    priority: str = "normal"
    segment_id: Optional[str] = None


@router.post("/corps/{corps_id}/messages")
def v1_send_message(corps_id: str, data: MessageCreateV1Request):
    from backend.models.message import MessageType, MessagePriority
    from backend.services.message_service import send_message, InvalidMessagePath, InvalidMessageType
    db = _get_db_session()
    try:
        msg = send_message(
            db, corps_id=corps_id, from_role=data.from_role,
            type=MessageType(data.type), subject=data.subject, body=data.body,
            to_role=data.to_role, priority=MessagePriority(data.priority),
            segment_id=data.segment_id,
        )
        return {"id": msg.id, "type": msg.type.value, "subject": msg.subject}
    except (ValueError, InvalidMessagePath, InvalidMessageType) as e:
        raise HTTPException(400, str(e))
    finally:
        db.close()
