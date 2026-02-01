"""V1 API router — thin adapters over existing service modules.

All business logic lives in backend/services/. These routes only translate
HTTP ↔ service calls and enforce slug/id validation.
"""

import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
        raise HTTPException(400, f"Invalid {label}")
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$", value):
        raise HTTPException(400, f"Invalid {label}")


# =========================================================================
# CORPS
# =========================================================================

def _get_db_session():
    """Get a SQLAlchemy session for DB fallback queries."""
    from backend.api.app import SessionFactory
    return SessionFactory()


@router.get("/corps")
def v1_list_corps():
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
                })
            except Exception:
                continue

    # DB corps (merge, dedup by display_name)
    try:
        from backend.models.corps import Corps, CorpsStatus
        db = _get_db_session()
        try:
            db_corps = db.query(Corps).filter(
                Corps.status != CorpsStatus.DISBANDED
            ).all()
            for c in db_corps:
                if c.name not in seen_names:
                    seen_names.add(c.name)
                    result.append({
                        "corps_id": c.id,
                        "display_name": c.name,
                        "philosophy": "",
                        "state": c.status.value if c.status else "unknown",
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
        "You are the Music Arranger for this show. You specialize in brass arrangements, "
        "percussion writing, and musical pacing. Contribute specific musical ideas — key changes, "
        "tempo progressions, instrument voicings, scoring decisions. Be concrete."
    ),
    "drill_writer": (
        "You are the Drill Designer for this show. You specialize in visual design, "
        "formations, transitions, and staging. Contribute specific visual ideas — formations, "
        "movement patterns, staging concepts, spatial relationships. Be concrete."
    ),
    "choreographer": (
        "You are the Guard Choreographer for this show. You specialize in color guard "
        "choreography, equipment work, and dance. Contribute specific guard ideas — equipment "
        "choices, choreographic moments, tosses, visual impact points. Be concrete."
    ),
    "program_coordinator": (
        "You are the Program Coordinator (lead designer) for this show. You run the design room "
        "meeting. Your job is to FACILITATE discussion, not just respond. You should:\n"
        "- Ask the user direct questions to draw out their vision\n"
        "- Identify which areas need input from specialists (music, drill, guard)\n"
        "- Synthesize ideas from the team into coherent design direction\n"
        "- Challenge vague ideas — push for specifics\n"
        "- Track what's been decided vs. what's still open\n"
        "- When enough decisions are made, suggest updating the spec"
    ),
}

_DESIGN_ROLE_DISPLAY = {
    "music_writer": "Music Arranger",
    "drill_writer": "Drill Designer",
    "choreographer": "Guard Choreographer",
    "program_coordinator": "Program Coordinator",
}

_DESIGN_SYSTEM_TEMPLATE = """You are a DCI show design staff member in a live Design Room meeting.
You are having a real-time collaborative discussion with the show's director (the user) and other design staff.

YOUR ROLE: {role_prompt}

SHOW: {slug}

CURRENT SPEC (what's been decided so far):
{spec_content}

CONVERSATION SO FAR:
{notes_content}

REQUIRED SPEC SECTIONS (the spec needs all of these before it can be published):
- ## Show Concept
- ## Musical Design
- ## Visual Design
- ## Guard Design
- ## General Effect
- ## Deliverables
- ## Evaluation Rubric

INSTRUCTIONS:
- Respond as your character in 2-5 sentences. Be specific and creative.
- This is a LIVE DISCUSSION. Talk naturally — react to what was just said, build on ideas, push back respectfully.
- If you need more information from the director, ask a SPECIFIC question (not generic).
- When you have a design idea, pitch it with enthusiasm and detail.
- If something another agent said concerns you, say so and explain why.
- Do NOT just acknowledge or summarize. Contribute substantive creative ideas.
- Keep driving toward a complete, publishable spec.
"""

_PC_MARSHAL_TEMPLATE = """You are the Program Coordinator running a Design Room meeting for show "{slug}".

CURRENT SPEC:
{spec_content}

CONVERSATION SO FAR:
{notes_content}

REQUIRED SPEC SECTIONS:
- ## Show Concept
- ## Musical Design
- ## Visual Design
- ## Guard Design
- ## General Effect
- ## Deliverables
- ## Evaluation Rubric

The director (user) just said: "{user_message}"

Based on the message content and what's been discussed, identify which design staff should weigh in.
Your job is to:
1. React to the director's message — acknowledge their input, ask a follow-up question to sharpen the idea
2. If specific expertise areas are relevant, call on those specialists by name
3. Track progress: note what sections of the spec are covered vs still open
4. Keep the energy up — this is a creative collaboration

Respond in 2-4 sentences as the Program Coordinator. Be direct and engaged.
If calling on a specialist, say something like "Let me get [Music Arranger/Drill Designer/Guard Choreographer]'s take on this."
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
        results.append({
            "season_id": season_id,
            "dir_name": season_dir.name,
            "metadata": data.get("metadata", {}),
        })
    return results


class CreateSeasonRequest(BaseModel):
    season_id: str
    metadata: Optional[dict] = None


@router.post("/seasons")
def v1_create_season(req: CreateSeasonRequest):
    """Create a new season workspace."""
    _validate_id(req.season_id, "season_id")
    root = _get_root()
    from backend.services.season_persistence import create_season
    try:
        season_dir = create_season(root, req.season_id, req.metadata)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {
        "season_id": req.season_id,
        "dir_name": season_dir.name,
        "metadata": req.metadata or {},
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
                if not db.get(Corps, req.corps_id):
                    raise HTTPException(404, f"Corps '{req.corps_id}' not found")
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

    composites = {}
    for cid in corps_ids:
        caption_scores = _stub_caption_scores(cid, show_slug)
        raw_total = sum(caption_scores[jt] * DEFAULT_WEIGHTS[jt] for jt in caption_scores)
        composites[cid] = CompositeScore(
            caption_scores=caption_scores,
            raw_total=raw_total,
            penalties_total=0.0,
            final_score=raw_total,
            needs_rework=False,
            needs_escalation=False,
        )

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

    return {
        "competition_id": competition_id,
        "status": "completed",
        "standings": standings_data["results"],
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


def _stub_caption_scores(corps_id: str, show_slug: str) -> dict:
    """Deterministic scores per caption, seeded from corps_id + show_slug."""
    from backend.models.score import JudgeType
    scores = {}
    for jtype in [JudgeType.BRASS, JudgeType.PERCUSSION, JudgeType.GUARD,
                  JudgeType.VISUAL, JudgeType.GENERAL_EFFECT]:
        seed = hashlib.sha256(f"{corps_id}:{show_slug}:{jtype.value}".encode()).hexdigest()
        scores[jtype] = (int(seed[:8], 16) % 30) + 60
    return scores
