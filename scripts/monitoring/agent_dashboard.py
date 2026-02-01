#!/usr/bin/env python3
"""Pane 2: Active Agents — who's on the field right now."""

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

STATUS_ICON = {
    "active": f"{GREEN}●{RESET}",
    "completed": f"{BLUE}○{RESET}",
    "failed": f"{RED}✗{RESET}",
    "timed_out": f"{MAGENTA}⏱{RESET}",
    "initializing": f"{YELLOW}◌{RESET}",
    "pending": f"{YELLOW}◌{RESET}",
    "in_progress": f"{CYAN}◑{RESET}",
}

API_BASE = os.environ.get("DCI_API_URL", "http://localhost:8000")


def fetch(path):
    try:
        req = urllib.request.Request(f"{API_BASE}{path}", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def render():
    clear()
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{GREEN}ACTIVE AGENTS{RESET}  {DIM}{now}{RESET}")
    print()

    shows = fetch("/api/v1/shows") or []
    active_shows = [s for s in shows if s.get("status") == "active" and s.get("corps_id")]

    if not active_shows:
        print(f"  {DIM}No active corps.{RESET}")
        print(f"  {DIM}Create and activate a show to{RESET}")
        print(f"  {DIM}bring agents on the field.{RESET}")
        return

    for show in active_shows:
        corps_id = show["corps_id"]
        title = show.get("title", "Untitled")
        roster = fetch(f"/api/v1/corps/{corps_id}/roster") or []

        if not roster:
            print(f"  {DIM}{title}: no agents spawned{RESET}")
            continue

        # Group by status
        by_status = {}
        for agent in roster:
            s = agent.get("status", "unknown")
            by_status.setdefault(s, []).append(agent)

        # Summary bar
        counts = {s: len(agents) for s, agents in by_status.items()}
        parts = []
        for s in ["active", "in_progress", "pending", "completed", "failed", "timed_out"]:
            if s in counts:
                icon = STATUS_ICON.get(s, "?")
                parts.append(f"{icon} {counts[s]} {s}")
        print(f"  {' '.join(parts)}")
        print()

        # Show active/in-progress agents with role hierarchy
        live_agents = by_status.get("active", []) + by_status.get("in_progress", [])

        # Build parent-child tree
        by_parent = {}
        agent_map = {a["id"]: a for a in roster}
        for a in roster:
            pid = a.get("parent_session_id")
            by_parent.setdefault(pid, []).append(a)

        # Render tree from roots
        roots = by_parent.get(None, [])
        for root in roots:
            _render_agent_tree(root, agent_map, by_parent, depth=0)


def _render_agent_tree(agent, agent_map, by_parent, depth):
    indent = "  " + "  │ " * depth
    role = agent.get("role", "?").replace("_", " ").title()
    status = agent.get("status", "?")
    icon = STATUS_ICON.get(status, "?")

    # Only show active tree branches (skip completed subtrees)
    children = by_parent.get(agent["id"], [])
    has_active = status in ("active", "in_progress", "initializing", "pending")
    has_active_child = any(
        c.get("status") in ("active", "in_progress", "initializing", "pending")
        for c in children
    )

    if not has_active and not has_active_child:
        return

    connector = "├─" if depth > 0 else "  "
    print(f"{indent}{connector}{icon} {role}")

    for child in children:
        _render_agent_tree(child, agent_map, by_parent, depth + 1)


def _self_mtime():
    try:
        return os.path.getmtime(__file__)
    except OSError:
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", type=int, default=2)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

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
