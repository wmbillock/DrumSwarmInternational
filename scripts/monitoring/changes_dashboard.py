#!/usr/bin/env python3
"""Pane 4: Changes & Tasks — pending file changes and completed work."""

import argparse
import json
import os
import subprocess
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

API_BASE = os.environ.get("DCI_API_URL", "http://localhost:4224")
PROJECT_ROOT = os.environ.get("DCI_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

GIT_STATUS_ICON = {
    "M": f"{YELLOW}~{RESET}",  # modified
    "A": f"{GREEN}+{RESET}",   # added
    "D": f"{RED}-{RESET}",     # deleted
    "R": f"{BLUE}>{RESET}",    # renamed
    "?": f"{DIM}?{RESET}",     # untracked
}


def fetch(path):
    try:
        req = urllib.request.Request(f"{API_BASE}{path}", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def git_status():
    """Get git status as structured data."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "-u"],
            capture_output=True, text=True, timeout=5,
            cwd=PROJECT_ROOT,
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


def git_recent_commits(n=5):
    """Get recent commit subjects."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--pretty=format:%h %s"],
            capture_output=True, text=True, timeout=5,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            return []
        return result.stdout.strip().splitlines()
    except Exception:
        return []


def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def render():
    clear()
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{BOLD}{MAGENTA}CHANGES & TASKS{RESET}  {DIM}{now}{RESET}")
    print()

    # Pending file changes
    changes = git_status()
    staged = [f for f in changes if f["staged"]]
    unstaged = [f for f in changes if not f["staged"]]

    if not changes:
        print(f"  {GREEN}Working tree clean{RESET}")
    else:
        print(f"  {BOLD}PENDING{RESET}  {len(changes)} file(s)")
        if staged:
            print(f"  {GREEN}Staged:{RESET}")
            for f in staged[:8]:
                icon = GIT_STATUS_ICON.get(f["status"], "?")
                path = f["path"]
                # Shorten long paths
                if len(path) > 40:
                    path = "..." + path[-37:]
                print(f"    {icon} {path}")
            if len(staged) > 8:
                print(f"    {DIM}... +{len(staged) - 8} more{RESET}")

        if unstaged:
            print(f"  {YELLOW}Unstaged:{RESET}")
            for f in unstaged[:8]:
                icon = GIT_STATUS_ICON.get(f["status"], "?")
                path = f["path"]
                if len(path) > 40:
                    path = "..." + path[-37:]
                print(f"    {icon} {path}")
            if len(unstaged) > 8:
                print(f"    {DIM}... +{len(unstaged) - 8} more{RESET}")

    print()
    print(f"{DIM}{'─' * 36}{RESET}")
    print()

    # Recent commits
    commits = git_recent_commits(6)
    if commits:
        print(f"  {BOLD}RECENT COMMITS{RESET}")
        for c in commits:
            hash_part = c[:7]
            msg = c[8:] if len(c) > 8 else ""
            if len(msg) > 35:
                msg = msg[:32] + "..."
            print(f"  {DIM}{hash_part}{RESET} {msg}")
    else:
        print(f"  {DIM}No git history.{RESET}")

    print()
    print(f"{DIM}{'─' * 36}{RESET}")
    print()

    # Completed tasks from API (reps)
    shows = fetch("/api/v1/shows") or []
    active = [s for s in shows if s.get("status") == "active"]

    if active:
        print(f"  {BOLD}COMPLETED REPS{RESET}")
        found = False
        for show in active[:2]:
            coord_root = show.get("segment_root_id")
            if not coord_root:
                continue
            reps = fetch(f"/api/v1/segments/{coord_root}/reps") or []
            completed = [r for r in reps if r.get("status") == "completed"]
            failed = [r for r in reps if r.get("status") == "failed"]
            pending = [r for r in reps if r.get("status") in ("pending", "assigned", "in_progress")]

            if reps:
                found = True
                print(f"  {GREEN}{len(completed)} done{RESET}  "
                      f"{CYAN}{len(pending)} wip{RESET}  "
                      f"{RED}{len(failed)} fail{RESET}")
        if not found:
            print(f"  {DIM}No reps yet.{RESET}")
    else:
        print(f"  {DIM}No active shows.{RESET}")


def _self_mtime():
    try:
        return os.path.getmtime(__file__)
    except OSError:
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", type=int, default=5)
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
