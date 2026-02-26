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


def _get_seance_llm_client():
    """Get an LLM client suitable for seance queries.

    Prefers direct API clients (Anthropic > OpenAI > Ollama) over CLI clients,
    because CLI clients inject CLAUDE.md/agent context that overwhelms the
    ED persona. Falls back to MockLLMClient if no API keys are available.
    """
    import os

    # Try Anthropic API first
    if os.environ.get("ANTHROPIC_SDK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from backend.services.llm_client import AnthropicLLMClient
            return AnthropicLLMClient()
        except Exception:
            pass

    # Try OpenAI API
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from backend.services.llm_client import OpenAIClient
            return OpenAIClient()
        except Exception:
            pass

    # Try Ollama (local)
    try:
        from backend.services.llm_client import OllamaClient
        client = OllamaClient()
        # Quick check that Ollama is reachable
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return client
    except Exception:
        pass

    # Fallback to mock
    from backend.services.llm_client import MockLLMClient
    return MockLLMClient()


def _gather_corps_context(db, corps) -> str:
    """Load real data about a corps to give the ED actual facts to reference."""
    import json
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition

    lines = [f"CORPS STATUS REPORT FOR: {corps.name}"]
    lines.append(f"  Corps ID: {corps.id}")
    lines.append(f"  Lifecycle Status: {corps.status.value if corps.status else 'unknown'}")
    lines.append(f"  Current Mode: {corps.mode.value if corps.mode else 'none'}")
    if corps.rehearsal_mode:
        lines.append(f"  Rehearsal Phase: {corps.rehearsal_mode.value}")
    if corps.caption_affinity:
        lines.append(f"  Caption Affinity: {corps.caption_affinity}")
    if corps.mascot:
        lines.append(f"  Mascot: {corps.mascot}")
    if corps.uniform_concept:
        lines.append(f"  Uniform Concept: {corps.uniform_concept}")
    lines.append(f"  Created: {corps.created_at}")

    # Founding identity
    if corps.founding_definition:
        try:
            fd = json.loads(corps.founding_definition)
            identity = fd.get("identity", {})
            if identity.get("philosophy"):
                lines.append(f"\nPHILOSOPHY: {identity['philosophy']}")
            if identity.get("personality"):
                lines.append(f"PERSONALITY: {identity['personality']}")
            strengths = fd.get("strengths", [])
            if strengths:
                lines.append(f"STRENGTHS: {', '.join(strengths)}")
            weaknesses = fd.get("weaknesses", [])
            if weaknesses:
                lines.append(f"WEAKNESSES: {', '.join(weaknesses)}")
        except (json.JSONDecodeError, TypeError):
            pass

    # Agent roster
    active_agents = db.query(AgentSession).filter(
        AgentSession.corps_id == corps.id,
        AgentSession.status == SessionStatus.ACTIVE,
    ).count()
    total_agents = db.query(AgentSession).filter(
        AgentSession.corps_id == corps.id,
    ).count()
    lines.append(f"\nROSTER: {active_agents} active agents, {total_agents} total sessions")

    # Role breakdown via join to AgentDefinition
    from sqlalchemy import func, select
    role_counts = db.execute(
        select(AgentDefinition.role, func.count())
        .join(AgentSession, AgentSession.definition_id == AgentDefinition.id)
        .where(
            AgentSession.corps_id == corps.id,
            AgentSession.status == SessionStatus.ACTIVE,
        )
        .group_by(AgentDefinition.role)
    ).all()
    if role_counts:
        lines.append("ACTIVE ROLES:")
        for role, count in role_counts:
            lines.append(f"  - {role}: {count}")

    # Competition/season history from filesystem
    try:
        from backend.api.v1.helpers import _get_root
        root = _get_root()
        seasons_dir = root / "seasons"
        if seasons_dir.exists():
            season_entries = []
            for sdir in seasons_dir.iterdir():
                if not sdir.is_dir():
                    continue
                season_file = sdir / "season.yaml"
                if not season_file.exists():
                    continue
                try:
                    import yaml
                    sdata = yaml.safe_load(season_file.read_text(encoding="utf-8"))
                    if not isinstance(sdata, dict):
                        continue
                    registered = sdata.get("registered_corps", [])
                    if corps.id in registered or corps.name in registered:
                        season_entries.append({
                            "season_id": sdir.name,
                            "status": sdata.get("status", "unknown"),
                            "schedule_count": len(sdata.get("schedule", [])),
                        })
                        # Check standings
                        standings_file = sdir / "standings.yaml"
                        if standings_file.exists():
                            try:
                                standings = yaml.safe_load(standings_file.read_text(encoding="utf-8"))
                                if isinstance(standings, list):
                                    for s in standings:
                                        if isinstance(s, dict) and s.get("corps_id") == corps.id:
                                            season_entries[-1]["standing"] = s
                            except Exception:
                                pass
                except Exception:
                    continue
            if season_entries:
                lines.append("\nSEASON PARTICIPATION:")
                for se in season_entries:
                    line = f"  - {se['season_id']}: status={se['status']}, rounds={se['schedule_count']}"
                    if se.get("standing"):
                        st = se["standing"]
                        line += f", rank={st.get('rank', '?')}, score={st.get('final_score', '?')}"
                    lines.append(line)
    except Exception:
        pass

    return "\n".join(lines)


def query_ed(db, corps_id: str, question: str) -> dict:
    """Standalone ED query — answers questions about a corps without a full seance session.

    This is the simplified entry point used by the /seance/query endpoint.
    It loads real corps data and builds a grounded prompt so the ED can answer
    factually about the corps' actual state.
    """
    from backend.models.corps import Corps
    from sqlalchemy import select

    corps = db.execute(select(Corps).where(Corps.id == corps_id)).scalar_one_or_none()
    if not corps:
        return {
            "role": "executive_director",
            "message": f"I couldn't find a corps with ID '{corps_id}'. Are you sure that's right?",
            "corps_id": corps_id,
        }

    # Gather real data about the corps
    context = _gather_corps_context(db, corps)

    system_prompt = (
        f"You are the Executive Director of {corps.name}. "
        f"You are speaking with the DCI director (the user running the swarm). "
        f"Answer their questions about your corps using the data provided below. "
        f"Be concise, in-character, and speak in first person. "
        f"Reference specific facts from the status report. "
        f"If the data doesn't cover something, say so honestly — never invent facts.\n\n"
        f"{context}"
    )

    # Use direct Anthropic API for seance queries — ClaudeCLIClient injects
    # CLAUDE.md and full agent context which overwhelms the ED persona.
    llm_client = _get_seance_llm_client()

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=question),
    ]

    response = llm_client.chat(messages=messages, model_tier=ModelTier.SONNET)
    return {
        "role": "executive_director",
        "message": response.content.strip() or "(no response)",
        "corps_id": corps_id,
    }


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
