#!/usr/bin/env python3
"""DCI Swarm — Corps activity feed watcher for TMUX dashboard pane.

Monitors active corps: rep status, messages, scores, metronome events.
"""

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

API_BASE = os.environ.get("DCI_API_URL", "http://localhost:8000")

REP_STATUS_ICON = {
    "pending": f"{YELLOW}○{RESET}",
    "assigned": f"{CYAN}◐{RESET}",
    "in_progress": f"{CYAN}◑{RESET}",
    "review": f"{MAGENTA}◕{RESET}",
    "completed": f"{GREEN}●{RESET}",
    "failed": f"{RED}✗{RESET}",
}

MSG_TYPE_ICON = {
    "handoff": f"{CYAN}→{RESET}",
    "escalation": f"{RED}↑{RESET}",
    "flag": f"{YELLOW}⚑{RESET}",
    "status": f"{DIM}•{RESET}",
    "directive": f"{MAGENTA}▶{RESET}",
    "feedback": f"{GREEN}◀{RESET}",
}


def fetch(path: str):
    try:
        url = f"{API_BASE}{path}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def render_header():
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{MAGENTA}DCI SWARM — Corps Activity{RESET}  {DIM}{now}{RESET}")
    print(f"{DIM}{'─' * 56}{RESET}")


def render_messages(corps_id: str, limit: int = 15):
    msgs = fetch(f"/api/corps/{corps_id}/messages")
    if not msgs:
        print(f"\n  {DIM}No messages.{RESET}")
        return

    print(f"\n  {BOLD}RECENT MESSAGES{RESET}  {DIM}({len(msgs)} total){RESET}")
    for msg in msgs[:limit]:
        icon = MSG_TYPE_ICON.get(msg.get("type", ""), "?")
        from_role = msg.get("from_role", "?").replace("_", " ")
        to_role = msg.get("to_role", "")
        subject = msg.get("subject", "")[:40]
        priority = msg.get("priority", "normal")

        priority_color = {
            "critical": RED, "high": YELLOW, "normal": DIM, "low": DIM
        }.get(priority, DIM)

        to_str = f" → {to_role.replace('_', ' ')}" if to_role else ""
        print(f"    {icon}  {priority_color}{priority:8s}{RESET}  "
              f"{from_role}{to_str}  {DIM}{subject}{RESET}")


def render_coordinate_tree(coord_id: str, depth: int = 0, max_depth: int = 3):
    if depth > max_depth:
        return

    coord = fetch(f"/api/coordinates/{coord_id}")
    if not coord:
        return

    indent = "  " * (depth + 2)
    icon = REP_STATUS_ICON.get(coord.get("status", ""), "?")
    title = coord.get("title", "?")[:30]
    ctype = coord.get("type", "?")
    print(f"{indent}{icon}  {DIM}{ctype:10s}{RESET}  {title}")

    children = fetch(f"/api/coordinates/{coord_id}/children") or []
    for child in children[:10]:
        render_coordinate_tree(child["id"], depth + 1, max_depth)


def render_active_corps():
    shows = fetch("/api/shows") or []
    active = [s for s in shows if s.get("status") == "active" and s.get("corps_id")]

    if not active:
        print(f"\n  {DIM}No active corps. Create and activate a show.{RESET}")
        return

    for show in active[:3]:
        corps_id = show["corps_id"]
        title = show.get("title", "Untitled")
        coord_root = show.get("coordinate_root_id")

        print(f"\n  {BOLD}SHOW: {title}{RESET}  {DIM}corps:{corps_id[:8]}{RESET}")

        # Coordinate tree
        if coord_root:
            print(f"\n  {BOLD}COORDINATE TREE{RESET}")
            render_coordinate_tree(coord_root)

        # Messages
        render_messages(corps_id)


def render(args):
    clear_screen()
    render_header()
    render_active_corps()


def main():
    parser = argparse.ArgumentParser(description="DCI Swarm corps watcher")
    parser.add_argument("--refresh", type=int, default=3, help="Refresh interval")
    parser.add_argument("--once", action="store_true", help="Display once and exit")
    args = parser.parse_args()

    while True:
        render(args)

        if args.once:
            break

        try:
            time.sleep(args.refresh)
        except KeyboardInterrupt:
            print(f"\n{DIM}Stopped.{RESET}")
            break


if __name__ == "__main__":
    main()
