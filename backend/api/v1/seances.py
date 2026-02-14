"""V1 API — Seance routes."""

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _validate_id, _get_root, _get_db_session
from backend.api.v1.schemas import CreateSeanceRequest, SeanceMessageRequest

router = APIRouter(prefix="/api/v1")


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

    content = abs_path.read_text(encoding="utf-8")
    max_chars = 10_000
    truncated = len(content) > max_chars
    return {"path": path, "content": content[:max_chars], "truncated": truncated}
