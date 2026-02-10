"""Shared data-fetching layer for the DCI dashboard.

Architecture:
- A background daemon thread refreshes data into a cache on a timer.
- All public get_* functions return instantly from cache (never block the caller).
- Service-down cooldown prevents hammering dead endpoints every cycle.
- The active tab controls which data set gets refreshed each cycle.

Used by both the tmux-based unified_dashboard.py and the Textual TUI.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

BACKEND_PORT = os.environ.get("DCI_PORT", "4224")
API_BASE = os.environ.get("DCI_API_URL", f"http://localhost:{BACKEND_PORT}")
PROJECT_ROOT = os.environ.get(
    "DCI_ROOT",
    str(Path(__file__).resolve().parent.parent.parent),
)
LOG_FILE = os.path.join(PROJECT_ROOT, "backend.log")
FE_LOG_FILE = os.path.join(PROJECT_ROOT, "frontend.log")

# ── Tuning ────────────────────────────────────────────────────────────
_FETCH_TIMEOUT = 0.5  # localhost responds instantly or not at all
_SERVICE_COOLDOWN = 15.0  # seconds to skip retrying a down service
_REFRESH_INTERVAL = 5.0  # seconds between background refresh cycles

# ── Internal state ────────────────────────────────────────────────────
_cache: dict[str, Any] = {}
_lock = threading.Lock()
_backend_down_until = 0.0
_frontend_down_until = 0.0
_active_tab = "metrics"
_refresh_thread: threading.Thread | None = None
_stop_event = threading.Event()
_wake_event = threading.Event()  # poked by request_refresh()


# ── Cache helpers ─────────────────────────────────────────────────────

def _put(key: str, value: Any) -> None:
    with _lock:
        _cache[key] = value


def _get(key: str, default: Any = None) -> Any:
    with _lock:
        return _cache.get(key, default)


# ── Low-level HTTP (internal only) ───────────────────────────────────

def _http_get(path: str, timeout: float = _FETCH_TIMEOUT) -> Any:
    """GET an API endpoint, return parsed JSON or None."""
    try:
        req = urllib.request.Request(
            f"{API_BASE}{path}", headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _http_post(path: str, data: dict | None = None, timeout: float = _FETCH_TIMEOUT) -> Any:
    """POST to an API endpoint, return parsed JSON or None."""
    try:
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            data=body,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


# ── Public HTTP helpers (used by actions.py — NOT cached) ─────────────

def fetch(path: str, timeout: int = 3) -> Any:
    """Direct API GET for one-shot action calls. Not cached."""
    return _http_get(path, timeout=timeout)


def api_post(path: str, data: dict | None = None, timeout: int = 5) -> Any:
    """Direct API POST for one-shot action calls. Not cached."""
    return _http_post(path, data=data, timeout=timeout)


# ── Service probes (with cooldown) ───────────────────────────────────

def _check_backend() -> bool:
    global _backend_down_until
    now = time.monotonic()
    if now < _backend_down_until:
        return False
    up = _http_get("/api/v1/system/health") is not None
    if not up:
        _backend_down_until = now + _SERVICE_COOLDOWN
    else:
        _backend_down_until = 0.0  # reset on recovery
    return up


def _check_frontend() -> bool:
    global _frontend_down_until
    now = time.monotonic()
    if now < _frontend_down_until:
        return False
    try:
        urllib.request.urlopen("http://localhost:5173", timeout=_FETCH_TIMEOUT)
        _frontend_down_until = 0.0
        return True
    except Exception:
        _frontend_down_until = now + _SERVICE_COOLDOWN
        return False


# ── Refresh functions (run on background thread) ─────────────────────

def _refresh_service_status() -> dict:
    status = {
        "backend": _check_backend(),
        "frontend": _check_frontend(),
        "backend_port": BACKEND_PORT,
    }
    _put("service_status", status)
    return status


def _refresh_shows_summary(backend_up: bool) -> None:
    if not backend_up:
        if _get("shows_summary") is None:
            _put("shows_summary", _empty_shows())
        return

    shows = _http_get("/api/v1/shows") or []
    result = {
        "total": len(shows),
        "active": sum(1 for s in shows if s.get("status") == "active"),
        "draft": sum(1 for s in shows if s.get("status") == "draft"),
        "completed": sum(1 for s in shows if s.get("status") == "completed"),
        "active_details": [],
    }

    for show in shows:
        if show.get("status") != "active" or not show.get("corps_id"):
            continue
        corps_id = show["corps_id"]
        corps = _http_get(f"/api/v1/corps/{corps_id}")
        roster = _http_get(f"/api/v1/corps/{corps_id}/roster") or []
        active_agents = sum(1 for a in roster if a.get("status") == "active")
        result["active_details"].append({
            "title": show.get("title", "?"),
            "corps_id": corps_id,
            "corps_name": corps.get("name", "?") if corps else "?",
            "total_agents": len(roster),
            "active_agents": active_agents,
        })

    _put("shows_summary", result)


def _refresh_agent_roster(backend_up: bool) -> None:
    if not backend_up:
        if _get("agent_roster") is None:
            _put("agent_roster", [])
        return

    shows = _http_get("/api/v1/shows") or []
    active_shows = [s for s in shows if s.get("status") == "active" and s.get("corps_id")]
    results = []

    for show in active_shows:
        corps_id = show["corps_id"]
        title = show.get("title", "Untitled")
        roster = _http_get(f"/api/v1/corps/{corps_id}/roster") or []

        by_status: dict[str, int] = {}
        for agent in roster:
            s = agent.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1

        by_parent: dict[str | None, list] = {}
        for a in roster:
            pid = a.get("parent_session_id")
            by_parent.setdefault(pid, []).append(a)

        results.append({
            "title": title,
            "corps_id": corps_id,
            "roster": roster,
            "by_status": by_status,
            "by_parent": by_parent,
            "roots": by_parent.get(None, []),
        })

    _put("agent_roster", results)


def _refresh_recent_logs() -> None:
    n = 50
    if not os.path.exists(LOG_FILE):
        _put("recent_logs", [])
        return

    try:
        with open(LOG_FILE, "r", errors="replace") as f:
            lines = f.readlines()
        recent = lines[-n:] if len(lines) > n else lines
        result = []
        for line in recent:
            line = line.rstrip()
            if not line:
                continue
            level = "info"
            if "ERROR" in line or "error" in line.lower():
                level = "error"
            elif "WARNING" in line or "warn" in line.lower():
                level = "warning"

            is_http = False
            method_path = ""
            status_code = ""
            if "INFO" in line and ("GET " in line or "POST " in line):
                parts = line.split('"')
                if len(parts) >= 2:
                    is_http = True
                    method_path = parts[1][:60]
                    status_code = parts[2].strip()[:3] if len(parts) > 2 else ""

            result.append({
                "raw": line[:200],
                "level": level,
                "is_http": is_http,
                "method_path": method_path,
                "status_code": status_code,
            })
        _put("recent_logs", result)
    except Exception:
        _put("recent_logs", [])


def _refresh_git_status() -> None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "-u"],
            capture_output=True, text=True, timeout=5, cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            _put("git_status", {"staged": [], "unstaged": []})
            return

        staged = []
        unstaged = []
        for line in result.stdout.strip().splitlines():
            if len(line) < 4:
                continue
            index_status = line[0].strip()
            work_status = line[1].strip()
            filepath = line[3:]
            status = work_status or index_status or "?"
            is_staged = index_status not in ("?", " ", "")
            entry = {"status": status, "path": filepath}
            if is_staged:
                staged.append(entry)
            else:
                unstaged.append(entry)
        _put("git_status", {"staged": staged, "unstaged": unstaged})
    except Exception:
        _put("git_status", {"staged": [], "unstaged": []})


def _refresh_recent_commits() -> None:
    try:
        result = subprocess.run(
            ["git", "log", "-8", "--pretty=format:%h %s"],
            capture_output=True, text=True, timeout=5, cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            _put("recent_commits", [])
            return
        commits = []
        for line in result.stdout.strip().splitlines():
            parts = line.split(" ", 1)
            commits.append({
                "hash": parts[0] if parts else "",
                "message": parts[1] if len(parts) > 1 else "",
            })
        _put("recent_commits", commits)
    except Exception:
        _put("recent_commits", [])


def _refresh_completed_reps(backend_up: bool) -> None:
    if not backend_up:
        if _get("completed_reps") is None:
            _put("completed_reps", [])
        return

    shows = _http_get("/api/v1/shows") or []
    active = [s for s in shows if s.get("status") == "active"]
    results = []
    for show in active[:3]:
        coord_root = show.get("segment_root_id")
        if not coord_root:
            continue
        reps = _http_get(f"/api/v1/segments/{coord_root}/reps") or []
        if reps:
            results.append({
                "title": show.get("title", "?"),
                "completed": sum(1 for r in reps if r.get("status") == "completed"),
                "failed": sum(1 for r in reps if r.get("status") == "failed"),
                "pending": sum(
                    1 for r in reps
                    if r.get("status") in ("pending", "assigned", "in_progress")
                ),
            })
    _put("completed_reps", results)


def _refresh_agent_memory(backend_up: bool) -> None:
    if not backend_up:
        if _get("agent_memory") is None:
            _put("agent_memory", [])
        return

    shows = _http_get("/api/v1/shows") or []
    active_shows = [s for s in shows if s.get("status") == "active" and s.get("corps_id")]
    results = []

    for show in active_shows[:3]:
        corps_id = show["corps_id"]
        roster = _http_get(f"/api/v1/corps/{corps_id}/roster") or []
        title = show.get("title", "Untitled")

        agents = []
        for agent in roster[:8]:
            identity = agent.get("nickname") or agent.get("role", "?")
            stats = _http_get(f"/api/v1/agents/{identity}/memory-stats")
            if not stats:
                continue
            agents.append({
                "role": agent.get("role", "?"),
                "total_memories": stats.get("total_memories", 0),
                "task_memories": stats.get("task_memories", 0),
                "avg_confidence": stats.get("avg_confidence", 0),
                "by_type": stats.get("by_type", {}),
            })

        results.append({"title": title, "corps_id": corps_id, "agents": agents})

    _put("agent_memory", results)


def _refresh_lifecycle(backend_up: bool) -> None:
    if not backend_up:
        if _get("lifecycle") is None:
            _put("lifecycle", [])
        return

    shows = _http_get("/api/v1/shows") or []
    active_shows = [s for s in shows if s.get("status") == "active" and s.get("corps_id")]
    results = []

    for show in active_shows[:3]:
        corps_id = show["corps_id"]
        corps = _http_get(f"/api/v1/corps/{corps_id}")
        if not corps:
            continue

        ageouts = _http_get(f"/api/v1/corps/{corps_id}/ageouts") or []
        roster = _http_get(f"/api/v1/corps/{corps_id}/roster") or []
        pending_improvements = _http_get("/api/v1/self-improvement/pending") or []

        by_class: dict[str, dict] = {}
        for agent in roster:
            cls = agent.get("classification", "unknown")
            entry = by_class.setdefault(cls, {"total": 0, "active": 0})
            entry["total"] += 1
            if agent.get("status") == "active":
                entry["active"] += 1

        results.append({
            "title": show.get("title", "Untitled"),
            "corps_id": corps_id,
            "mascot": corps.get("mascot", "—"),
            "theme": corps.get("theme_id", "—"),
            "ageouts": ageouts,
            "by_classification": by_class,
            "pending_improvements": pending_improvements,
        })

    _put("lifecycle", results)


# ── Defaults ──────────────────────────────────────────────────────────

def _empty_shows() -> dict:
    return {"total": 0, "active": 0, "draft": 0, "completed": 0, "active_details": []}


# ── Background loop ──────────────────────────────────────────────────

_TAB_REFRESHERS: dict[str, Any] = {
    "metrics": lambda up: _refresh_shows_summary(up),
    "agents": lambda up: _refresh_agent_roster(up),
    "logs": lambda _: _refresh_recent_logs(),
    "changes": lambda up: (_refresh_git_status(), _refresh_recent_commits(), _refresh_completed_reps(up)),
    "memory": lambda up: _refresh_agent_memory(up),
    "lifecycle": lambda up: _refresh_lifecycle(up),
}


def _refresh_cycle() -> None:
    status = _refresh_service_status()
    backend_up = status["backend"]
    tab = _active_tab
    refresher = _TAB_REFRESHERS.get(tab)
    if refresher:
        refresher(backend_up)


def _background_loop() -> None:
    while not _stop_event.is_set():
        try:
            _refresh_cycle()
        except Exception:
            pass
        # Sleep until next cycle OR until poked by request_refresh()
        _wake_event.wait(timeout=_REFRESH_INTERVAL)
        _wake_event.clear()


# ── Public control API ────────────────────────────────────────────────

def start() -> None:
    """Start the background data-refresh thread. Idempotent."""
    global _refresh_thread
    if _refresh_thread is not None and _refresh_thread.is_alive():
        return
    _stop_event.clear()
    _wake_event.clear()
    _refresh_thread = threading.Thread(
        target=_background_loop, daemon=True, name="dashboard-data"
    )
    _refresh_thread.start()


def stop() -> None:
    """Stop the background data-refresh thread."""
    _stop_event.set()
    _wake_event.set()  # unblock the sleep
    if _refresh_thread is not None:
        _refresh_thread.join(timeout=2)


def set_active_tab(tab: str) -> None:
    """Tell the data layer which tab to prioritize on next cycle."""
    global _active_tab
    _active_tab = tab


def request_refresh() -> None:
    """Wake the background thread for an immediate refresh cycle."""
    _wake_event.set()


def reset_cooldowns() -> None:
    """Clear service-down cooldowns (e.g. after user starts a service)."""
    global _backend_down_until, _frontend_down_until
    _backend_down_until = 0.0
    _frontend_down_until = 0.0
    request_refresh()


# ── Public getters (instant cache reads — never block) ────────────────

def get_service_status() -> dict:
    return _get("service_status", {"backend": False, "frontend": False, "backend_port": BACKEND_PORT})


def get_shows_summary() -> dict:
    return _get("shows_summary", _empty_shows())


def get_agent_roster() -> list[dict]:
    return _get("agent_roster", [])


def get_recent_logs(n: int = 40) -> list[dict]:
    return _get("recent_logs", [])


def get_frontend_logs(n: int = 20) -> list[str]:
    """Read frontend log lines directly (cheap file I/O, not cached)."""
    if not os.path.exists(FE_LOG_FILE):
        return []
    try:
        with open(FE_LOG_FILE, "r", errors="replace") as f:
            lines = f.readlines()
        return [line.rstrip() for line in lines[-n:] if line.strip()]
    except Exception:
        return []


def get_git_status() -> dict:
    return _get("git_status", {"staged": [], "unstaged": []})


def get_recent_commits(n: int = 8) -> list[dict]:
    return _get("recent_commits", [])


def get_completed_reps() -> list[dict]:
    return _get("completed_reps", [])


def get_agent_memory_stats() -> list[dict]:
    return _get("agent_memory", [])


def get_lifecycle_data() -> list[dict]:
    return _get("lifecycle", [])


# ── Legacy shim: backend_up / frontend_up (used by old callers) ───────

def backend_up() -> bool:
    return get_service_status()["backend"]


def frontend_up() -> bool:
    return get_service_status()["frontend"]
