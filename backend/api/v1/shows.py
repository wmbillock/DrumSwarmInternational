"""V1 API — Shows routes."""

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _get_db_session, _shows_dir

router = APIRouter(prefix="/api/v1")


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
    show_path = create_show(title, _shows_dir())
    slug = show_path.name
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
    show_dir = _shows_dir() / slug
    if not show_dir.exists():
        raise HTTPException(404, "Show not found")
    shutil.rmtree(show_dir)
    return {"status": "deleted", "slug": slug}


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
