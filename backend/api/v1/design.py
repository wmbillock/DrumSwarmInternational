"""V1 API — Design Room routes.

Extracted from the monolithic router.py. All business logic lives in
backend/services/; these routes only translate HTTP ↔ service calls.
"""

import re
from datetime import datetime, timezone
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _shows_dir, _show_dir, _get_llm_client, _llm_chat
from backend.api.v1.schemas import CreateThreadRequest, PostMessageRequest, UpdateSpecRequest

router = APIRouter(prefix="/api/v1")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


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
