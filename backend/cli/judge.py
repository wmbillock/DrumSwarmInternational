#!/usr/bin/env python3
"""DCI Swarm Judge Monitoring Tool — `./dci judge`

For judges (Timing & Penalties, Execution, etc.) to monitor corps health,
identify issues, and escalate problems to appropriate roles.

Usage:
    python -m backend.cli.judge health <corps-id>
    python -m backend.cli.judge escalate <corps-id> <role> "Issue description"
    python -m backend.cli.judge list-issues <corps-id>
"""

import argparse
import json
import sys
import os
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# Colors for terminal output
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
MAGENTA = "\033[0;35m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


def log(color, prefix, msg):
    """Pretty-print colored log messages."""
    print(f"{color}[{prefix}]{NC} {msg}")


def run_health_check(corps_id: str, output_format: str = "text"):
    """Run health check on a corps and display results."""
    from backend.database import create_db_engine, create_session_factory
    from backend.services.health_monitor import analyze_corps_health, format_health_report, export_json

    engine = create_db_engine()
    DBSession = create_session_factory(engine)
    db = DBSession()

    try:
        log(CYAN, "judge", f"Running health check on corps {corps_id}...")
        report = analyze_corps_health(db, corps_id)

        if output_format == "json":
            print(export_json(report))
        else:
            print(format_health_report(report))

        return report

    finally:
        db.close()


def escalate_issue(corps_id: str, to_role: str, subject: str, body: str = ""):
    """Send an escalation message to a role."""
    from backend.database import create_db_engine, create_session_factory
    from backend.models.message import MessageType, MessagePriority
    from backend.services.message_service import send_message

    engine = create_db_engine()
    DBSession = create_session_factory(engine)
    db = DBSession()

    try:
        log(CYAN, "judge", f"Escalating to {to_role}: {subject}")

        msg = send_message(
            db,
            corps_id=corps_id,
            from_role="timing_penalties_judge",
            to_role=to_role,
            type=MessageType.ESCALATION,
            subject=subject,
            body=body or "Escalated from Timing & Penalties Judge health monitoring",
            priority=MessagePriority.HIGH,
        )

        log(GREEN, "judge", f"Escalation sent: {msg.id}")
        return msg

    finally:
        db.close()


def list_issues(corps_id: str):
    """List all current issues in a corps."""
    from backend.database import create_db_engine, create_session_factory
    from backend.services.health_monitor import analyze_corps_health

    engine = create_db_engine()
    DBSession = create_session_factory(engine)
    db = DBSession()

    try:
        report = analyze_corps_health(db, corps_id)

        print(f"\n{BOLD}Issues for Corps: {report.corps_name}{NC}")
        print(f"Assessment: {report.assessment_time.isoformat()}\n")

        if not report.critical_issues and not report.warnings:
            log(GREEN, "judge", "No issues detected!")
            return

        if report.critical_issues:
            print(f"{RED}CRITICAL ISSUES ({len(report.critical_issues)}):{NC}")
            for i, issue in enumerate(report.critical_issues, 1):
                print(f"  {i}. {issue}")
            print()

        if report.warnings:
            print(f"{YELLOW}WARNINGS ({len(report.warnings)}):{NC}")
            for i, warning in enumerate(report.warnings, 1):
                print(f"  {i}. {warning}")
            print()

        # Summary of problematic segments
        problem_segments = [s for s in report.all_segments if s.critical_issues]
        if problem_segments:
            print(f"{YELLOW}Affected Segments ({len(problem_segments)}):{NC}")
            for seg in sorted(problem_segments, key=lambda s: s.title):
                print(f"  - {seg.title} ({seg.segment_type}) [{seg.status}]")
                for issue in seg.critical_issues[:1]:  # Show first issue
                    print(f"    {issue}")

    finally:
        db.close()


def get_segment_details(segment_id: str):
    """Get detailed information about a specific segment."""
    from backend.database import create_db_engine, create_session_factory
    from backend.services.segment_service import get_segment, get_children
    from backend.services.rep_service import get_reps_for_segment
    from backend.services.health_monitor import get_segment_health

    engine = create_db_engine()
    DBSession = create_session_factory(engine)
    db = DBSession()

    try:
        segment = get_segment(db, segment_id)
        if not segment:
            log(RED, "judge", f"Segment not found: {segment_id}")
            return

        health = get_segment_health(db, segment_id)
        children = get_children(db, segment_id)
        reps = get_reps_for_segment(db, segment_id)

        print(f"\n{BOLD}Segment Details: {segment.title}{NC}")
        print(f"ID:          {segment_id}")
        print(f"Type:        {segment.type.value}")
        print(f"Status:      {segment.status.value}")
        print(f"Parent:      {segment.parent_id or 'N/A'}")
        print(f"Description: {segment.description or 'N/A'}")
        print(f"Caption:     {segment.caption or 'N/A'}")
        print()

        print(f"{BOLD}Hierarchy:{NC}")
        print(f"  Children:  {len(children)}")
        print(f"  Reps:      {len(reps)}")
        print()

        if reps:
            print(f"{BOLD}Reps:{NC}")
            for rep in reps:
                status_color = GREEN if rep.status.value == 'completed' else RED if rep.status.value == 'failed' else YELLOW
                print(f"  {status_color}{rep.status.value:>12}{NC} {rep.id}")
                if rep.assigned_to:
                    print(f"    Assigned to: {rep.assigned_to}")
                if rep.result:
                    preview = rep.result[:100].replace('\n', ' ')
                    print(f"    Result: {preview}...")
            print()

        if health.critical_issues:
            print(f"{RED}{BOLD}Critical Issues:{NC}")
            for issue in health.critical_issues:
                print(f"  - {issue}")
            print()

        if health.stale_reps:
            print(f"{YELLOW}{BOLD}Stale Reps:{NC}")
            for stale in health.stale_reps:
                print(f"  {stale['rep_id']} - {stale['age_hours']}h old ({stale['status']})")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="DCI Swarm Judge Monitoring Tool",
        epilog="Use subcommands to monitor corps health and escalate issues.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Health check subcommand
    health_parser = subparsers.add_parser("health", help="Run health check on a corps")
    health_parser.add_argument("corps_id", help="Corps ID to check")
    health_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Escalate subcommand
    escalate_parser = subparsers.add_parser("escalate", help="Escalate an issue")
    escalate_parser.add_argument("corps_id", help="Corps ID")
    escalate_parser.add_argument("role", help="Role to escalate to (e.g., executive_director, program_coordinator)")
    escalate_parser.add_argument("subject", help="Issue subject")
    escalate_parser.add_argument("--body", help="Detailed issue description")

    # List issues subcommand
    issues_parser = subparsers.add_parser("list-issues", help="List all issues in a corps")
    issues_parser.add_argument("corps_id", help="Corps ID")

    # Segment details subcommand
    segment_parser = subparsers.add_parser("segment", help="Get details about a segment")
    segment_parser.add_argument("segment_id", help="Segment ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "health":
        output_format = "json" if args.json else "text"
        run_health_check(args.corps_id, output_format)

    elif args.command == "escalate":
        escalate_issue(args.corps_id, args.role, args.subject, args.body or "")

    elif args.command == "list-issues":
        list_issues(args.corps_id)

    elif args.command == "segment":
        get_segment_details(args.segment_id)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
