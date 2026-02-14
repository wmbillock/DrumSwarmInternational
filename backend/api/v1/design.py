"""V1 API — Design Room routes.

Extracted from the monolithic router.py. All business logic lives in
backend/services/; these routes only translate HTTP ↔ service calls.
"""

import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _shows_dir, _show_dir, _get_llm_client, _llm_chat
from backend.api.v1.schemas import CreateThreadRequest, PostMessageRequest, UpdateSpecRequest
from backend.services.yaml_util import safe_load_yaml_dict

router = APIRouter(prefix="/api/v1")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DESIGN_ROLE_PROMPTS = {
    "music_writer": (
        "You are the Music Arranger. You think in keys, tempos, and brass books. "
        "Pitch specific musical ideas. 30 words max."
    ),
    "drill_writer": (
        "You are the Drill Designer. You think in formations and spatial flow. "
        "Pitch specific visual ideas. 30 words max."
    ),
    "choreographer": (
        "You are the Guard Choreographer. You think in silk, sabre, and movement. "
        "Pitch specific guard ideas. 30 words max."
    ),
    "program_coordinator": (
        "You are the Program Coordinator. You track what's decided vs. foggy "
        "and push for details agents need. 30 words max."
    ),
}

_DESIGN_ROLE_DISPLAY = {
    "music_writer": "Music Arranger",
    "drill_writer": "Drill Designer",
    "choreographer": "Guard Choreographer",
    "program_coordinator": "Program Coordinator",
}

_DESIGN_SYSTEM_TEMPLATE = """You're on the design staff for show "{slug}".

{role_prompt}

Brief so far:
{spec_content}

{role_context}

RULES — follow these exactly:
- MAX 30 WORDS. No exceptions. One or two short sentences.
- The Brief and Prompt tabs update automatically — never mention saving or writing files.
- Pitch a specific idea or ask one pointed question. That's it.
- Never recap. Never narrate. Let the Brief document tell the story.
"""

_PC_MARSHAL_TEMPLATE = """You're the Program Coordinator for "{slug}".

Brief so far:
{spec_content}

Recent conversation:
{notes_content}

Director just said: "{user_message}"

{specialist_context}

RULES — follow these exactly:
- MAX 30 WORDS total. No exceptions.
- The Brief and Prompt tabs auto-update after each exchange. Never mention saving files.
- Pick ONE move: confirm a decision, ask one question, or flag what's missing.
- If specialists contributed input above, weave their key points into your response — don't repeat them separately.
- Never recap what the director said.
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
- ## Swarm Prompt: synthesize decided sections into an actionable prompt for the agent swarm.
  The Swarm Prompt is a SEPARATE document from the Brief — it must use action-oriented sections:
  ## Objective (what are we building), ## Deliverables (bullet list of outputs),
  ## Constraints (limits and rules), ## Acceptance Criteria (how to verify).
  Do NOT repeat Brief sections like Show Concept/Musical Design in the Swarm Prompt.
- Output ONLY the spec markdown, no preamble
"""


_PC_GREETING_TEMPLATE = """You're the Program Coordinator for show "{slug}".
The director just entered the Design Room. Greet them in MAX 30 WORDS.
Mention the show name and ask one question to get started. Be direct and collegial."""


def _get_role_context(notes_path, role: str, limit: int = 10) -> str:
    """Parse design_notes.md for messages relevant to this role.

    Returns the last *limit* messages from: this role, program_coordinator, and user.
    Excludes other specialists so each role sees only its own thread.
    """
    if not notes_path.exists():
        return ""
    content = notes_path.read_text(encoding="utf-8", errors="replace")
    allowed_roles = {role, "program_coordinator", "user"}
    relevant: list[str] = []
    lines = content.split("\n")
    for line in lines:
        line_stripped = line.strip()
        m = re.match(r"\*\*\[(\w+)\]\*\*\s*(.*)", line_stripped)
        if m:
            msg_role = m.group(1)
            msg_text = m.group(2)
            if msg_role in allowed_roles:
                relevant.append(f"[{msg_role}] {msg_text}")
    if not relevant:
        return ""
    recent = relevant[-limit:]
    return "Your recent conversation thread:\n" + "\n".join(recent)


