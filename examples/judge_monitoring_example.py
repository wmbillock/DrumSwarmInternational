#!/usr/bin/env python3
"""Example: Judge Monitoring Workflow

This script demonstrates how to use the judge monitoring tools to:
1. Get current corps health
2. Identify critical issues
3. Escalate problems to appropriate roles
4. Monitor segment-level details
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.database import create_db_engine, create_session_factory
from backend.services.health_monitor import analyze_corps_health, format_health_report
from backend.services.judge_dashboard import create_judge_dashboard
from backend.services.message_service import send_message
from backend.models.message import MessageType, MessagePriority


def example_1_basic_health_check():
    """Example 1: Run a basic health check."""
    print("=" * 70)
    print("EXAMPLE 1: Basic Health Check")
    print("=" * 70)

    engine = create_db_engine()
    DBSession = create_session_factory(engine)
    db = DBSession()

    try:
        corps_id = "e3ce0861-3f6e-4411-90db-a366a28a70f8"

        # Run health check
        report = analyze_corps_health(db, corps_id)

        # Print formatted report
        print(format_health_report(report))

    finally:
        db.close()


def example_2_identify_problems():
    """Example 2: Identify problems and their locations."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Problem Identification")
    print("=" * 70)

    engine = create_db_engine()
    DBSession = create_session_factory(engine)
    db = DBSession()

    try:
        corps_id = "e3ce0861-3f6e-4411-90db-a366a28a70f8"
        report = analyze_corps_health(db, corps_id)

        # Group problems by type
        failed_segments = [s for s in report.all_segments if s.status == "failed"]
        blocked_segments = [s for s in report.all_segments if s.status == "blocked"]
        stale_reps = []

        for seg in report.all_segments:
            if seg.stale_reps:
                stale_reps.extend([{
                    "segment": seg.title,
                    **rep
                } for rep in seg.stale_reps])

        print(f"\nFailed Segments ({len(failed_segments)}):")
        for seg in failed_segments:
            print(f"  - {seg.title} ({seg.segment_id[:8]}...)")

        print(f"\nBlocked Segments ({len(blocked_segments)}):")
        for seg in blocked_segments:
            print(f"  - {seg.title} ({seg.segment_id[:8]}...)")

        print(f"\nStale Reps ({len(stale_reps)}):")
        for rep in stale_reps[:5]:  # Show first 5
            print(f"  - {rep['segment']}: {rep['rep_id']} ({rep['age_hours']}h old)")

        print(f"\nCritical Issues ({len(report.critical_issues)}):")
        for issue in report.critical_issues[:5]:  # Show first 5
            print(f"  - {issue}")

    finally:
        db.close()


def example_3_escalate_issue():
    """Example 3: Escalate an issue to a role."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Issue Escalation")
    print("=" * 70)

    engine = create_db_engine()
    DBSession = create_session_factory(engine)
    db = DBSession()

    try:
        corps_id = "e3ce0861-3f6e-4411-90db-a366a28a70f8"

        # Check for critical issues
        report = analyze_corps_health(db, corps_id)

        if report.critical_issues:
            # Escalate first critical issue
            issue = report.critical_issues[0]
            print(f"\nDetected critical issue: {issue}")
            print(f"Escalating to Program Coordinator...")

            msg = send_message(
                db,
                corps_id=corps_id,
                from_role="timing_penalties_judge",
                to_role="program_coordinator",
                type=MessageType.ESCALATION,
                subject="Critical issue detected during health monitoring",
                body=f"Judge monitoring detected: {issue}\n\nPlease investigate and take corrective action.",
                priority=MessagePriority.HIGH,
            )

            print(f"Escalation sent: {msg.id}")
        else:
            print("\nNo critical issues to escalate.")

    finally:
        db.close()


def example_4_dashboard_view():
    """Example 4: View dashboard ASCII art."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Real-time Dashboard")
    print("=" * 70)

    engine = create_db_engine()
    DBSession = create_session_factory(engine)
    db = DBSession()

    try:
        corps_id = "e3ce0861-3f6e-4411-90db-a366a28a70f8"

        # Create dashboard
        dashboard = create_judge_dashboard(db, corps_id)

        # Print ASCII dashboard
        print(dashboard.get_ascii_dashboard())

        # Get detailed summaries
        seg_summary = dashboard.get_segment_summary()
        rep_summary = dashboard.get_rep_summary()

        print("\nSegment Summary:")
        print(f"  Total: {seg_summary['total']}")
        for status, count in sorted(seg_summary['by_status'].items()):
            print(f"    {status}: {count}")

        print("\nRep Summary:")
        print(f"  Total: {rep_summary['total']}")
        print(f"  Failed: {rep_summary['failed']}")
        print(f"  Pending: {rep_summary['pending']}")
        print(f"  Stale: {rep_summary['stale']}")

    finally:
        db.close()


