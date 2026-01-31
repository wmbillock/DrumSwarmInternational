"""Health monitoring service for corps judges.

Provides comprehensive health checks for a corps, including:
- Root segment status and hierarchy
- Rep status tracking
- Stale work detection
- Error identification
- Critical issue escalation
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from backend.models.corps import Corps
from backend.models.segment import Segment, SegmentStatus, SegmentType
from backend.models.rep import Rep, RepStatus
from backend.models.message import Message, MessageType, MessagePriority


@dataclass
class SegmentHealthReport:
    """Health status of a single segment."""
    segment_id: str
    segment_type: str
    title: str
    status: str
    parent_id: Optional[str]
    child_count: int
    rep_count: int
    failed_rep_count: int
    pending_rep_count: int
    stale_reps: list = field(default_factory=list)
    critical_issues: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "type": self.segment_type,
            "title": self.title,
            "status": self.status,
            "parent_id": self.parent_id,
            "children": self.child_count,
            "reps_total": self.rep_count,
            "reps_failed": self.failed_rep_count,
            "reps_pending": self.pending_rep_count,
            "stale_reps": self.stale_reps,
            "critical_issues": self.critical_issues,
        }


@dataclass
class CorpsHealthReport:
    """Comprehensive health report for a corps."""
    corps_id: str
    corps_name: str
    corps_status: str
    rehearsal_mode: Optional[str]
    assessment_time: datetime
    root_segment: Optional[SegmentHealthReport]
    all_segments: list[SegmentHealthReport] = field(default_factory=list)
    critical_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "corps_id": self.corps_id,
            "corps_name": self.corps_name,
            "corps_status": self.corps_status,
            "rehearsal_mode": self.rehearsal_mode,
            "assessment_time": self.assessment_time.isoformat(),
            "root_segment": self.root_segment.to_dict() if self.root_segment else None,
            "segments_summary": {
                "total": len(self.all_segments),
                "by_status": self._count_by_status(),
                "by_type": self._count_by_type(),
            },
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "stats": self.stats,
        }

    def _count_by_status(self) -> dict:
        counts = {}
        for seg in self.all_segments:
            status = seg.status
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _count_by_type(self) -> dict:
        counts = {}
        for seg in self.all_segments:
            seg_type = seg.segment_type
            counts[seg_type] = counts.get(seg_type, 0) + 1
        return counts


def get_segment_health(db: Session, segment_id: str, stale_threshold_hours: int = 2) -> SegmentHealthReport:
    """Analyze health of a single segment."""
    segment = db.get(Segment, segment_id)
    if not segment:
        return SegmentHealthReport(
            segment_id=segment_id,
            segment_type="unknown",
            title="NOT FOUND",
            status="unknown",
            parent_id=None,
            child_count=0,
            rep_count=0,
            failed_rep_count=0,
            pending_rep_count=0,
            critical_issues=["Segment not found"],
        )

    # Get children
    children = db.query(Segment).filter(Segment.parent_id == segment_id).all()
    child_count = len(children)

    # Get reps
    reps = db.query(Rep).filter(Rep.segment_id == segment_id).all()
    rep_count = len(reps)
    failed_reps = [r for r in reps if r.status == RepStatus.FAILED]
    pending_reps = [r for r in reps if r.status in (RepStatus.PENDING, RepStatus.ASSIGNED)]

    # Identify stale reps
    now = datetime.utcnow()
    stale_threshold = timedelta(hours=stale_threshold_hours)
    stale_reps = []
    for rep in reps:
        if rep.updated_at and (now - rep.updated_at) > stale_threshold:
            stale_reps.append({
                "rep_id": rep.id[:8] + "...",
                "status": rep.status.value,
                "age_hours": round((now - rep.updated_at).total_seconds() / 3600, 1),
                "assigned_to": rep.assigned_to or "unassigned",
            })

    # Identify critical issues
    critical_issues = []
    if segment.status == SegmentStatus.FAILED:
        critical_issues.append(f"Segment status is FAILED")
    if segment.status == SegmentStatus.BLOCKED:
        critical_issues.append(f"Segment is BLOCKED")
    if failed_reps:
        critical_issues.append(f"{len(failed_reps)} rep(s) FAILED")
    if stale_reps:
        critical_issues.append(f"{len(stale_reps)} rep(s) are STALE (> {stale_threshold_hours}h)")
    if pending_reps and rep_count > 0 and rep_count > len(pending_reps):
        # Some reps are active, but others are still pending — potential bottleneck
        critical_issues.append(f"{len(pending_reps)} rep(s) still PENDING while others are active")

    return SegmentHealthReport(
        segment_id=segment_id,
        segment_type=segment.type.value,
        title=segment.title,
        status=segment.status.value,
        parent_id=segment.parent_id,
        child_count=child_count,
        rep_count=rep_count,
        failed_rep_count=len(failed_reps),
        pending_rep_count=len(pending_reps),
        stale_reps=stale_reps,
        critical_issues=critical_issues,
    )


def analyze_corps_health(db: Session, corps_id: str, stale_threshold_hours: int = 2) -> CorpsHealthReport:
    """Perform comprehensive health check on a corps."""
    corps = db.get(Corps, corps_id)
    if not corps:
        return CorpsHealthReport(
            corps_id=corps_id,
            corps_name="NOT FOUND",
            corps_status="unknown",
            rehearsal_mode=None,
            assessment_time=datetime.utcnow(),
            critical_issues=["Corps not found in database"],
        )

    # Find root segment (SHOW type with no parent)
    root_segment = db.query(Segment).filter(
        Segment.type == SegmentType.SHOW
    ).all()
    root = None
    for seg in root_segment:
        # In a multi-show system, try to find one associated with this corps
        # For now, just use the first SHOW segment as a proxy
        root = seg
        break

    root_health = get_segment_health(db, root.id, stale_threshold_hours) if root else None

    # Get all segments recursively
    all_segments = []
    def collect_segments(seg_id: str):
        health = get_segment_health(db, seg_id, stale_threshold_hours)
        all_segments.append(health)
        # Get children
        children = db.query(Segment).filter(Segment.parent_id == seg_id).all()
        for child in children:
            collect_segments(child.id)

    if root:
        collect_segments(root.id)

    # Collect critical issues and warnings
    critical_issues = []
    warnings = []

    for seg in all_segments:
        if seg.critical_issues:
            for issue in seg.critical_issues:
                critical_issues.append(f"{seg.title} [{seg.segment_id[:8]}]: {issue}")

    # Identify stuck agents (messages with no progress)
    stuck_messages = db.query(Message).filter(
        Message.corps_id == corps_id,
        Message.type == MessageType.HANDOFF,
        Message.acknowledged_at.is_(None),
    ).all()
    if stuck_messages:
        warnings.append(f"{len(stuck_messages)} unacknowledged handoff message(s)")

    # Stats
    total_reps = sum(seg.rep_count for seg in all_segments)
    total_failed = sum(seg.failed_rep_count for seg in all_segments)
    total_stale = sum(len(seg.stale_reps) for seg in all_segments)
    total_pending = sum(seg.pending_rep_count for seg in all_segments)

    stats = {
        "total_segments": len(all_segments),
        "total_reps": total_reps,
        "reps_failed": total_failed,
        "reps_pending": total_pending,
        "reps_stale": total_stale,
        "segments_by_status": {},
    }

    # Count segments by status
    for seg in all_segments:
        status = seg.status
        if status not in stats["segments_by_status"]:
            stats["segments_by_status"][status] = 0
        stats["segments_by_status"][status] += 1

    # Severity checks
    if corps.status.value == "disbanded":
        critical_issues.insert(0, "Corps status is DISBANDED")
    if total_failed > 0:
        if critical_issues:
            critical_issues.insert(0, f"WARNING: {total_failed} total rep(s) have FAILED")
    if total_stale > 0:
        if len(critical_issues) < 2:
            warnings.insert(0, f"WARNING: {total_stale} total rep(s) are STALE")

    return CorpsHealthReport(
        corps_id=corps_id,
        corps_name=corps.name,
        corps_status=corps.status.value,
        rehearsal_mode=corps.rehearsal_mode.value if corps.rehearsal_mode else None,
        assessment_time=datetime.utcnow(),
        root_segment=root_health,
        all_segments=all_segments,
        critical_issues=critical_issues,
        warnings=warnings,
        stats=stats,
    )


def format_health_report(report: CorpsHealthReport) -> str:
    """Format health report as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"CORPS HEALTH ASSESSMENT: {report.corps_name} ({report.corps_id})")
    lines.append("=" * 70)
    lines.append(f"Assessment Time: {report.assessment_time.isoformat()}")
    lines.append(f"Corps Status: {report.corps_status}")
    lines.append(f"Rehearsal Mode: {report.rehearsal_mode or 'N/A'}")
    lines.append("")

    # Critical issues
    if report.critical_issues:
        lines.append("CRITICAL ISSUES:")
        for issue in report.critical_issues:
            lines.append(f"  [CRITICAL] {issue}")
        lines.append("")

    # Warnings
    if report.warnings:
        lines.append("WARNINGS:")
        for warning in report.warnings:
            lines.append(f"  [WARN] {warning}")
        lines.append("")

    # Stats
    lines.append("SUMMARY STATISTICS:")
    lines.append(f"  Total Segments: {report.stats.get('total_segments', 0)}")
    lines.append(f"  Total Reps: {report.stats.get('total_reps', 0)}")
    lines.append(f"    - Failed: {report.stats.get('reps_failed', 0)}")
    lines.append(f"    - Pending: {report.stats.get('reps_pending', 0)}")
    lines.append(f"    - Stale: {report.stats.get('reps_stale', 0)}")
    lines.append("")

    # Segments by status
    if report.stats.get('segments_by_status'):
        lines.append("Segments by Status:")
        for status, count in sorted(report.stats['segments_by_status'].items()):
            lines.append(f"  {status:>15}: {count}")
        lines.append("")

    # Root segment details
    if report.root_segment:
        lines.append(f"ROOT SEGMENT: {report.root_segment.title}")
        lines.append(f"  ID: {report.root_segment.segment_id}")
        lines.append(f"  Type: {report.root_segment.segment_type}")
        lines.append(f"  Status: {report.root_segment.status}")
        lines.append(f"  Children: {report.root_segment.child_count}")
        lines.append(f"  Reps: {report.root_segment.rep_count} total")
        if report.root_segment.critical_issues:
            lines.append(f"  Issues: {', '.join(report.root_segment.critical_issues)}")
        lines.append("")

    # Problematic segments (those with critical issues)
    problem_segments = [s for s in report.all_segments if s.critical_issues]
    if problem_segments:
        lines.append(f"SEGMENTS WITH ISSUES ({len(problem_segments)} total):")
        for seg in sorted(problem_segments, key=lambda s: len(s.critical_issues), reverse=True):
            lines.append(f"  [{seg.status:>12}] {seg.title} ({seg.segment_type})")
            lines.append(f"      ID: {seg.segment_id}")
            for issue in seg.critical_issues:
                lines.append(f"      - {issue}")
            if seg.stale_reps:
                for stale in seg.stale_reps[:2]:  # Show first 2
                    lines.append(f"        Stale: {stale['rep_id']} ({stale['age_hours']}h old, status={stale['status']})")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def export_json(report: CorpsHealthReport) -> str:
    """Export health report as JSON."""
    return json.dumps(report.to_dict(), indent=2)