def _extract_swarm_prompt(show_dir, spec_text: str):
    """Extract the ## Swarm Prompt section from a spec and write it to show_prompt.md.

    Since the swarm prompt lives under ## Swarm Prompt in the spec, the LLM
    writes its sub-sections as ### (one level deeper). We promote all headings
    by one level so the standalone show_prompt.md uses ## as expected by the linter.
    """
    import re as _re
    m = _re.search(r"^## Swarm Prompt\s*\n(.*?)(?=\n## |\Z)", spec_text, _re.DOTALL | _re.MULTILINE)
    if m:
        prompt_text = m.group(1).strip()
        if prompt_text and "TBD" not in prompt_text and "awaiting" not in prompt_text.lower():
            # Promote heading levels: ### → ##, #### → ###, etc.
            prompt_text = _re.sub(r"^###(#*\s)", r"##\1", prompt_text, flags=_re.MULTILINE)
            from backend.services.yaml_util import atomic_write
            atomic_write(show_dir / "show_prompt.md", prompt_text)


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
        f"# {req.title}\n\n## Decisions\n\n_No decisions yet._\n\n"
        f"## Open Questions\n\n_No open questions._\n\n"
        f"## Constraints\n\n_No constraints defined._\n"
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
        status = safe_load_yaml_dict(status_path.read_text(encoding="utf-8"))
        summary = status.get("summary", "")
        if not summary:
            spec_path = d / "spec.md"
            if spec_path.exists():
                for line in spec_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("# ") and not line.startswith("---"):
                        summary = line[2:].strip()
                        break
        threads.append({
            "slug": d.name,
            "status": status.get("status", "unknown"),
            "has_spec": (d / "spec.md").exists(),
            "summary": summary,
        })
    return threads


@router.get("/design/threads/{slug}/messages")
def v1_get_thread_messages(slug: str):
    """Get design notes for a thread (parsed as messages)."""
    show_dir = _show_dir(slug)
    notes_path = show_dir / "design_notes.md"
    if not notes_path.exists():
        return {"slug": slug, "messages": []}
    content = notes_path.read_text(encoding="utf-8", errors="replace")
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
    with open(notes_path, "a", encoding="utf-8") as f:
        f.write(tag_comment + entry)

    # Build context
    spec_content = read_spec(show_dir) or "(no spec yet)"
    notes_content = notes_path.read_text(encoding="utf-8", errors="replace") if notes_path.exists() else "(no notes yet)"
    if len(notes_content) > 4000:
        notes_content = "...\n" + notes_content[-4000:]

    responses: list[dict] = []
    llm_client = _get_llm_client()

    if llm_client:
        # 1. Specialists contribute first if their domain was tagged
        specialist_inputs: list[str] = []
        for spec_role in sorted(specialist_roles):
            role_prompt = _DESIGN_ROLE_PROMPTS[spec_role]
            role_context = _get_role_context(notes_path, spec_role)
            system_prompt = _DESIGN_SYSTEM_TEMPLATE.format(
                role_prompt=role_prompt,
                slug=slug,
                spec_content=spec_content[:2000],
                role_context=role_context,
            )
            spec_text = _llm_chat(llm_client, system_prompt, req.message)
            if spec_text:
                spec_entry = f"\n<!-- tags: {', '.join(tags)} -->\n**[{spec_role}]** {spec_text}\n"
                with open(notes_path, "a", encoding="utf-8") as f:
                    f.write(spec_entry)
                responses.append({
                    "role": spec_role,
                    "display_name": _DESIGN_ROLE_DISPLAY.get(spec_role, spec_role),
                    "tags": tags,
                    "response": spec_text,
                })
                specialist_inputs.append(f"{_DESIGN_ROLE_DISPLAY.get(spec_role, spec_role)}: {spec_text}")

        # 2. PC marshals — sees specialist input and gives one coordinating response
        specialist_ctx = ""
        if specialist_inputs:
            specialist_ctx = "Specialist input:\n" + "\n".join(specialist_inputs)

        # Re-read notes after specialist writes
        notes_content = notes_path.read_text(encoding="utf-8", errors="replace") if notes_path.exists() else "(no notes yet)"
        if len(notes_content) > 4000:
            notes_content = "...\n" + notes_content[-4000:]

        pc_prompt = _PC_MARSHAL_TEMPLATE.format(
            slug=slug,
            spec_content=spec_content[:2000],
            notes_content=notes_content,
            user_message=req.message,
            specialist_context=specialist_ctx,
        )
        pc_text = _llm_chat(llm_client, pc_prompt, req.message)
        if pc_text:
            pc_entry = f"\n<!-- tags: {', '.join(tags)} -->\n**[program_coordinator]** {pc_text}\n"
            with open(notes_path, "a", encoding="utf-8") as f:
                f.write(pc_entry)
            responses.append({
                "role": "program_coordinator",
                "display_name": _DESIGN_ROLE_DISPLAY["program_coordinator"],
                "tags": tags,
                "response": pc_text,
            })

    # Fallback if no LLM responses were generated
    if not responses:
        fallback_text = (
            f"I hear you on that. Let me think about how this fits into the overall design. "
            f"(LLM unavailable — connect an LLM backend for full collaborative design sessions.)"
        )
        fb_entry = f"\n<!-- tags: {', '.join(tags)} -->\n**[program_coordinator]** {fallback_text}\n"
        with open(notes_path, "a", encoding="utf-8") as f:
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
            notes_for_spec = notes_path.read_text(encoding="utf-8", errors="replace") if notes_path.exists() else ""
            if len(notes_for_spec) > 5000:
                notes_for_spec = "...\n" + notes_for_spec[-5000:]
            spec_prompt = _SPEC_UPDATE_TEMPLATE.format(
                spec_content=spec_content,
                notes_content=notes_for_spec,
            )
            updated_spec = _llm_chat(llm_client, spec_prompt, "Update the spec now.")
            if updated_spec and len(updated_spec) > 50:
                write_spec(show_dir, updated_spec)
                # Auto-extract ## Swarm Prompt into show_prompt.md
                _extract_swarm_prompt(show_dir, updated_spec)
        except Exception:
            pass  # Spec update is best-effort

    # Auto-lint: run both linters and report issues as a judge message
    try:
        from backend.services.brief_linter import lint_brief
        from backend.services.prompt_linter import lint_prompt
        from backend.services.show_persistence import read_spec as _read_spec, missing_show_files

        brief_content = _read_spec(show_dir) or ""
        prompt_path = show_dir / "show_prompt.md"
        prompt_content = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

        brief_report = lint_brief(brief_content)
        prompt_report = lint_prompt(prompt_content)
        missing_files = missing_show_files(show_dir)

        issues: list[str] = []
        for f in brief_report.required_fix:
            issues.append(f"Brief — {f.section}: {f.message}")
        for f in prompt_report.required_fix:
            issues.append(f"Prompt — {f.section}: {f.message}")
        for name in missing_files:
            issues.append(f"Show Files — Missing required file: {name}")

        if issues:
            judge_text = "Open issues: " + "; ".join(issues[:5])
            if len(issues) > 5:
                judge_text += f" (+{len(issues) - 5} more)"
            judge_entry = f"\n<!-- tags: admin -->\n**[judge]** {judge_text}\n"
            with open(notes_path, "a", encoding="utf-8") as f:
                f.write(judge_entry)
            responses.append({
                "role": "judge",
                "display_name": "Judge",
                "tags": ["admin"],
                "response": judge_text,
            })
    except Exception:
        pass  # Lint is best-effort

    # Return backward-compatible single response + full responses array
    return {
        "role": responses[0]["role"],
        "tags": tags,
        "response": responses[0]["response"],
        "responses": responses,
    }


