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
        "You are the Systems Architect. "
        "Your domain: backend, APIs, data models, service layers, database schemas, data flow. "
        "You think about how things connect under the hood. "
        "Always propose concrete: name the models, sketch the endpoints, specify the data types. "
        "Push back on vague requirements — demand specifics you can build against."
    ),
    "drill_writer": (
        "You are the UX Designer. "
        "Your domain: frontend pages, components, user journeys, interactions, state management. "
        "You think about what the user sees and does. "
        "Always propose concrete: name the components, describe the layout, specify the user flow. "
        "Challenge the team when the UX is unclear or the interaction model is confusing."
    ),
    "choreographer": (
        "You are the QA Specialist. "
        "Your domain: testing strategy, edge cases, error handling, integration points, failure modes. "
        "You think about what can go wrong. "
        "Always raise concrete risks: name the edge case, describe the failure scenario, suggest the test. "
        "Push the team to define acceptance criteria before building."
    ),
    "program_coordinator": (
        "You are the Program Coordinator. You track what's decided vs. still open "
        "and push for specifics the agent swarm needs to execute. "
        "Your job is to synthesize and drive — never let the conversation stall."
    ),
}

# Specialists (excludes PC — used for engagement logic)
_SPECIALIST_ROLES = {"music_writer", "drill_writer", "choreographer"}

_DESIGN_ROLE_DISPLAY = {
    "music_writer": "Systems Architect",
    "drill_writer": "UX Designer",
    "choreographer": "QA Specialist",
    "program_coordinator": "Program Coordinator",
}

_DESIGN_SYSTEM_TEMPLATE = """You're on the design staff for show "{slug}".
A "show" is a software feature or task to be implemented by an agent swarm.

{role_prompt}

Brief so far:
{spec_content}

{exchange_context}

{role_context}

RULES — follow these exactly:
- MAX 60 WORDS. Two or three punchy sentences.
- Be specific: name components, endpoints, test cases, pages — never speak in generalities.
- If another specialist proposed something, react to it: agree and extend, or challenge with a concrete alternative.
- End with a sharp question to keep design moving forward.
- Never recap what was said. Never narrate. Never mention saving files (the Brief auto-updates).
"""

_PC_MARSHAL_TEMPLATE = """You're the Program Coordinator for "{slug}".
A "show" in this system is a software feature or task to be implemented by an agent swarm.

Brief so far:
{spec_content}

Recent conversation:
{notes_content}

Director just said: "{user_message}"

{specialist_context}

RULES — follow these exactly:
- MAX 60 WORDS total.
- The Brief and Prompt tabs auto-update after each exchange. Never mention saving files.
- Synthesize the specialist proposals. Name specific decisions to lock in.
- End with a sharp follow-up question directed at a specific specialist by name.
- Drive forward — the design should feel like it's moving, not stalling.
- Never recap what the director said. Never be vague. Be concrete.
"""

_PC_FOLLOWUP_TEMPLATE = """You're the Program Coordinator for "{slug}".

Brief so far:
{spec_content}

This exchange so far:
{exchange_context}

{gap_hint}

RULES — follow these exactly:
- MAX 50 WORDS total.
- Synthesize the round. Lock in decisions with "Decision:" prefix.
- Identify the single most important open question and pose it.
- If the design feels solid for this topic, say "Ready to move on" and suggest the next topic.
- Never recap. Keep momentum.
"""

