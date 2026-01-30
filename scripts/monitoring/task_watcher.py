#!/usr/bin/env python3
"""DCI Swarm — Real-time task/agent status watcher for TMUX dashboard pane.

Polls the backend API and displays color-coded agent status with DCI terminology.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime

# ANSI color codes
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

# Status display config
STATUS_DISPLAY = {
    "active": (GREEN, "ACTIVE"),
    "completed": (BLUE, "DONE"),
    "failed": (RED, "FAILED"),
    "timed_out": (MAGENTA, "TIMEOUT"),
    "draft": (DIM, "DRAFT"),
    "rehearsal": (CYAN, "REHEARSAL"),
    "tour": (GREEN, "ON TOUR"),
    "disbanded": (RED, "DISBANDED"),
    "initializing": (YELLOW, "INIT"),
    "pending": (YELLOW, "PENDING"),
    "in_progress": (CYAN, "IN PROGRESS"),
    "review": (MAGENTA, "REVIEW"),
    "blocked": (RED, "BLOCKED"),
}

API_BASE = os.environ.get("DCI_API_URL", "http://localhost:8000")


def fetch(path: str):
    """Fetch JSON from backend API."""
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


def status_str(status: str) -> str:
    color, label = STATUS_DISPLAY.get(status, (DIM, status.upper()))
    return f"{color}{label}{RESET}"


def render_header():
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{CYAN}DCI SWARM — Agent Status{RESET}  {DIM}{now}{RESET}")
    print(f"{DIM}{'─' * 56}{RESET}")


def render_shows(shows: list):
    if not shows:
        print(f"\n  {DIM}No shows found.{RESET}")
        return

    print(f"\n  {BOLD}SHOWS{RESET}")
    for show in shows:
        sid = show.get("id", "?")[:8]
        title = show.get("title", "Untitled")
        status = show.get("status", "unknown")
        corps_id = show.get("corps_id")
        corps_tag = f"  {DIM}corps:{corps_id[:8]}{RESET}" if corps_id else ""
        print(f"    {DIM}{sid}{RESET}  {title:30s}  {status_str(status)}{corps_tag}")


def render_roster(corps_id: str):
    roster = fetch(f"/api/corps/{corps_id}/roster")
    if not roster:
        return

    # Count by status
    counts = {}
    for agent in roster:
        s = agent.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1

    print(f"\n  {BOLD}ROSTER{RESET}  {DIM}({len(roster)} agents){RESET}")
    for status, count in sorted(counts.items()):
        bar = "█" * min(count, 30)
        print(f"    {status_str(status):30s}  {count:3d}  {GREEN}{bar}{RESET}")

    # Show hierarchy (top-level roles)
    top_roles = [a for a in roster if not a.get("parent_session_id")]
    if top_roles:
        print(f"\n  {BOLD}CHAIN OF COMMAND{RESET}")
        for agent in top_roles[:10]:
            role = agent.get("role", "?").replace("_", " ").title()
            status = agent.get("status", "?")
            print(f"    {role:30s}  {status_str(status)}")


def render_corps_info(corps_id: str):
    corps = fetch(f"/api/corps/{corps_id}")
    if not corps:
        return

    name = corps.get("name", "Unknown")
    status = corps.get("status", "unknown")
    tour = corps.get("tour_mode", False)
    mode = corps.get("rehearsal_mode")

    print(f"\n  {BOLD}CORPS: {name}{RESET}")
    print(f"    Status:    {status_str(status)}")
    print(f"    Tour mode: {GREEN}ON{RESET}" if tour else f"    Tour mode: {DIM}OFF{RESET}")
    if mode:
        print(f"    Rehearsal: {CYAN}{mode}{RESET}")


def render_summary_bar(shows: list):
    total = len(shows)
    active = sum(1 for s in shows if s.get("status") == "active")
    draft = sum(1 for s in shows if s.get("status") == "draft")
    done = sum(1 for s in shows if s.get("status") == "completed")

    print(f"\n  {DIM}Shows: {total}  "
          f"{GREEN}Active: {active}{DIM}  "
          f"{YELLOW}Draft: {draft}{DIM}  "
          f"{BLUE}Done: {done}{RESET}")


def render(shows: list):
    clear_screen()
    render_header()
    render_shows(shows)
    render_summary_bar(shows)

    # If there's an active show with a corps, show corps details
    for show in shows:
        corps_id = show.get("corps_id")
        if corps_id and show.get("status") == "active":
            render_corps_info(corps_id)
            render_roster(corps_id)
            break


def main():
    parser = argparse.ArgumentParser(description="DCI Swarm task watcher")
    parser.add_argument("--refresh", type=int, default=2, help="Refresh interval in seconds")
    parser.add_argument("--once", action="store_true", help="Display once and exit")
    args = parser.parse_args()

    while True:
        shows = fetch("/api/shows") or []
        render(shows)

        if args.once:
            break

        try:
            time.sleep(args.refresh)
        except KeyboardInterrupt:
            print(f"\n{DIM}Stopped.{RESET}")
            break


if __name__ == "__main__":
    main()
