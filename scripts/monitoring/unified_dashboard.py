#!/usr/bin/env python3
"""Unified right-pane dashboard — switchable between views.

Reads a view selector file to know which view to show.
Views: metrics, agents, logs, changes

Switch views by writing to the selector file (done via tmux keybindings).
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BG_DIM = "\033[48;5;236m"

BACKEND_PORT = os.environ.get("DCI_PORT", "8000")
API_BASE = os.environ.get("DCI_API_URL", f"http://localhost:{BACKEND_PORT}")
PROJECT_ROOT = os.environ.get("DCI_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
LOG_FILE = os.path.join(PROJECT_ROOT, "backend.log")

VIEWS = ["metrics", "agents", "logs", "changes", "memory", "lifecycle"]
VIEW_FILE = os.path.join(PROJECT_ROOT, ".dci-dashboard-view")

STATUS_ICON = {
    "active": f"{GREEN}\u25cf{RESET}",
    "completed": f"{BLUE}\u25cb{RESET}",
    "failed": f"{RED}\u2717{RESET}",
    "timed_out": f"{MAGENTA}\u23f1{RESET}",
    "initializing": f"{YELLOW}\u25cc{RESET}",
    "pending": f"{YELLOW}\u25cc{RESET}",
    "in_progress": f"{CYAN}\u25d1{RESET}",
}

GIT_STATUS_ICON = {
    "M": f"{YELLOW}~{RESET}",
    "A": f"{GREEN}+{RESET}",
    "D": f"{RED}-{RESET}",
    "R": f"{BLUE}>{RESET}",
    "?": f"{DIM}?{RESET}",
}


def fetch(path):
    try:
        req = urllib.request.Request(f"{API_BASE}{path}", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def backend_up():
    return fetch("/api/v1/shows") is not None


def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def get_current_view():
    try:
        return Path(VIEW_FILE).read_text().strip()
    except Exception:
        return "metrics"


def set_view(view):
    Path(VIEW_FILE).write_text(view)


# --- Tab bar shown at top of every view ---

def render_tab_bar(active_view):
    tabs = []
    for i, v in enumerate(VIEWS):
        key = str(i + 1)
        label = v.capitalize()
        if v == active_view:
            tabs.append(f"{BG_DIM}{BOLD}{WHITE} {key}:{label} {RESET}")
        else:
            tabs.append(f"{DIM} {key}:{label} {RESET}")
    print("".join(tabs))
    print(f"{DIM}{'─' * 50}{RESET}")


# --- View: Metrics ---

def render_metrics():
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{CYAN}DCI SWARM{RESET}  {DIM}{now}{RESET}")
    print()

    be_up = backend_up()
    fe_check = False
    try:
        urllib.request.urlopen("http://localhost:5173", timeout=2)
        fe_check = True
    except Exception:
        pass

    print(f"  Backend   {GREEN}ON{RESET}" if be_up else f"  Backend   {RED}OFF{RESET}")
    print(f"  Frontend  {GREEN}ON{RESET}" if fe_check else f"  Frontend  {RED}OFF{RESET}")
    print()

    if not be_up:
        print(f"  {DIM}Backend offline. Run: ./dci forward-march{RESET}")
        _render_quick_ref()
        return

    shows = fetch("/api/v1/shows") or []
    total = len(shows)
    active = sum(1 for s in shows if s.get("status") == "active")
    draft = sum(1 for s in shows if s.get("status") == "draft")
    done = sum(1 for s in shows if s.get("status") == "completed")

    print(f"  {BOLD}SHOWS{RESET}  {total} total")
    print(f"  {GREEN}Active: {active}{RESET}  {YELLOW}Draft: {draft}{RESET}  {BLUE}Done: {done}{RESET}")

    for show in shows:
        if show.get("status") != "active" or not show.get("corps_id"):
            continue
        corps_id = show["corps_id"]
        corps = fetch(f"/api/v1/corps/{corps_id}")
        if not corps:
            continue
        print()
        print(f"  {BOLD}{corps.get('name', '?')}{RESET}")
        roster = fetch(f"/api/v1/corps/{corps_id}/roster") or []
        if roster:
            active_agents = sum(1 for a in roster if a.get("status") == "active")
            print(f"  Agents: {GREEN}{active_agents}{RESET}/{len(roster)}")

    print()
    _render_quick_ref()


def _render_quick_ref():
    print(f"{DIM}{'─' * 50}{RESET}")
    print()
    print(f"  {BOLD}COMMANDS{RESET}")
    cmds = [
        ("ten-hut", "Start all"), ("parade-rest", "Stop all"),
        ("resume-hut", "Restart services"), ("forward-march", "Backend only"),
        ("company-front", "Frontend only"), ("run-through", "Tests"),
        ("drill -p N", "Euler drill"), ("check-step", "Status"),
    ]
    for cmd, desc in cmds:
        print(f"  {GREEN}{cmd:<16}{RESET}{DIM}{desc}{RESET}")
    print()
    print(f"  {BOLD}URLS{RESET}")
    print(f"  Frontend  {CYAN}http://localhost:5173{RESET}")
    print(f"  Backend   {CYAN}{API_BASE}{RESET}")


# --- View: Agents ---

def render_agents():
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{GREEN}AGENTS{RESET}  {DIM}{now}{RESET}")
    print()

    shows = fetch("/api/v1/shows") or []
    active_shows = [s for s in shows if s.get("status") == "active" and s.get("corps_id")]

    if not active_shows:
        print(f"  {DIM}No active corps. Create and activate a show.{RESET}")
        return

    for show in active_shows:
        corps_id = show["corps_id"]
        title = show.get("title", "Untitled")
        roster = fetch(f"/api/v1/corps/{corps_id}/roster") or []

        if not roster:
            print(f"  {DIM}{title}: no agents{RESET}")
            continue

        by_status = {}
        for agent in roster:
            s = agent.get("status", "unknown")
            by_status.setdefault(s, []).append(agent)

        counts = {s: len(agents) for s, agents in by_status.items()}
        parts = []
        for s in ["active", "completed", "failed"]:
            if s in counts:
                icon = STATUS_ICON.get(s, "?")
                parts.append(f"{icon} {counts[s]}")
        print(f"  {BOLD}{title}{RESET}  {' '.join(parts)}")
        print()

        # Tree
        by_parent = {}
        for a in roster:
            pid = a.get("parent_session_id")
            by_parent.setdefault(pid, []).append(a)

        roots = by_parent.get(None, [])
        for root in roots:
            _render_agent_tree(root, by_parent, depth=0)
        print()


def _render_agent_tree(agent, by_parent, depth):
    indent = "  " + "  " * depth
    role = agent.get("role", "?").replace("_", " ").title()
    status = agent.get("status", "?")
    icon = STATUS_ICON.get(status, "?")
    connector = "\u251c\u2500" if depth > 0 else ""
    print(f"{indent}{connector}{icon} {role}")

    children = by_parent.get(agent["id"], [])
    for child in children:
        _render_agent_tree(child, by_parent, depth + 1)


# --- View: Logs ---

def render_logs():
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{YELLOW}LOGS{RESET}  {DIM}{now}{RESET}")
    print()

    if not os.path.exists(LOG_FILE):
        print(f"  {DIM}No log file at {LOG_FILE}{RESET}")
        return

    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        # Show last N lines that fit
        recent = lines[-40:] if len(lines) > 40 else lines
        for line in recent:
            line = line.rstrip()
            if not line:
                continue
            # Color by log level
            if "ERROR" in line or "error" in line.lower():
                print(f"  {RED}{line[:100]}{RESET}")
            elif "WARNING" in line or "warn" in line.lower():
                print(f"  {YELLOW}{line[:100]}{RESET}")
            elif "INFO" in line:
                label = "BE"
                if "GET " in line or "POST " in line:
                    # HTTP request log — compact
                    parts = line.split('"')
                    if len(parts) >= 2:
                        method_path = parts[1][:60]
                        status = parts[2].strip()[:3] if len(parts) > 2 else ""
                        color = GREEN if status.startswith("2") else RED
                        print(f"  {DIM}{label}{RESET} {color}{status}{RESET} {method_path}")
                        continue
                print(f"  {DIM}{line[:100]}{RESET}")
            else:
                print(f"  {DIM}{line[:100]}{RESET}")
    except Exception as e:
        print(f"  {RED}Error reading logs: {e}{RESET}")


# --- View: Changes ---

def render_changes():
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{MAGENTA}CHANGES{RESET}  {DIM}{now}{RESET}")
    print()

    # Git status
    changes = _git_status()
    staged = [f for f in changes if f["staged"]]
    unstaged = [f for f in changes if not f["staged"]]

    if not changes:
        print(f"  {GREEN}Working tree clean{RESET}")
    else:
        print(f"  {BOLD}{len(changes)} file(s) changed{RESET}")
        if staged:
            print(f"  {GREEN}Staged:{RESET}")
            for f in staged[:10]:
                icon = GIT_STATUS_ICON.get(f["status"], "?")
                path = f["path"] if len(f["path"]) <= 45 else "..." + f["path"][-42:]
                print(f"    {icon} {path}")
            if len(staged) > 10:
                print(f"    {DIM}... +{len(staged) - 10} more{RESET}")
        if unstaged:
            print(f"  {YELLOW}Unstaged:{RESET}")
            for f in unstaged[:10]:
                icon = GIT_STATUS_ICON.get(f["status"], "?")
                path = f["path"] if len(f["path"]) <= 45 else "..." + f["path"][-42:]
                print(f"    {icon} {path}")
            if len(unstaged) > 10:
                print(f"    {DIM}... +{len(unstaged) - 10} more{RESET}")

    print()
    print(f"{DIM}{'─' * 50}{RESET}")
    print()

    # Recent commits
    commits = _git_recent_commits(8)
    if commits:
        print(f"  {BOLD}RECENT COMMITS{RESET}")
        for c in commits:
            h = c[:7]
            msg = c[8:][:45] if len(c) > 8 else ""
            print(f"  {DIM}{h}{RESET} {msg}")
    print()

    print(f"{DIM}{'─' * 50}{RESET}")
    print()

    # Completed reps
    shows = fetch("/api/v1/shows") or []
    active = [s for s in shows if s.get("status") == "active"]
    print(f"  {BOLD}COMPLETED REPS{RESET}")
    found = False
    for show in active[:3]:
        coord_root = show.get("segment_root_id")
        if not coord_root:
            continue
        reps = fetch(f"/api/v1/segments/{coord_root}/reps") or []
        if reps:
            found = True
            completed = sum(1 for r in reps if r.get("status") == "completed")
            failed = sum(1 for r in reps if r.get("status") == "failed")
            pending = sum(1 for r in reps if r.get("status") in ("pending", "assigned", "in_progress"))
            print(f"  {GREEN}{completed} done{RESET}  {CYAN}{pending} wip{RESET}  {RED}{failed} fail{RESET}")
    if not found:
        print(f"  {DIM}No reps yet.{RESET}")


def _git_status():
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "-u"],
            capture_output=True, text=True, timeout=5, cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            return []
        files = []
        for line in result.stdout.strip().splitlines():
            if len(line) < 4:
                continue
            index_status = line[0].strip()
            work_status = line[1].strip()
            filepath = line[3:]
            status = work_status or index_status or "?"
            staged = index_status not in ("?", " ", "")
            files.append({"status": status, "path": filepath, "staged": staged})
        return files
    except Exception:
        return []


def _git_recent_commits(n=5):
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--pretty=format:%h %s"],
            capture_output=True, text=True, timeout=5, cwd=PROJECT_ROOT,
        )
        return result.stdout.strip().splitlines() if result.returncode == 0 else []
    except Exception:
        return []


# --- View: Memory ---

def render_memory():
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{BLUE}MEMORY{RESET}  {DIM}{now}{RESET}")
    print()

    if not backend_up():
        print(f"  {DIM}Backend offline.{RESET}")
        return

    shows = fetch("/api/v1/shows") or []
    active_shows = [s for s in shows if s.get("status") == "active" and s.get("corps_id")]

    if not active_shows:
        print(f"  {DIM}No active corps.{RESET}")
        return

    for show in active_shows[:3]:
        corps_id = show["corps_id"]
        roster = fetch(f"/api/v1/corps/{corps_id}/roster") or []
        title = show.get("title", "Untitled")
        print(f"  {BOLD}{title}{RESET}")

        for agent in roster[:8]:
            identity = agent.get("nickname") or agent.get("role", "?")
            stats = fetch(f"/api/v1/agents/{identity}/memory-stats")
            if not stats:
                continue
            total = stats.get("total_memories", 0)
            tasks = stats.get("task_memories", 0)
            avg_conf = stats.get("avg_confidence", 0)
            by_type = stats.get("by_type", {})

            parts = []
            for mt, count in sorted(by_type.items()):
                parts.append(f"{mt}:{count}")
            type_str = " ".join(parts) if parts else "none"

            role = agent.get("role", "?").replace("_", " ").title()[:18]
            print(f"    {role:<20} {GREEN}{total}{RESET} mem  {CYAN}{tasks}{RESET} tasks  conf:{avg_conf:.1f}  ({type_str})")

        print()


# --- View: Lifecycle ---

def render_lifecycle():
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{MAGENTA}LIFECYCLE{RESET}  {DIM}{now}{RESET}")
    print()

    if not backend_up():
        print(f"  {DIM}Backend offline.{RESET}")
        return

    shows = fetch("/api/v1/shows") or []
    active_shows = [s for s in shows if s.get("status") == "active" and s.get("corps_id")]

    if not active_shows:
        print(f"  {DIM}No active corps.{RESET}")
        return

    for show in active_shows[:3]:
        corps_id = show["corps_id"]
        corps = fetch(f"/api/v1/corps/{corps_id}")
        if not corps:
            continue

        title = show.get("title", "Untitled")
        mascot = corps.get("mascot", "—")
        theme = corps.get("theme_id", "—")
        print(f"  {BOLD}{title}{RESET}  {DIM}({mascot} / {theme}){RESET}")
        print()

        # Ageouts
        ageouts = fetch(f"/api/v1/corps/{corps_id}/ageouts") or []
        if ageouts:
            print(f"  {YELLOW}Pending Ageouts: {len(ageouts)}{RESET}")
            for a in ageouts[:5]:
                print(f"    {a.get('name', '?')} — age {a.get('age', '?')}")
        else:
            print(f"  {GREEN}No pending ageouts{RESET}")

        print()

        # Roster classification breakdown
        roster = fetch(f"/api/v1/corps/{corps_id}/roster") or []
        if roster:
            by_class = {}
            for agent in roster:
                cls = agent.get("classification", "unknown")
                by_class.setdefault(cls, []).append(agent)

            print(f"  {BOLD}Classification Breakdown{RESET}")
            class_icons = {
                "performing_member": f"{YELLOW}\u266b{RESET}",
                "instructional_staff": f"{BLUE}\u2691{RESET}",
                "administrative_staff": f"{MAGENTA}\u2605{RESET}",
                "logistics": f"{GREEN}\u2699{RESET}",
                "dci_assigned": f"{DIM}\u2696{RESET}",
            }
            for cls in ["administrative_staff", "instructional_staff", "performing_member", "logistics", "dci_assigned"]:
                agents = by_class.get(cls, [])
                if agents:
                    icon = class_icons.get(cls, "?")
                    active = sum(1 for a in agents if a.get("status") == "active")
                    label = cls.replace("_", " ").title()
                    print(f"    {icon} {label}: {active}/{len(agents)}")

        print()

        # Self-improvement pending
        pending = fetch("/api/v1/self-improvement/pending") or []
        if pending:
            print(f"  {CYAN}Pending Improvements: {len(pending)}{RESET}")
            for p in pending[:5]:
                print(f"    v{p.get('old_version', '?')}→v{p.get('new_version', '?')}: {p.get('reason', '?')[:40]}")
        print()


# --- Main render dispatch ---

VIEW_RENDERERS = {
    "metrics": render_metrics,
    "agents": render_agents,
    "logs": render_logs,
    "changes": render_changes,
    "memory": render_memory,
    "lifecycle": render_lifecycle,
}


def render():
    clear()
    view = get_current_view()
    if view not in VIEWS:
        view = "metrics"
    render_tab_bar(view)
    renderer = VIEW_RENDERERS.get(view, render_metrics)
    renderer()


def _self_mtime():
    try:
        return os.path.getmtime(__file__)
    except OSError:
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", type=int, default=3)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--view", choices=VIEWS, help="Initial view")
    args = parser.parse_args()

    if args.view:
        set_view(args.view)

    start_mtime = _self_mtime()

    while True:
        try:
            render()
        except Exception as e:
            clear()
            print(f"{RED}Error: {e}{RESET}")

        if args.once:
            break
        try:
            time.sleep(args.refresh)
        except KeyboardInterrupt:
            break

        if _self_mtime() != start_mtime:
            os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == "__main__":
    main()