_SPEC_UPDATE_TEMPLATE = """Update the show spec (Brief) based on the design conversation.
A "show" is a software feature or task. The spec describes what to build.

CURRENT SPEC:
{spec_content}

RECENT CONVERSATION:
{notes_content}

MANDATORY SECTIONS (every spec must have these):
- ## Show Concept (what is this feature/task and why)
- ## Architecture (backend design: models, services, APIs, data flow)
- ## Interface Design (frontend: pages, components, UX flow)
- ## Quality Plan (testing strategy, edge cases, integration points)
- ## General Effect (user-facing impact, how this improves the system)
- ## Constraints (technical limits, dependencies, compatibility)
- ## Deliverables (specific files, endpoints, components to create/modify)
- ## Swarm Prompt

Write the COMPLETE updated spec in markdown. Do NOT wrap output in code fences.
- Keep existing content that's still valid
- Incorporate ALL design decisions from the conversation — be thorough
- If a section hasn't been discussed yet, write "Awaiting design input" (just those three words)
- ## Swarm Prompt: synthesize decided sections into an actionable prompt for the agent swarm.
  The Swarm Prompt is action-oriented with these sub-sections (use ### inside ## Swarm Prompt):
  ### Objective (what are we building), ### Deliverables (bullet list of outputs),
  ### Constraints (limits and rules), ### Acceptance Criteria (how to verify).
- Output ONLY the spec markdown — no preamble, no code fences, no commentary
"""


_PC_GREETING_TEMPLATE = """You're the Program Coordinator for show "{slug}".
A "show" is a software feature or task to design. The director just entered the Design Room.
Greet them in MAX 40 WORDS. Mention the show name and ask one question to get the design started.
The whole design team is here — Systems Architect, UX Designer, QA Specialist — ready to collaborate."""

_PC_CONTINUE_TEMPLATE = """You're the Program Coordinator for "{slug}".
A "show" is a software feature or task. The director wants us to keep designing.

Brief so far:
{spec_content}

Recent conversation:
{notes_content}

Open lint issues:
{lint_summary}

RULES — follow these exactly:
- MAX 60 WORDS total.
- Review the Brief and conversation. Identify the MOST IMPORTANT gap or open question.
- Frame it as a specific, actionable question directed at one or two specialists by name.
- If the brief has TBD/awaiting sections, prioritize filling those.
- If the brief is mostly complete, push toward finalizing details or resolving conflicts.
- Be concrete. "Systems Architect, what's the data model for X?" not "Let's think about architecture."
"""


def _get_last_judge_message(notes_path) -> str | None:
    """Extract the last judge message from design_notes.md, or None if none exist."""
    if not notes_path.exists():
        return None
    content = notes_path.read_text(encoding="utf-8", errors="replace")
    last = None
    for line in content.splitlines():
        m = re.match(r"\*\*\[judge\]\*\*\s*(.*)", line.strip())
        if m:
            last = m.group(1)
    return last


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences that LLMs sometimes wrap output in."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Remove opening fence (```markdown, ```md, or just ```)
        first_newline = stripped.index("\n") if "\n" in stripped else len(stripped)
        stripped = stripped[first_newline + 1:]
    if stripped.rstrip().endswith("```"):
        stripped = stripped.rstrip()[:-3].rstrip()
    return stripped


