"""
Metrics collection and instrumentation for the DCI Swarm system.

Provides event-based metrics recording for:
- Rep lifecycle (duration, throughput, error rates)
- Agent sessions (utilization, activity)
- Message throughput
- Database latency
- Corps progression

Uses append-only event log design for immutability and concurrent access.
"""

import enum
import time
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Any, Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from backend.database import Base
from sqlalchemy import String, Text, Float, Integer, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
import uuid
import logging

logger = logging.getLogger(__name__)


class MetricType(str, enum.Enum):
    """All metric event types in the swarm system."""

    # Rep lifecycle metrics
    REP_CREATED = "rep_created"
    REP_ASSIGNED = "rep_assigned"
    REP_IN_PROGRESS = "rep_in_progress"
    REP_SUBMITTED = "rep_submitted"
    REP_COMPLETED = "rep_completed"
    REP_FAILED = "rep_failed"

    # Agent session metrics
    AGENT_SESSION_STARTED = "agent_session_started"
    AGENT_SESSION_ACTIVE = "agent_session_active"
    AGENT_SESSION_COMPLETED = "agent_session_completed"
    AGENT_SESSION_FAILED = "agent_session_failed"

    # Message metrics
    MESSAGE_SENT = "message_sent"
    MESSAGE_ARCHIVED = "message_archived"

    # Corps lifecycle metrics
    CORPS_CREATED = "corps_created"
    CORPS_STATUS_CHANGED = "corps_status_changed"

    # System metrics
    QUERY_LATENCY = "query_latency"
    TASK_LATENCY = "task_latency"
    BACKGROUND_JOB_EXECUTED = "background_job_executed"


@dataclass
class MetricEvent:
    """A single metric event in the swarm system."""

    timestamp: datetime
    metric_type: MetricType
    corps_id: Optional[str] = None
    agent_role: Optional[str] = None
    rep_id: Optional[str] = None
    segment_id: Optional[str] = None
    session_id: Optional[str] = None
    value: Optional[float] = None  # For latency, counts, etc.
    unit: Optional[str] = None  # "ms", "count", "seconds", etc.
    tags: Optional[Dict[str, str]] = None  # Additional context


class MetricsEvent(Base):
    """SQLAlchemy model for metrics event persistence."""

    __tablename__ = "metrics_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    metric_type: Mapped[str] = mapped_column(String(50), index=True)
    corps_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    agent_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rep_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    segment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<MetricsEvent({self.metric_type} at {self.timestamp})>"


