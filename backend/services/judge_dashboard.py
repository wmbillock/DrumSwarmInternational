"""Judge dashboard service for real-time monitoring.

Provides streaming health updates and formatted dashboards for judges
to monitor corps in real-time.
"""

import json
from datetime import datetime
from typing import Optional, Generator
from sqlalchemy.orm import Session

from backend.services.health_monitor import analyze_corps_health, CorpsHealthReport


class JudgeDashboard:
    """Real-time dashboard for judge monitoring."""

    def __init__(self, db: Session, corps_id: str, refresh_interval: int = 5):
        """Initialize dashboard.

        Args:
            db: Database session
            corps_id: Corps ID to monitor
            refresh_interval: Seconds between health checks (default 5)
        """
        self.db = db
        self.corps_id = corps_id
        self.refresh_interval = refresh_interval
        self.last_report = None
        self.report_history = []

    def get_current_status(self) -> dict:
        """Get current status snapshot."""
        report = analyze_corps_health(self.db, self.corps_id)
        self.last_report = report

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "corps_id": self.corps_id,
            "corps_name": report.corps_name,
            "corps_status": report.corps_status,
            "rehearsal_mode": report.rehearsal_mode,
            "critical_count": len(report.critical_issues),
            "warning_count": len(report.warnings),
            "total_segments": report.stats.get("total_segments", 0),
            "reps_total": report.stats.get("total_reps", 0),
            "reps_failed": report.stats.get("reps_failed", 0),
            "reps_pending": report.stats.get("reps_pending", 0),
            "reps_stale": report.stats.get("reps_stale", 0),
        }

    def stream_updates(self, max_updates: Optional[int] = None) -> Generator[dict, None, None]:
        """Stream dashboard updates continuously.

        Args:
            max_updates: Maximum number of updates to stream (None = infinite)

        Yields:
            Status dictionaries with current health data
        """
        update_count = 0
        while max_updates is None or update_count < max_updates:
            status = self.get_current_status()
            yield status
            update_count += 1

    def get_critical_alerts(self) -> list[dict]:
        """Get list of critical alerts."""
        if not self.last_report:
            self.get_current_status()

        alerts = []
        for issue in self.last_report.critical_issues:
            alerts.append({
                "severity": "critical",
                "message": issue,
                "timestamp": datetime.utcnow().isoformat(),
            })
        for warning in self.last_report.warnings:
            alerts.append({
                "severity": "warning",
                "message": warning,
                "timestamp": datetime.utcnow().isoformat(),
            })
        return alerts

    def get_segment_summary(self) -> dict:
        """Get summary of segments by status."""
        if not self.last_report:
            self.get_current_status()

        summary = {
            "total": len(self.last_report.all_segments),
            "by_status": {},
            "by_type": {},
            "problem_segments": [],
        }

        # Count by status
        for seg in self.last_report.all_segments:
            status = seg.status
            if status not in summary["by_status"]:
                summary["by_status"][status] = 0
            summary["by_status"][status] += 1

            seg_type = seg.segment_type
            if seg_type not in summary["by_type"]:
                summary["by_type"][seg_type] = 0
            summary["by_type"][seg_type] += 1

            if seg.critical_issues:
                summary["problem_segments"].append({
                    "id": seg.segment_id,
                    "title": seg.title,
                    "type": seg.segment_type,
                    "status": seg.status,
                    "issues": seg.critical_issues,
                    "reps_failed": seg.failed_rep_count,
                    "reps_stale": len(seg.stale_reps),
                })

        return summary

    def get_rep_summary(self) -> dict:
        """Get summary of reps across all segments."""
        if not self.last_report:
            self.get_current_status()

        return {
            "total": self.last_report.stats.get("total_reps", 0),
            "completed": (self.last_report.stats.get("total_reps", 0) -
                         self.last_report.stats.get("reps_failed", 0) -
                         self.last_report.stats.get("reps_pending", 0) -
                         self.last_report.stats.get("reps_stale", 0)),
            "in_progress": (self.last_report.stats.get("total_reps", 0) -
                           self.last_report.stats.get("reps_completed", 0) -
                           self.last_report.stats.get("reps_failed", 0)),
            "failed": self.last_report.stats.get("reps_failed", 0),
            "pending": self.last_report.stats.get("reps_pending", 0),
            "stale": self.last_report.stats.get("reps_stale", 0),
        }

    def get_ascii_dashboard(self) -> str:
        """Generate ASCII art dashboard."""
        if not self.last_report:
            self.get_current_status()

        lines = []
        lines.append("╔══════════════════════════════════════════════════════╗")
        lines.append("║ JUDGE MONITORING DASHBOARD — DCI SWARM SYSTEM HEALTH ║")
        lines.append("╚══════════════════════════════════════════════════════╝")
        lines.append("")

        # Header info
        lines.append(f"Corps: {self.last_report.corps_name}")
        lines.append(f"Status: {self.last_report.corps_status}")
        lines.append(f"Mode: {self.last_report.rehearsal_mode or 'N/A'}")
        lines.append(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")

        # Alert summary
        crit_count = len(self.last_report.critical_issues)
        warn_count = len(self.last_report.warnings)

        if crit_count > 0:
            lines.append(f"⚠️  CRITICAL ISSUES: {crit_count}")
        if warn_count > 0:
            lines.append(f"⚠️  WARNINGS: {warn_count}")
        if crit_count == 0 and warn_count == 0:
            lines.append("✓ System healthy")
        lines.append("")

        # Segment stats
        stats = self.last_report.stats
        total_segs = stats.get("total_segments", 0)
        lines.append(f"Segments: {total_segs}")
        status_dist = stats.get("segments_by_status", {})
        for status in ["completed", "in_progress", "pending", "failed", "blocked"]:
            count = status_dist.get(status, 0)
            if count > 0:
                lines.append(f"  {status:>12}: {count}")
        lines.append("")

        # Rep stats
        total_reps = stats.get("total_reps", 0)
        failed_reps = stats.get("reps_failed", 0)
        pending_reps = stats.get("reps_pending", 0)
        stale_reps = stats.get("reps_stale", 0)

        lines.append(f"Reps: {total_reps} total")
        lines.append(f"  {failed_reps:>3} failed | {pending_reps:>3} pending | {stale_reps:>3} stale")
        lines.append("")

        # Top issues
        if self.last_report.critical_issues:
            lines.append("Top Critical Issues:")
            for issue in self.last_report.critical_issues[:3]:
                # Truncate long issues
                issue_text = issue if len(issue) <= 50 else issue[:47] + "..."
                lines.append(f"  • {issue_text}")
            if len(self.last_report.critical_issues) > 3:
                lines.append(f"  ... and {len(self.last_report.critical_issues) - 3} more")
            lines.append("")

        lines.append("╚══════════════════════════════════════════════════════╝")
        return "\n".join(lines)

    def export_json(self) -> str:
        """Export full dashboard state as JSON."""
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "status": self.get_current_status(),
            "alerts": self.get_critical_alerts(),
            "segments": self.get_segment_summary(),
            "reps": self.get_rep_summary(),
        }, indent=2)


def create_judge_dashboard(db: Session, corps_id: str) -> JudgeDashboard:
    """Factory function to create a judge dashboard."""
    return JudgeDashboard(db, corps_id)