@router.post("/design/threads/{slug}/greet")
def v1_greet_thread(slug: str):
    """Generate a PC greeting when the director first enters the Design Room."""
    show_dir = _show_dir(slug)
    from backend.services.show_persistence import read_spec
    spec_content = read_spec(show_dir) or "(blank spec)"
    llm_client = _get_llm_client()
    if not llm_client:
        return {
            "role": "program_coordinator",
            "display_name": "Program Coordinator",
            "response": f"Welcome to the Design Room for \"{slug}\". I'm your Program Coordinator — tell me your vision and we'll build the Brief together.",
        }
    prompt = _PC_GREETING_TEMPLATE.format(slug=slug) + f"\n\nCurrent Brief:\n{spec_content[:2000]}"
    text = _llm_chat(llm_client, prompt, "Greet the director.")
    if not text:
        text = f"Welcome to the Design Room for \"{slug}\". I'm your Program Coordinator — tell me your vision and we'll build the Brief together."
    # Persist greeting to design notes
    notes_path = show_dir / "design_notes.md"
    entry = f"\n<!-- tags: admin -->\n**[program_coordinator]** {text}\n"
    with open(notes_path, "a", encoding="utf-8") as f:
        f.write(entry)
    return {
        "role": "program_coordinator",
        "display_name": "Program Coordinator",
        "response": text,
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
    content = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
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
    content = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    from backend.services.prompt_linter import lint_prompt
    report = lint_prompt(content)
    return {
        "required_fix": [{"section": f.section, "message": f.message} for f in report.required_fix],
        "nice_to_have": [{"section": f.section, "message": f.message} for f in report.nice_to_have],
        "acceptable_risk": [{"section": f.section, "message": f.message} for f in report.acceptable_risk],
    }


@router.post("/design/threads/{slug}/lint-brief")
def v1_lint_brief(slug: str):
    """Run brief linter on current spec.md."""
    show_dir = _show_dir(slug)
    from backend.services.show_persistence import read_spec
    from backend.services.brief_linter import lint_brief
    content = read_spec(show_dir) or ""
    report = lint_brief(content)
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
    content = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
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
