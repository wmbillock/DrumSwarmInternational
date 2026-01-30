#!/usr/bin/env python3
"""Pane 3: Streaming Logs — tail backend + frontend logs with color coding."""

import os
import sys
import time
import select
import re

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"

PROJECT_ROOT = os.environ.get("DCI_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
BACKEND_LOG = os.path.join(PROJECT_ROOT, "backend.log")
FRONTEND_LOG = os.path.join(PROJECT_ROOT, "frontend.log")

# Patterns to highlight
ERROR_RE = re.compile(r"(error|exception|traceback|failed|500)", re.IGNORECASE)
WARN_RE = re.compile(r"(warn|warning|deprecated|404)", re.IGNORECASE)
HTTP_RE = re.compile(r"(GET|POST|PUT|DELETE|PATCH)\s+\S+\s+\d{3}")
STARTUP_RE = re.compile(r"(started|running|listening|ready|uvicorn)", re.IGNORECASE)


def colorize(line, prefix_color, prefix):
    tag = f"{prefix_color}{prefix}{RESET} "

    if ERROR_RE.search(line):
        return f"{tag}{RED}{line}{RESET}"
    elif WARN_RE.search(line):
        return f"{tag}{YELLOW}{line}{RESET}"
    elif HTTP_RE.search(line):
        return f"{tag}{CYAN}{line}{RESET}"
    elif STARTUP_RE.search(line):
        return f"{tag}{GREEN}{line}{RESET}"
    else:
        return f"{tag}{DIM}{line}{RESET}"


def tail_file(path):
    """Open a file and seek to end, returning the file object."""
    try:
        f = open(path, "r")
        f.seek(0, 2)  # seek to end
        return f
    except FileNotFoundError:
        return None


def _self_mtime():
    try:
        return os.path.getmtime(__file__)
    except OSError:
        return 0


def main():
    start_mtime = _self_mtime()

    print(f"{BOLD}{YELLOW}LOGS{RESET}")
    print(f"{DIM}Tailing backend.log & frontend.log{RESET}")
    print()

    # Ensure log files exist
    for path in [BACKEND_LOG, FRONTEND_LOG]:
        if not os.path.exists(path):
            try:
                open(path, "a").close()
            except Exception:
                pass

    be_file = tail_file(BACKEND_LOG)
    fe_file = tail_file(FRONTEND_LOG)

    if not be_file and not fe_file:
        print(f"{RED}No log files found.{RESET}")
        print(f"{DIM}Start the backend: ./dci forward-march{RESET}")
        # Wait and retry
        while True:
            time.sleep(3)
            be_file = tail_file(BACKEND_LOG)
            fe_file = tail_file(FRONTEND_LOG)
            if be_file or fe_file:
                break

    try:
        while True:
            activity = False

            if be_file:
                for line in be_file:
                    line = line.rstrip()
                    if line:
                        print(colorize(line, BLUE, "BE"))
                        activity = True

            if fe_file:
                for line in fe_file:
                    line = line.rstrip()
                    if line:
                        print(colorize(line, MAGENTA, "FE"))
                        activity = True

            if not activity:
                time.sleep(0.3)

            if _self_mtime() != start_mtime:
                os.execv(sys.executable, [sys.executable] + sys.argv)

            # Check if files got rotated/recreated
            if be_file and not os.path.exists(BACKEND_LOG):
                be_file.close()
                be_file = None
            elif not be_file and os.path.exists(BACKEND_LOG):
                be_file = tail_file(BACKEND_LOG)

            if fe_file and not os.path.exists(FRONTEND_LOG):
                fe_file.close()
                fe_file = None
            elif not fe_file and os.path.exists(FRONTEND_LOG):
                fe_file = tail_file(FRONTEND_LOG)

    except KeyboardInterrupt:
        pass
    finally:
        if be_file:
            be_file.close()
        if fe_file:
            fe_file.close()


if __name__ == "__main__":
    main()
