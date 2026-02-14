"""Cross-platform swarm actions — pure Python replacements for swarm_actions.sh.

Each action returns (title: str, output: str) for display in the TUI modal.

Subprocess management:
- Backend and frontend run as child processes of the TUI (no new windows).
- `shutdown_children()` terminates all managed children — called on TUI exit.
"""

from __future__ import annotations

import atexit
import json
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)

BACKEND_PORT = os.environ.get("DCI_PORT", "4224")
API_BASE = os.environ.get("DCI_API_URL", f"http://localhost:{BACKEND_PORT}")
VENV_DIR = os.path.join(_project_root, ".venv")

# ── Managed child processes ───────────────────────────────────────────

_children: dict[str, subprocess.Popen] = {}  # "backend" | "frontend" → Popen


def _spawn(name: str, cmd: list[str], cwd: str, log_path: str) -> subprocess.Popen:
    """Spawn a child process with stdout/stderr to a log file, no new window."""
    _stop_child(name)

    log_fh = open(log_path, "w")
    kwargs: dict = dict(
        cwd=cwd,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
    )
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    proc = subprocess.Popen(cmd, **kwargs)
    _children[name] = proc
    return proc


def _stop_child(name: str) -> None:
    """Terminate a managed child if it's still running."""
    proc = _children.pop(name, None)
    if proc is None:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    except OSError:
        pass


def shutdown_children() -> None:
    """Terminate all managed child processes. Called on TUI exit."""
    for name in list(_children):
        _stop_child(name)


# Register as a safety net — TUI also calls this explicitly
atexit.register(shutdown_children)


def _venv_python() -> str:
    """Return the path to the virtualenv Python, or sys.executable."""
    if sys.platform == "win32":
        candidate = os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:
        candidate = os.path.join(VENV_DIR, "bin", "python")
    return candidate if os.path.exists(candidate) else sys.executable


def _kill_port(port: int | str) -> bool:
    """Kill process on a port. Cross-platform."""
    port = str(port)
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid.isdigit():
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True, timeout=5,
                        )
            return True
        else:
            result = subprocess.run(
                ["lsof", f"-ti:{port}"],
                capture_output=True, text=True, timeout=5,
            )
            if result.stdout.strip():
                for pid in result.stdout.strip().split():
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
            return True
    except Exception:
        return False


