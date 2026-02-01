"""Watch command: live tail of corps activity via polling or WebSocket."""

import time
import signal
import sys

from backend.cli.output import print_info, print_error


def cmd_watch(client, args):
    corps_id = args.corps_id
    interval = getattr(args, "interval", 2)
    follow = getattr(args, "follow", True)

    print_info(f"Watching corps {corps_id[:8]}... (Ctrl+C to stop)")

    # Track what we've already shown
    seen_ids = set()
    running = True

    def handle_sigint(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_sigint)

    # First, show recent log entries
    try:
        initial = client.work_log(corps_id, limit=10)
        if isinstance(initial, list):
            for entry in initial:
                eid = entry.get("id", "")
                seen_ids.add(eid)
                _print_log_entry(entry)
    except Exception as e:
        print_error(f"Failed to fetch initial logs: {e}")
        return

    if not follow:
        return

    # Poll for new entries
    while running:
        try:
            time.sleep(interval)
            entries = client.work_log(corps_id, limit=20)
            if not isinstance(entries, list):
                continue
            new_entries = [e for e in entries if e.get("id", "") not in seen_ids]
            for entry in reversed(new_entries):
                seen_ids.add(entry.get("id", ""))
                _print_log_entry(entry)
        except KeyboardInterrupt:
            break
        except Exception:
            pass

    print_info("\nStopped watching.")


def _print_log_entry(entry: dict) -> None:
    event = entry.get("event_type", "?")
    role = entry.get("role", "")
    details = (entry.get("details") or "")[:120]
    ts = entry.get("created_at", "")
    if ts and len(ts) > 19:
        ts = ts[11:19]  # HH:MM:SS

    try:
        from rich.console import Console
        c = Console()
        c.print(f"[dim]{ts}[/dim] [cyan]{event:<18}[/cyan] [yellow]{role:<20}[/yellow] {details}")
    except ImportError:
        print(f"{ts} {event:<18} {role:<20} {details}")