def example_5_detailed_segment_analysis():
    """Example 5: Deep dive into a specific segment."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Detailed Segment Analysis")
    print("=" * 70)

    engine = create_db_engine()
    DBSession = create_session_factory(engine)
    db = DBSession()

    try:
        from backend.services.segment_service import get_segment, get_children
        from backend.services.rep_service import get_reps_for_segment

        corps_id = "e3ce0861-3f6e-4411-90db-a366a28a70f8"
        report = analyze_corps_health(db, corps_id)

        # Find a segment with issues
        problem_segs = [s for s in report.all_segments if s.critical_issues]
        if problem_segs:
            seg_health = problem_segs[0]
            segment = get_segment(db, seg_health.segment_id)
            children = get_children(db, seg_health.segment_id)
            reps = get_reps_for_segment(db, seg_health.segment_id)

            print(f"\nAnalyzing: {segment.title}")
            print(f"ID: {segment.id}")
            print(f"Type: {segment.type.value}")
            print(f"Status: {segment.status.value}")
            print(f"Description: {segment.description or 'N/A'}")

            print(f"\nChildren: {len(children)}")
            for child in children[:3]:
                print(f"  - {child.title} ({child.status.value})")

            print(f"\nReps: {len(reps)}")
            for rep in reps:
                print(f"  - {rep['id'][:8]}... ({rep['status']})")
                if rep.get('assigned_to'):
                    print(f"    Assigned to: {rep['assigned_to']}")

            print(f"\nCritical Issues:")
            for issue in seg_health.critical_issues:
                print(f"  - {issue}")

            if seg_health.stale_reps:
                print(f"\nStale Reps:")
                for stale in seg_health.stale_reps:
                    print(f"  - {stale['rep_id']} ({stale['age_hours']}h old, {stale['status']})")

        else:
            print("\nNo problematic segments found — system is healthy!")

    finally:
        db.close()


def example_6_comparative_monitoring():
    """Example 6: Monitor changes over time."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Comparative Monitoring (Simulated)")
    print("=" * 70)

    engine = create_db_engine()
    DBSession = create_session_factory(engine)
    db = DBSession()

    try:
        corps_id = "e3ce0861-3f6e-4411-90db-a366a28a70f8"

        # Take first snapshot
        report1 = analyze_corps_health(db, corps_id)
        print(f"\nSnapshot 1:")
        print(f"  Total segments: {report1.stats['total_segments']}")
        print(f"  Total reps: {report1.stats['total_reps']}")
        print(f"  Failed: {report1.stats['reps_failed']}")
        print(f"  Pending: {report1.stats['reps_pending']}")
        print(f"  Stale: {report1.stats['reps_stale']}")

        # In real scenario, wait for changes to occur...
        # For demo, we'll just note what changes to watch for

        print(f"\nChanges to monitor:")
        print(f"  - Increase in failed reps (regression)")
        print(f"  - Increase in stale reps (bottleneck)")
        print(f"  - Decrease in pending reps (progress)")
        print(f"  - New critical issues (errors)")

        # Simulate second snapshot (would be different after wait)
        report2 = analyze_corps_health(db, corps_id)

        delta_total = report2.stats['total_reps'] - report1.stats['total_reps']
        delta_failed = report2.stats['reps_failed'] - report1.stats['reps_failed']
        delta_pending = report2.stats['reps_pending'] - report1.stats['reps_pending']

        print(f"\nDelta (Snapshot 2 vs 1):")
        print(f"  Reps: {delta_total:+d}")
        print(f"  Failed: {delta_failed:+d}")
        print(f"  Pending: {delta_pending:+d}")

    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("JUDGE MONITORING EXAMPLES")
    print("=" * 70)
    print("\nThese examples show how to use the health monitoring tools.")
    print("Replace 'e3ce0861-3f6e-4411-90db-a366a28a70f8' with your actual corps ID.\n")

    try:
        # Run examples
        example_1_basic_health_check()
        example_2_identify_problems()
        example_3_escalate_issue()
        example_4_dashboard_view()
        example_5_detailed_segment_analysis()
        example_6_comparative_monitoring()

        print("\n" + "=" * 70)
        print("All examples completed!")
        print("=" * 70)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