def _api_get(path: str) -> str | None:
    """Quick API GET, return raw JSON string or None."""
    import urllib.request
    try:
        req = urllib.request.Request(
            f"{API_BASE}{path}", headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode()
    except Exception:
        return None


def _api_post(path: str) -> str | None:
    """Quick API POST, return raw JSON string or None."""
    import urllib.request
    try:
        req = urllib.request.Request(
            f"{API_BASE}{path}",
            data=b"{}",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode()
    except Exception:
        return None


def _start_backend() -> str:
    """Start the backend as a managed child process."""
    python = _venv_python()
    _spawn(
        "backend",
        [python, "-m", "uvicorn", "backend.api.app:app",
         "--host", "0.0.0.0", "--port", BACKEND_PORT, "--reload"],
        cwd=_project_root,
        log_path=os.path.join(_project_root, "backend.log"),
    )
    return f"Backend starting (port {BACKEND_PORT})"


def _start_frontend() -> str:
    """Start the frontend as a managed child process."""
    npm_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    fe_dir = os.path.join(_project_root, "frontend")
    if not os.path.isdir(fe_dir):
        return "Frontend directory not found — skipped"

    _spawn(
        "frontend",
        [npm_cmd, "vite"],
        cwd=fe_dir,
        log_path=os.path.join(_project_root, "frontend.log"),
    )
    return "Frontend starting (port 5173)"


# ── Actions ──────────────────────────────────────────────────────────

def action_resume_hut() -> tuple[str, str]:
    """Restart backend + frontend."""
    lines = ["RESUME — HUT!", ""]

    # Kill any external processes on those ports first
    _kill_port(BACKEND_PORT)
    _kill_port(5173)

    lines.append(_start_backend())
    lines.append(_start_frontend())

    # Wait for backend
    for _ in range(10):
        if _api_get("/api/v1/shows") is not None:
            lines.append("[green]Backend is set[/]")
            break
        time.sleep(1)
    else:
        lines.append("[yellow]Backend still starting...[/]")

    lines.append("")
    lines.append("Services resumed.")
    return "Resume Hut", "\n".join(lines)


def action_heartbeat() -> tuple[str, str]:
    """Ping the backend heartbeat endpoint."""
    result = _api_post("/api/v1/heartbeat")
    if result:
        try:
            formatted = json.dumps(json.loads(result), indent=2)
            return "Heartbeat", formatted
        except json.JSONDecodeError:
            return "Heartbeat", result
    return "Heartbeat", "[red]Backend unreachable[/]"


def action_run_tests() -> tuple[str, str]:
    """Run the backend test suite."""
    python = _venv_python()
    try:
        result = subprocess.run(
            [python, "-m", "pytest", "backend/tests/", "-v", "--tb=short"],
            capture_output=True, text=True, timeout=600, cwd=_project_root,
        )
        output = result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout
        if result.stderr:
            output += "\n" + result.stderr[-1000:]
        return "Run-Through (Tests)", output
    except subprocess.TimeoutExpired:
        return "Run-Through (Tests)", "[red]Tests timed out after 10 minutes[/]"
    except Exception as e:
        return "Run-Through (Tests)", f"[red]Error: {e}[/]"


def action_restart_backend() -> tuple[str, str]:
    """Restart only the backend."""
    _kill_port(BACKEND_PORT)
    time.sleep(1)

    lines = [_start_backend()]

    time.sleep(2)
    if _api_get("/api/v1/shows") is not None:
        lines.append(f"[green]Backend is set (port {BACKEND_PORT})[/]")
    else:
        lines.append(f"[yellow]Backend restarting on port {BACKEND_PORT}...[/]")
    return "Restart Backend", "\n".join(lines)


def action_restart_frontend() -> tuple[str, str]:
    """Restart only the frontend."""
    _kill_port(5173)
    time.sleep(1)
    return "Restart Frontend", _start_frontend()


def action_migrate() -> tuple[str, str]:
    """Run alembic migrations."""
    python = _venv_python()
    try:
        result = subprocess.run(
            [python, "-m", "alembic", "upgrade", "head"],
            capture_output=True, text=True, timeout=60, cwd=_project_root,
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        if result.returncode == 0:
            output += "\n[green]Migration complete[/]"
        else:
            output += "\n[red]Migration failed[/]"
        return "Run Migration", output
    except Exception as e:
        return "Run Migration", f"[red]Error: {e}[/]"


def action_check_step() -> tuple[str, str]:
    """Show service status."""
    lines = ["CHECK STEP", ""]

    be_up = _api_get("/api/v1/shows") is not None
    lines.append(f"  Backend:   {'[green]ON[/]' if be_up else '[red]OFF[/]'}  (port {BACKEND_PORT})")

    import urllib.request
    fe_up = False
    try:
        urllib.request.urlopen("http://localhost:5173", timeout=2)
        fe_up = True
    except Exception:
        pass
    lines.append(f"  Frontend:  {'[green]ON[/]' if fe_up else '[red]OFF[/]'}  (port 5173)")
    lines.append(f"  Dashboard: [green]ON[/]  (TUI)")

    # Show managed child process status
    for name, proc in _children.items():
        alive = proc.poll() is None
        status = "[green]running[/]" if alive else f"[red]exited ({proc.returncode})[/]"
        lines.append(f"  {name.title()} process: {status}  (pid {proc.pid})")

    if be_up:
        lines.append("")
        shows_raw = _api_get("/api/v1/shows")
        if shows_raw:
            try:
                shows = json.loads(shows_raw)
                lines.append(f"  Shows: [cyan]{len(shows)}[/]")
            except json.JSONDecodeError:
                pass

        agents_raw = _api_get("/api/v1/system/agents")
        if agents_raw:
            try:
                agents = json.loads(agents_raw)
                active = sum(1 for a in agents if a.get("status") == "active")
                lines.append(f"  Active agents: [green]{active}[/]")
            except json.JSONDecodeError:
                pass

    return "Check Step", "\n".join(lines)


def action_parade_rest() -> tuple[str, str]:
    """Stop all services."""
    shutdown_children()
    _kill_port(BACKEND_PORT)
    _kill_port(5173)
    return "Parade Rest", "[green]Services stopped.[/]"


def action_open_browser() -> tuple[str, str]:
    """Open the frontend in the default browser."""
    try:
        webbrowser.open("http://localhost:5173")
        return "Open Browser", "Opened http://localhost:5173"
    except Exception as e:
        return "Open Browser", f"[red]Cannot open browser: {e}[/]"


# ── Dispatcher ───────────────────────────────────────────────────────

_ACTIONS = {
    "resume-hut": action_resume_hut,
    "heartbeat": action_heartbeat,
    "run-tests": action_run_tests,
    "restart-backend": action_restart_backend,
    "restart-frontend": action_restart_frontend,
    "migrate": action_migrate,
    "check-step": action_check_step,
    "parade-rest": action_parade_rest,
    "open-browser": action_open_browser,
}


def run_action(name: str) -> tuple[str, str]:
    """Run a named action and return (title, output)."""
    action_fn = _ACTIONS.get(name)
    if action_fn is None:
        return "Unknown Action", f"[red]Unknown action: {name}[/]"
    try:
        return action_fn()
    except Exception as e:
        return name.replace("-", " ").title(), f"[red]Error: {e}[/]"
