"""Executive Director retrospective chat — grounded in seance binder artifacts.

The ED responds to user questions about a past show, using only the artifacts
loaded into the seance's context binder. Two strictness modes control how
the ED handles questions that go beyond binder content.
"""

from pathlib import Path

from backend.models.agent_definition import ModelTier
from backend.services.llm_client import LLMClient, LLMMessage
from backend.services.seance_session import (
    assemble_context,
    append_transcript,
    read_transcript,
)

# Per-artifact truncation limit to keep prompt manageable
ARTIFACT_TRUNCATE = 4_000

STRICT_PREAMBLE = (
    "STRICT MODE: You may ONLY cite, quote, or reference information that appears "
    "in the binder artifacts below. If the user asks about something not covered by "
    "the binder, say so explicitly — do NOT invent scores, placements, captions, "
    "or any other facts. If an artifact is missing from the binder, state which "
    "artifact would be needed to answer the question."
)

RELAXED_PREAMBLE = (
    "RELAXED MODE: You should ground your answers in the binder artifacts below. "
    "If the user asks about something not fully covered by the binder, you MAY "
    "hypothesize, but you MUST clearly label every hypothesis with [HYPOTHESIS]. "
    "Never present a hypothesis as established fact. Never invent specific scores, "
    "placements, or artifact contents."
)

ED_IDENTITY = (
    "You are the Executive Director of {corps_id}, reflecting on season {season_id}"
    "{show_clause}. You are speaking with a user who wants to understand what happened "
    "during this competition. Answer in first person as the ED. Be concise and specific, "
    "referencing actual data from the binder when possible."
)


def build_ed_prompt(project_root: Path, session: dict, mode: str = "strict") -> str:
    """Build the system prompt for the ED, including binder artifacts."""
    project_root = Path(project_root)

    show_clause = ""
    if session.get("show_slug"):
        show_clause = f" (show: {session['show_slug']})"

    identity = ED_IDENTITY.format(
        corps_id=session["corps_id"],
        season_id=session["season_id"],
        show_clause=show_clause,
    )

    preamble = STRICT_PREAMBLE if mode == "strict" else RELAXED_PREAMBLE

    # Build binder manifest
    binder_lines = ["BINDER MANIFEST:"]
    for item in session["context_binder"]:
        status = "loaded" if item["loaded"] else "NOT LOADED (empty/missing)"
        binder_lines.append(f"  - [{item['type']}] {item['path']} — {status}")

    # Read and truncate each loaded artifact
    artifact_sections = []
    for item in session["context_binder"]:
        if not item["loaded"]:
            continue
        abs_path = project_root / item["path"]
        if not abs_path.exists():
            continue
        content = abs_path.read_text().strip()
        if not content:
            continue
        if len(content) > ARTIFACT_TRUNCATE:
            content = content[:ARTIFACT_TRUNCATE] + "\n[... truncated ...]"
        artifact_sections.append(f"--- {item['type']} ({item['path']}) ---\n{content}")

    artifacts_block = "\n\n".join(artifact_sections) if artifact_sections else "(no artifacts loaded)"

    return (
        f"{identity}\n\n"
        f"{preamble}\n\n"
        f"{chr(10).join(binder_lines)}\n\n"
        f"ARTIFACT CONTENTS:\n\n{artifacts_block}"
    )


def _parse_transcript_messages(transcript: str) -> list[LLMMessage]:
    """Parse transcript.md into LLM message pairs."""
    messages: list[LLMMessage] = []
    for line in transcript.split("\n"):
        line = line.strip()
        if line.startswith("**[user]** "):
            messages.append(LLMMessage(role="user", content=line[len("**[user]** "):]))
        elif line.startswith("**[executive_director]** "):
            messages.append(LLMMessage(role="assistant", content=line[len("**[executive_director]** "):]))
    return messages


def ed_respond(
    project_root: Path,
    session: dict,
    user_message: str,
    llm_client: LLMClient,
    mode: str = "strict",
    model_tier: ModelTier = ModelTier.SONNET,
) -> dict:
    """Generate an ED response grounded in binder artifacts.

    Returns dict with role, message, mode, seance_id.
    """
    project_root = Path(project_root)

    if session.get("status") == "closed":
        raise ValueError("Seance session is closed")

    seance_id = session["seance_id"]

    # Build system prompt with binder content
    system_prompt = build_ed_prompt(project_root, session, mode=mode)

    # Build conversation history from transcript
    transcript = read_transcript(project_root, seance_id)
    history = _parse_transcript_messages(transcript)

    # Assemble messages: system + history + current user message
    messages = [LLMMessage(role="system", content=system_prompt)]
    messages.extend(history)
    messages.append(LLMMessage(role="user", content=user_message))

    # Call LLM
    response = llm_client.chat(
        messages=messages,
        model_tier=model_tier,
    )

    ed_message = response.content.strip() or "(no response)"

    # Append both messages to transcript
    append_transcript(project_root, seance_id, "user", user_message)
    append_transcript(project_root, seance_id, "executive_director", ed_message)

    return {
        "role": "executive_director",
        "message": ed_message,
        "seance_id": seance_id,
        "mode": mode,
    }
