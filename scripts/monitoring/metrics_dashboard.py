#!/usr/bin/env python3
"""Pane 1: Metrics & Quick Reference — 90,000-foot view of the swarm."""

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
PROJECT_ROOT = os.environ.get("DCI_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def fetch(path):
    try:
        req = urllib.request.Request(f"{API_BASE}{path}", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def backend_up():
    return fetch("/api/shows") is not None


def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def render():
    clear()
    now = datetime.now().strftime("%H:%M:%S")

    print(f"{BOLD}{CYAN}DRUM SWARM INTERNATIONAL{RESET}")
    print(f"{DIM}{now}{RESET}")
    print()

    # Service status
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
        print(f"  {DIM}Backend offline. Run:{RESET}")
        print(f"  {DIM}./dci forward-march{RESET}")
        print()
        print(f"{DIM}{'─' * 36}{RESET}")
        print()
        print(f"  {BOLD}QUICK REFERENCE{RESET}")
        print()
        print(f"  {GREEN}ten-hut{RESET}        Start all")
        print(f"  {GREEN}parade-rest{RESET}     Stop all")
        print(f"  {GREEN}forward-march{RESET}   Backend only")
        print(f"  {GREEN}company-front{RESET}   Frontend only")
        print(f"  {GREEN}run-through{RESET}     Tests")
        print(f"  {GREEN}check-step{RESET}      Status")
        print()
        print(f"  {BOLD}URLS{RESET}")
        print(f"  Frontend  {CYAN}http://localhost:5173{RESET}")
        print(f"  Backend   {CYAN}{API_BASE}{RESET}")
        return

    # Show summary
    shows = fetch("/api/shows") or []
    total = len(shows)
    active = sum(1 for s in shows if s.get("status") == "active")
    draft = sum(1 for s in shows if s.get("status") == "draft")
    done = sum(1 for s in shows if s.get("status") == "completed")

    print(f"  {BOLD}SHOWS{RESET}  {total} total")
    print(f"  {GREEN}Active: {active}{RESET}  {YELLOW}Draft: {draft}{RESET}  {BLUE}Done: {done}{RESET}")

    # Active corps details
    for show in shows:
        if show.get("status") != "active" or not show.get("corps_id"):
            continue

        corps_id = show["corps_id"]
        corps = fetch(f"/api/corps/{corps_id}")
        if not corps:
            continue

        print()
        print(f"  {BOLD}{corps.get('name', '?')}{RESET}")
        tour = corps.get("tour_mode", False)
        mode = corps.get("rehearsal_mode", "—")
        print(f"  Tour: {GREEN}ON{RESET}" if tour else f"  Tour: {DIM}off{RESET}", end="")
        print(f"  Mode: {CYAN}{mode}{RESET}")

        # Roster counts
        roster = fetch(f"/api/corps/{corps_id}/roster") or []
        if roster:
            active_agents = sum(1 for a in roster if a.get("status") == "active")
            total_agents = len(roster)
            print(f"  Agents: {GREEN}{active_agents}{RESET}/{total_agents}")

        # Rep counts from coordinate tree
        coord_root = show.get("coordinate_root_id")
        if coord_root:
            reps = fetch(f"/api/coordinates/{coord_root}/reps") or []
            if reps:
                completed = sum(1 for r in reps if r.get("status") == "completed")
                failed = sum(1 for r in reps if r.get("status") == "failed")
                in_prog = sum(1 for r in reps if r.get("status") == "in_progress")
                print(f"  Reps: {CYAN}{in_prog} wip{RESET}  {GREEN}{completed} done{RESET}  {RED}{failed} fail{RESET}")

    print()
    print(f"{DIM}{'─' * 36}{RESET}")
    print()
    print(f"  {BOLD}QUICK REFERENCE{RESET}")
    print()
    print(f"  {GREEN}ten-hut{RESET}        Start all")
    print(f"  {GREEN}parade-rest{RESET}     Stop all")
    print(f"  {GREEN}forward-march{RESET}   Backend only")
    print(f"  {GREEN}company-front{RESET}   Frontend only")
    print(f"  {GREEN}run-through{RESET}     Tests")
    print(f"  {GREEN}check-step{RESET}      Status")
    print()
    print(f"  {BOLD}URLS{RESET}")
    print(f"  Frontend  {CYAN}http://localhost:5173{RESET}")
    print(f"  Backend   {CYAN}{API_BASE}{RESET}")


def _self_mtime():
    try:
        return os.path.getmtime(__file__)
    except OSError:
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", type=int, default=3)
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
