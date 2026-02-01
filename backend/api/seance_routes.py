"""Seance & Corps History API routes — filesystem readers for the UI."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


def _get_llm_client():
    """Get the LLM client from the task manager, or fall back to MockLLMClient."""
    try:
        from backend.api.app import get_task_manager
        tm = get_task_manager()
        if tm and hasattr(tm, "llm_client"):
            return tm.llm_client
    except Exception:
        pass
    from backend.services.llm_client import MockLLMClient
    return MockLLMClient()


def _get_root() -> Path:
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    if override:
        return Path(override).resolve()
    from backend.cli.commands.doctor import _find_project_root
    return Path(_find_project_root())


def _validate_id(value: str, label: str = "ID") -> None:
    if ".." in value or "/" in value or "\\" in value:
        raise HTTPException(status_code=400, detail=f"Invalid {label}")


# ---------------------------------------------------------------------------
# Corps History Index
# ---------------------------------------------------------------------------

@router.get("/api/corps/{corps_id}/history-index")
def api_get_history_index(corps_id: str):
    """Build (or return cached) history index for a corps."""
    _validate_id(corps_id, "corps_id")
    root = _get_root()
    corps_path = root / "corps" / corps_id / "corps.yaml"
    if not corps_path.is_file():
        raise HTTPException(status_code=404, detail=f"Corps '{corps_id}' not found")

    from backend.services.corps_history import load_history_index
    return load_history_index(root, corps_id)


# ---------------------------------------------------------------------------
# Seance Sessions
# ---------------------------------------------------------------------------

class CreateSeanceRequest(BaseModel):
    corps_id: str
    entry_id: str


@router.post("/api/seances")
def api_create_seance(req: CreateSeanceRequest):
    """Create a seance session from a history entry."""
    _validate_id(req.corps_id, "corps_id")
    root = _get_root()
    from backend.services.seance_session import create_session
    try:
        return create_session(root, req.corps_id, req.entry_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/seances/{seance_id}")
def api_get_seance(seance_id: str):
    """Get seance session metadata + context binder."""
    _validate_id(seance_id, "seance_id")
    root = _get_root()
    from backend.services.seance_session import load_session
    try:
        return load_session(root, seance_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/seances/{seance_id}/binder")
def api_get_seance_binder(seance_id: str):
    """Get context binder for a seance."""
    _validate_id(seance_id, "seance_id")
    root = _get_root()
    from backend.services.seance_session import load_session
    try:
        session = load_session(root, seance_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"seance_id": seance_id, "context_binder": session["context_binder"]}


@router.get("/api/seances/{seance_id}/transcript")
def api_get_seance_transcript(seance_id: str):
    """Read transcript for a seance."""
    _validate_id(seance_id, "seance_id")
    root = _get_root()
    from backend.services.seance_session import read_transcript
    try:
        content = read_transcript(root, seance_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"seance_id": seance_id, "transcript": content}


class SeanceMessageRequest(BaseModel):
    message: str
    role: str = "user"
    mode: str = "strict"  # "strict" or "relaxed"


@router.post("/api/seances/{seance_id}/message")
def api_post_seance_message(seance_id: str, req: SeanceMessageRequest):
    """Post a message to a seance session and get an ED response grounded in binder artifacts."""
    _validate_id(seance_id, "seance_id")
    if req.mode not in ("strict", "relaxed"):
        raise HTTPException(status_code=400, detail="mode must be 'strict' or 'relaxed'")
    root = _get_root()
    from backend.services.seance_session import load_session
    try:
        session = load_session(root, seance_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if session.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Seance session is closed")

    # Get LLM client from app state
    llm_client = _get_llm_client()

    from backend.services.ed_chat import ed_respond
    try:
        return ed_respond(
            project_root=root,
            session=session,
            user_message=req.message,
            llm_client=llm_client,
            mode=req.mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/seances/{seance_id}/artifact-preview")
def api_preview_artifact(seance_id: str, path: str = ""):
    """Preview an artifact file from the context binder (read-only, truncated)."""
    _validate_id(seance_id, "seance_id")
    if ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")
    root = _get_root()
    from backend.services.seance_session import load_session
    try:
        session = load_session(root, seance_id)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Only allow paths that are in the context binder
    binder_paths = {item["path"] for item in session["context_binder"]}
    if path not in binder_paths:
        raise HTTPException(status_code=403, detail="Path not in context binder")

    abs_path = root / path
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found")

    content = abs_path.read_text()
    # Truncate large files
    max_chars = 10_000
    truncated = len(content) > max_chars
    return {
        "path": path,
        "content": content[:max_chars],
        "truncated": truncated,
    }