def _get_role_context(notes_path, role: str, limit: int = 10) -> str:
    """Parse design_notes.md for messages relevant to this role.

    Returns the last *limit* messages from all roles so specialists can
    see what each other said and build on it (cross-pollination).
    """
    if not notes_path.exists():
        return ""
    content = notes_path.read_text(encoding="utf-8", errors="replace")
    relevant: list[str] = []
    lines = content.split("\n")
    for line in lines:
        line_stripped = line.strip()
        m = re.match(r"\*\*\[(\w+)\]\*\*\s*(.*)", line_stripped)
        if m:
            msg_role = m.group(1)
            msg_text = m.group(2)
            # Skip judge messages — they're lint output, not conversation
            if msg_role != "judge":
                relevant.append(f"[{msg_role}] {msg_text}")
    if not relevant:
        return ""
    recent = relevant[-limit:]
    return "Recent design room conversation:\n" + "\n".join(recent)


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
        # Use filesystem timestamps for created/updated
        created_at = datetime.fromtimestamp(d.stat().st_ctime, tz=timezone.utc).isoformat()
        updated_at = datetime.fromtimestamp(status_path.stat().st_mtime, tz=timezone.utc).isoformat()
        threads.append({
            "slug": d.name,
            "status": status.get("status", "unknown"),
            "has_spec": (d / "spec.md").exists(),
            "summary": summary,
            "created_at": created_at,
            "updated_at": updated_at,
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
                    role = m.group(1)
                    messages.append({
                        "role": role,
                        "display_name": _DESIGN_ROLE_DISPLAY.get(role, role),
                        "content": m.group(2),
                        "tags": tags,
                    })
        i += 1
    return {"slug": slug, "messages": messages}


def _invoke_specialist(llm_client, slug: str, spec_role: str, notes_path,
                       spec_content: str, exchange_context: str, prompt_text: str,
                       tags: list[str]) -> dict | None:
    """Call a single specialist and persist their response. Returns response dict or None."""
    role_prompt = _DESIGN_ROLE_PROMPTS[spec_role]
    role_context = _get_role_context(notes_path, spec_role)
    system_prompt = _DESIGN_SYSTEM_TEMPLATE.format(
        role_prompt=role_prompt,
        slug=slug,
        spec_content=spec_content[:2000],
        exchange_context=exchange_context,
        role_context=role_context,
    )
    text = _llm_chat(llm_client, system_prompt, prompt_text)
    if text:
        entry = f"\n<!-- tags: {', '.join(tags)} -->\n**[{spec_role}]** {text}\n"
        with open(notes_path, "a", encoding="utf-8") as f:
            f.write(entry)
        return {
            "role": spec_role,
            "display_name": _DESIGN_ROLE_DISPLAY.get(spec_role, spec_role),
            "tags": tags,
            "response": text,
        }
    return None



def _build_exchange_context(exchange_responses: list[dict]) -> str:
    """Build a summary of what's been said this exchange for cross-pollination."""
    if not exchange_responses:
        return ""
    lines = []
    for r in exchange_responses:
        display = r.get("display_name", r["role"])
        lines.append(f"{display}: {r['response']}")
    return "What the team said so far this exchange:\n" + "\n".join(lines)


def _identify_gaps(spec_content: str, heard_from: set[str]) -> str:
    """Return a hint about which specialists haven't been heard from."""
    all_specs = {"music_writer", "drill_writer", "choreographer"}
    missing = all_specs - heard_from
    if not missing:
        return ""
    names = [_DESIGN_ROLE_DISPLAY.get(r, r) for r in sorted(missing)]
    return f"Haven't heard from: {', '.join(names)}."


@router.post("/design/threads/{slug}/messages")
def v1_post_thread_message(slug: str, req: PostMessageRequest):
    """Post a message to a design thread — multi-round collaborative design session.

    Flow:
    1. Route message by tags → determine initial specialists
    2. Round 1: Tagged specialists respond, then PC marshals
    3. Round 2: PC's follow-up pulls in remaining specialists, then PC wraps up
    This gives a natural 4-6 message collaborative exchange from one user prompt.
    """
    show_dir = _show_dir(slug)
    from backend.services.note_router import route_note
    from backend.services.show_persistence import read_spec

    tags = route_note(req.message)

    # All specialists always engage — the design room is a collaborative meeting.
    # Tags are still used for context/metadata but don't gate specialist participation.
    specialist_roles = set(_SPECIALIST_ROLES)

    # Persist user message to design notes
    notes_path = show_dir / "design_notes.md"
    tag_comment = f"<!-- tags: {', '.join(tags)} -->\n"
    entry = f"\n**[user]** {req.message}\n"
    with open(notes_path, "a", encoding="utf-8") as f:
        f.write(tag_comment + entry)

    # Build context
    spec_content = read_spec(show_dir) or "(no spec yet)"

    responses: list[dict] = []
    llm_client = _get_llm_client()
    heard_from: set[str] = set()  # Track which specialists have contributed

    if llm_client:
        # ── Round 1: Tagged specialists respond ──
        exchange_ctx = ""
        for spec_role in sorted(specialist_roles):
            resp = _invoke_specialist(
                llm_client, slug, spec_role, notes_path,
                spec_content, exchange_ctx, req.message, tags,
            )
            if resp:
                responses.append(resp)
                heard_from.add(spec_role)
                exchange_ctx = _build_exchange_context(responses)

        # ── Round 1 PC: Marshal specialist input ──
        specialist_inputs = [
            f"{r['display_name']}: {r['response']}" for r in responses
        ]
        specialist_ctx = "Specialist input:\n" + "\n".join(specialist_inputs) if specialist_inputs else ""

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

            # ── Round 2: Follow-up — ALL specialists respond to PC's direction ──
            # Even if they already spoke in round 1, they get to react to the PC
            # and to each other. This creates the collaborative back-and-forth.
            exchange_ctx = _build_exchange_context(responses)
            round2_had_responses = False
            for spec_role in sorted(_SPECIALIST_ROLES):
                followup_prompt = (
                    f"The Program Coordinator just said: \"{pc_text}\"\n\n"
                    f"Respond from your specialist perspective. React to what "
                    f"the team proposed, add your angle, or answer the PC's question."
                )
                resp = _invoke_specialist(
                    llm_client, slug, spec_role, notes_path,
                    spec_content, exchange_ctx, followup_prompt, tags,
                )
                if resp:
                    responses.append(resp)
                    heard_from.add(spec_role)
                    exchange_ctx = _build_exchange_context(responses)
                    round2_had_responses = True

            # ── Round 2 PC: Wrap up with decisions and next steps ──
            if round2_had_responses:
                gap_hint = _identify_gaps(spec_content, heard_from)
                wrap_exchange = _build_exchange_context(responses)

                pc_followup_prompt = _PC_FOLLOWUP_TEMPLATE.format(
                    slug=slug,
                    spec_content=spec_content[:2000],
                    exchange_context=wrap_exchange,
                    gap_hint=gap_hint,
                )
                pc_wrap = _llm_chat(llm_client, pc_followup_prompt, "Wrap up this round of discussion.")
                if pc_wrap:
                    pc_wrap_entry = f"\n<!-- tags: {', '.join(tags)} -->\n**[program_coordinator]** {pc_wrap}\n"
                    with open(notes_path, "a", encoding="utf-8") as f:
                        f.write(pc_wrap_entry)
                    responses.append({
                        "role": "program_coordinator",
                        "display_name": _DESIGN_ROLE_DISPLAY["program_coordinator"],
                        "tags": tags,
                        "response": pc_wrap,
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

    # Auto-update spec + lint/judge
    if llm_client and responses:
        _update_spec_from_conversation(llm_client, show_dir, notes_path, spec_content)
    _run_lint_and_judge(show_dir, notes_path, responses)

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


@router.post("/design/threads/{slug}/continue")
def v1_continue_design(slug: str):
    """PC-driven autonomous design continuation.

    The PC reviews the current brief and conversation, identifies the most
    important gap, and drives the team to fill it. One round: PC question →
    specialists respond → PC wraps up → spec auto-updates.
    """
    show_dir = _show_dir(slug)
    from backend.services.show_persistence import read_spec

    llm_client = _get_llm_client()
    if not llm_client:
        return {"responses": [{
            "role": "program_coordinator",
            "display_name": "Program Coordinator",
            "tags": ["admin"],
            "response": "LLM unavailable — can't continue autonomously.",
        }]}

    notes_path = show_dir / "design_notes.md"
    spec_content = read_spec(show_dir) or "(no spec yet)"
    notes_content = notes_path.read_text(encoding="utf-8", errors="replace") if notes_path.exists() else "(no notes)"
    if len(notes_content) > 4000:
        notes_content = "...\n" + notes_content[-4000:]

    # Get current lint status for the PC
    lint_summary = "None"
    try:
        from backend.services.brief_linter import lint_brief
        report = lint_brief(spec_content)
        if report.required_fix:
            lint_summary = "; ".join(f"{f.section}: {f.message}" for f in report.required_fix[:5])
    except Exception:
        pass

    # PC identifies what to tackle next
    pc_prompt = _PC_CONTINUE_TEMPLATE.format(
        slug=slug,
        spec_content=spec_content[:2000],
        notes_content=notes_content,
        lint_summary=lint_summary,
    )
    pc_text = _llm_chat(llm_client, pc_prompt, "What should we work on next?")
    if not pc_text:
        return {"responses": [{
            "role": "program_coordinator",
            "display_name": "Program Coordinator",
            "tags": ["admin"],
            "response": "I'm having trouble formulating the next question. Try sending a message instead.",
        }]}

    # Persist PC's driving question
    tags = ["admin"]
    pc_entry = f"\n<!-- tags: admin -->\n**[program_coordinator]** {pc_text}\n"
    with open(notes_path, "a", encoding="utf-8") as f:
        f.write(pc_entry)

    responses: list[dict] = [{
        "role": "program_coordinator",
        "display_name": _DESIGN_ROLE_DISPLAY["program_coordinator"],
        "tags": tags,
        "response": pc_text,
    }]

    # Specialists respond to the PC's question
    exchange_ctx = _build_exchange_context(responses)
    for spec_role in sorted(_SPECIALIST_ROLES):
        resp = _invoke_specialist(
            llm_client, slug, spec_role, notes_path,
            spec_content, exchange_ctx, pc_text, tags,
        )
        if resp:
            responses.append(resp)
            exchange_ctx = _build_exchange_context(responses)

    # PC wrap-up
    if len(responses) > 1:
        wrap_exchange = _build_exchange_context(responses)
        pc_followup = _PC_FOLLOWUP_TEMPLATE.format(
            slug=slug,
            spec_content=spec_content[:2000],
            exchange_context=wrap_exchange,
            gap_hint="",
        )
        pc_wrap = _llm_chat(llm_client, pc_followup, "Wrap up this round.")
        if pc_wrap:
            pc_wrap_entry = f"\n<!-- tags: admin -->\n**[program_coordinator]** {pc_wrap}\n"
            with open(notes_path, "a", encoding="utf-8") as f:
                f.write(pc_wrap_entry)
            responses.append({
                "role": "program_coordinator",
                "display_name": _DESIGN_ROLE_DISPLAY["program_coordinator"],
                "tags": tags,
                "response": pc_wrap,
            })

    # Auto-update spec + lint/judge
    _update_spec_from_conversation(llm_client, show_dir, notes_path, spec_content)
    _run_lint_and_judge(show_dir, notes_path, responses)

    return {
        "role": responses[0]["role"],
        "tags": tags,
        "response": responses[0]["response"],
        "responses": responses,
    }


def _auto_progress_status(show_dir, notes_path, responses: list[dict]):
    """Auto-transition draft → needs_review when lint is clean."""
    try:
        from backend.services.show_persistence import load_status, update_status
        status = load_status(show_dir)
        if status.get("status") == "draft":
            update_status(show_dir, "needs_review")
            msg = "All sections filled and lint is clean. Status upgraded to needs_review — ready for approval."
            entry = f"\n<!-- tags: admin -->\n**[judge]** {msg}\n"
            with open(notes_path, "a", encoding="utf-8") as f:
                f.write(entry)
            responses.append({
                "role": "judge",
                "display_name": "Judge",
                "tags": ["admin"],
                "response": msg,
            })
    except Exception:
        pass


def _update_spec_from_conversation(llm_client, show_dir, notes_path, spec_content: str):
    """Auto-update the spec based on the full conversation. Best-effort."""
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
            updated_spec = _strip_code_fences(updated_spec)
            write_spec(show_dir, updated_spec)
            _extract_swarm_prompt(show_dir, updated_spec)
    except Exception:
        pass


def _run_lint_and_judge(show_dir, notes_path, responses: list[dict]):
    """Run linters, emit judge message (deduped), auto-progress if clean. Best-effort."""
    try:
        from backend.services.brief_linter import lint_brief
        from backend.services.prompt_linter import lint_prompt
        from backend.services.show_persistence import read_spec, missing_show_files

        brief_content = read_spec(show_dir) or ""
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
            last_judge = _get_last_judge_message(notes_path)
            if judge_text != last_judge:
                judge_entry = f"\n<!-- tags: admin -->\n**[judge]** {judge_text}\n"
                with open(notes_path, "a", encoding="utf-8") as f:
                    f.write(judge_entry)
                responses.append({
                    "role": "judge",
                    "display_name": "Judge",
                    "tags": ["admin"],
                    "response": judge_text,
                })
        else:
            _auto_progress_status(show_dir, notes_path, responses)
    except Exception:
        pass


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