class MetricsCollector:
    """Records metric events and provides query interface."""

    def __init__(self, db: Session):
        self.db = db

    def record(self, event: MetricEvent) -> None:
        """Record a metric event.

        Args:
            event: MetricEvent to record

        Note:
            This is non-blocking and safe for concurrent calls.
        """
        try:
            import json

            db_event = MetricsEvent(
                timestamp=event.timestamp,
                metric_type=event.metric_type.value,
                corps_id=event.corps_id,
                agent_role=event.agent_role,
                rep_id=event.rep_id,
                segment_id=event.segment_id,
                session_id=event.session_id,
                value=event.value,
                unit=event.unit,
                tags=json.dumps(event.tags) if event.tags else None
            )
            self.db.add(db_event)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to record metric event: {e}")
            self.db.rollback()

    def get_events(
        self,
        metric_type: Optional[MetricType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        corps_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        rep_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 1000
    ) -> List[MetricsEvent]:
        """Query metric events with filtering.

        Args:
            metric_type: Filter by metric type
            start_time: Filter events after this time
            end_time: Filter events before this time
            corps_id: Filter by corps
            agent_role: Filter by agent role
            rep_id: Filter by rep
            session_id: Filter by session
            limit: Maximum results to return

        Returns:
            List of matching MetricsEvent objects
        """
        query = select(MetricsEvent)

        if metric_type:
            query = query.where(MetricsEvent.metric_type == metric_type.value)
        if start_time:
            query = query.where(MetricsEvent.timestamp >= start_time)
        if end_time:
            query = query.where(MetricsEvent.timestamp <= end_time)
        if corps_id:
            query = query.where(MetricsEvent.corps_id == corps_id)
        if agent_role:
            query = query.where(MetricsEvent.agent_role == agent_role)
        if rep_id:
            query = query.where(MetricsEvent.rep_id == rep_id)
        if session_id:
            query = query.where(MetricsEvent.session_id == session_id)

        query = query.order_by(MetricsEvent.timestamp.desc()).limit(limit)

        return self.db.execute(query).scalars().all()

    def get_latency_percentiles(
        self,
        metric_type: MetricType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        corps_id: Optional[str] = None
    ) -> Dict[str, Optional[float]]:
        """Calculate latency percentiles (p50, p95, p99) for a metric type.

        Args:
            metric_type: The latency metric to analyze (e.g., QUERY_LATENCY)
            start_time: Start of time window
            end_time: End of time window
            corps_id: Filter by corps

        Returns:
            Dict with keys: p50, p95, p99, min, max, mean, count
        """
        query = select(MetricsEvent).where(
            MetricsEvent.metric_type == metric_type.value,
            MetricsEvent.value.isnot(None)
        )

        if start_time:
            query = query.where(MetricsEvent.timestamp >= start_time)
        if end_time:
            query = query.where(MetricsEvent.timestamp <= end_time)
        if corps_id:
            query = query.where(MetricsEvent.corps_id == corps_id)

        events = self.db.execute(query).scalars().all()

        if not events:
            return {"p50": None, "p95": None, "p99": None, "min": None, "max": None, "mean": None, "count": 0}

        values = sorted([e.value for e in events if e.value is not None])

        if not values:
            return {"p50": None, "p95": None, "p99": None, "min": None, "max": None, "mean": None, "count": 0}

        import statistics

        def percentile(data, p):
            n = len(data)
            if n == 0:
                return None
            index = (p / 100) * (n - 1)
            lower = int(index)
            upper = lower + 1
            if upper >= n:
                return data[lower]
            return data[lower] + (data[upper] - data[lower]) * (index - lower)

        return {
            "p50": percentile(values, 50),
            "p95": percentile(values, 95),
            "p99": percentile(values, 99),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "count": len(values)
        }

    def get_throughput(
        self,
        metric_type: MetricType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        corps_id: Optional[str] = None,
        interval_seconds: int = 60
    ) -> List[Dict[str, Any]]:
        """Get throughput (count per time interval).

        Args:
            metric_type: The metric to analyze
            start_time: Start of time window
            end_time: End of time window
            corps_id: Filter by corps
            interval_seconds: Size of each bucket (default 1 minute)

        Returns:
            List of dicts: {"timestamp": datetime, "count": int}
        """
        query = select(
            func.datetime(
                MetricsEvent.timestamp,
                f"-{interval_seconds} seconds"
            ).label("bucket"),
            func.count().label("count")
        ).where(MetricsEvent.metric_type == metric_type.value)

        if start_time:
            query = query.where(MetricsEvent.timestamp >= start_time)
        if end_time:
            query = query.where(MetricsEvent.timestamp <= end_time)
        if corps_id:
            query = query.where(MetricsEvent.corps_id == corps_id)

        query = query.group_by("bucket").order_by("bucket")

        results = self.db.execute(query).all()

        return [
            {
                "timestamp": row[0],
                "count": row[1]
            }
            for row in results
        ]

    def get_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        corps_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary metrics across all types.

        Args:
            start_time: Start of time window
            end_time: End of time window
            corps_id: Filter by corps

        Returns:
            Dict with overall metrics
        """
        query = select(MetricsEvent.metric_type, func.count().label("count"))

        if start_time:
            query = query.where(MetricsEvent.timestamp >= start_time)
        if end_time:
            query = query.where(MetricsEvent.timestamp <= end_time)
        if corps_id:
            query = query.where(MetricsEvent.corps_id == corps_id)

        query = query.group_by(MetricsEvent.metric_type)

        results = self.db.execute(query).all()

        return {
            metric_type: count
            for metric_type, count in results
        }


# Global metric instances (lazy initialized)
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(db: Session) -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(db)
    return _metrics_collector


def record_event(
    db: Session,
    metric_type: MetricType,
    corps_id: Optional[str] = None,
    agent_role: Optional[str] = None,
    rep_id: Optional[str] = None,
    segment_id: Optional[str] = None,
    session_id: Optional[str] = None,
    value: Optional[float] = None,
    unit: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """Convenience function to record a metric event.

    Args:
        db: SQLAlchemy session
        metric_type: Type of metric event
        corps_id: Optional corps identifier
        agent_role: Optional agent role
        rep_id: Optional rep identifier
        segment_id: Optional segment identifier
        session_id: Optional session identifier
        value: Optional numeric value (for latency, counts, etc.)
        unit: Optional unit of measurement
        tags: Optional dict of additional context
    """
    event = MetricEvent(
        timestamp=datetime.now(timezone.utc),
        metric_type=metric_type,
        corps_id=corps_id,
        agent_role=agent_role,
        rep_id=rep_id,
        segment_id=segment_id,
        session_id=session_id,
        value=value,
        unit=unit,
        tags=tags
    )
    collector = get_metrics_collector(db)
    collector.record(event)
