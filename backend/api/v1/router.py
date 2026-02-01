"""V1 API router — thin adapters over existing service modules.

All business logic lives in backend/services/. These routes only translate
HTTP ↔ service calls and enforce slug/id validation.
"""

import hashlib
import os
import re
from datetime import datetime, timezone
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

@router.get("/corps")
def v1_list_corps():
    """List all corps from filesystem workspaces."""
    root = _get_root()
    corps_base = root / "corps"
    if not corps_base.exists():
        return []
    result = []
    for corps_dir in sorted(corps_base.iterdir()):
        corps_path = corps_dir / "corps.yaml"
        if not corps_path.is_file():
            continue
        try:
            data = yaml.safe_load(corps_path.read_text())
            result.append({
                "corps_id": data.get("corps_id", corps_dir.name),
                "display_name": data.get("display_name", corps_dir.name),
                "philosophy": data.get("philosophy", ""),
                "state": data.get("state", "unknown"),
            })
        except Exception:
            continue
    return result


@router.get("/corps/{corps_id}")
def v1_get_corps(corps_id: str):
    """Get corps detail including roster size and history."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    corps_path = root / "corps" / corps_id / "corps.yaml"
    if not corps_path.is_file():
        raise HTTPException(404, f"Corps '{corps_id}' not found")
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


# =========================================================================
# RUNS
# =========================================================================

@router.get("/runs")
def v1_list_runs():
    """List all run manifests across seasons."""
    root = _get_root()
    seasons_dir = root / "seasons"
    if not seasons_dir.exists():
        return []
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

    corps_dir = root / "corps" / req.corps_id
    if not (corps_dir / "corps.yaml").exists():
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


@router.post("/design/threads/{slug}/messages")
def v1_post_thread_message(slug: str, req: PostMessageRequest):
    """Post a message to a design thread — routes via note_router."""
    show_dir = _show_dir(slug)
    from backend.services.note_router import route_note

    tags = route_note(req.message)

    TAG_TO_ROLE = {
        "music": "music_writer", "visual": "drill_writer",
        "guard": "choreographer", "ge": "program_coordinator",
        "admin": "program_coordinator", "questions": "program_coordinator",
    }
    if req.role_hint and req.role_hint in TAG_TO_ROLE.values():
        role = req.role_hint
    else:
        role = TAG_TO_ROLE.get(tags[0], "program_coordinator") if tags else "program_coordinator"

    notes_path = show_dir / "design_notes.md"
    tag_comment = f"<!-- tags: {', '.join(tags)} -->\n"
    entry = f"\n**[user]** {req.message}\n"
    with open(notes_path, "a") as f:
        f.write(tag_comment + entry)

    return {
        "role": role,
        "tags": tags,
        "response": f"[{role}] Noted. Tags: {', '.join(tags)}.",
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
    """List past shows for a corps (builds/returns history index)."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    from backend.services.corps_history import build_history_index
    try:
        index = build_history_index(root, corps_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return index


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


# =========================================================================
# COMPETITIONS
# =========================================================================

class CreateCompetitionRequest(BaseModel):
    season_id: str
    show_slug: str
    corps_ids: list[str]


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

    from backend.services.season_persistence import register_corps
    for cid in req.corps_ids:
        corps_dir = root / "corps" / cid
        if not (corps_dir / "corps.yaml").exists():
            raise HTTPException(404, f"Corps '{cid}' not found")
        register_corps(season_dir, cid, root / "corps")

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
    parts = competition_id.split("-", 1)
    if len(parts) != 2:
        raise HTTPException(400, "Invalid competition_id format (expected season_id-show_slug)")
    season_id, show_slug = parts

    root = _get_root()
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

    for cid in corps_ids:
        if not (root / "corps" / cid / "corps.yaml").exists():
            raise HTTPException(400, f"Corps '{cid}' no longer exists")

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
    parts = competition_id.split("-", 1)
    if len(parts) != 2:
        raise HTTPException(400, "Invalid competition_id format")
    season_id, _show_slug = parts

    root = _get_root()
    standings_path = root / "seasons" / season_id / "standings.yaml"
    if not standings_path.exists():
        raise HTTPException(404, "Standings not found — competition may not have run yet")
    standings = yaml.safe_load(standings_path.read_text())
    standings["competition_id"] = competition_id
    standings["show_slug"] = _show_slug
    return standings


def _stub_caption_scores(corps_id: str, show_slug: str) -> dict:
    """Deterministic scores per caption, seeded from corps_id + show_slug."""
    from backend.models.score import JudgeType
    scores = {}
    for jtype in [JudgeType.BRASS, JudgeType.PERCUSSION, JudgeType.GUARD,
                  JudgeType.VISUAL, JudgeType.GENERAL_EFFECT]:
        seed = hashlib.sha256(f"{corps_id}:{show_slug}:{jtype.value}".encode()).hexdigest()
        scores[jtype] = (int(seed[:8], 16) % 30) + 60
    return scores
