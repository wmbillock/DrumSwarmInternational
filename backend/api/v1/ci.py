"""V1 API — CI/Testing/Coverage routes."""

from fastapi import APIRouter, HTTPException

from backend.api.v1.helpers import _validate_id

router = APIRouter(prefix="/api/v1")


@router.get("/ci/status")
def get_ci_status():
    """Get current CI watcher status."""
    from backend.services.ci_watcher import get_ci_watcher
    return get_ci_watcher().get_status()


@router.post("/ci/run")
def trigger_ci_run():
    """Manually trigger a CI run (full test suite + coverage)."""
    from backend.services.ci_watcher import get_ci_watcher
    import threading
    watcher = get_ci_watcher()

    def _run():
        watcher.run_manual(trigger="api_request")

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "message": "CI run triggered"}


@router.get("/ci/coverage/{show_slug}")
def get_show_coverage(show_slug: str):
    """Get coverage report for a completed show (used in scoring/judging)."""
    _validate_id(show_slug, "show_slug")
    from backend.services.ci_watcher import get_ci_watcher
    data = get_ci_watcher().get_coverage_for_show(show_slug)
    if data is None:
        raise HTTPException(404, f"No coverage data for show '{show_slug}'")
    return data
