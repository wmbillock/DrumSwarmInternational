"""
Metrics aggregation and time-series storage for the DCI Swarm.

Takes raw metric events and aggregates them into:
- Time-series buckets (1-minute, 5-minute, hourly)
- Percentile calculations over time windows
- Trend analysis and rate-of-change
- Historical data with retention policy

Uses append-only immutable aggregates for consistency.
"""

import enum
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session, Mapped, mapped_column
from sqlalchemy import select, func, String, Float, DateTime, Integer, text
from sqlalchemy.types import JSON
from backend.database import Base
import uuid
import json
import logging

logger = logging.getLogger(__name__)


class AggregateWindow(str, enum.Enum):
    """Time windows for metric aggregation."""

    MINUTE = "1m"    # 1-minute buckets
    FIVE_MINUTE = "5m"  # 5-minute buckets
    HOUR = "1h"      # hourly buckets
    DAY = "1d"       # daily buckets


class MetricsAggregate(Base):
    """SQLAlchemy model for aggregated metrics."""

    __tablename__ = "metrics_aggregates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Identification
    bucket_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    window: Mapped[str] = mapped_column(String(10), index=True)  # "1m", "5m", "1h", "1d"
    metric_type: Mapped[str] = mapped_column(String(50), index=True)

    # Context filters
    corps_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    agent_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Aggregate values
    count: Mapped[int] = mapped_column(Integer, default=0)
    sum_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mean_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p50_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p95_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p99_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregate to dictionary."""
        return {
            "id": self.id,
            "bucket_start": self.bucket_start,
            "window": self.window,
            "metric_type": self.metric_type,
            "corps_id": self.corps_id,
            "agent_role": self.agent_role,
            "count": self.count,
            "sum": self.sum_value,
            "min": self.min_value,
            "max": self.max_value,
            "mean": self.mean_value,
            "p50": self.p50_value,
            "p95": self.p95_value,
            "p99": self.p99_value,
        }

    def __repr__(self) -> str:
        return f"<MetricsAggregate({self.metric_type} {self.window} @ {self.bucket_start})>"


class MetricsTrend(Base):
    """SQLAlchemy model for trend analysis."""

    __tablename__ = "metrics_trends"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Identification
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_days: Mapped[int] = mapped_column(Integer)  # 7, 30, etc.
    metric_type: Mapped[str] = mapped_column(String(50), index=True)

    # Context
    corps_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    agent_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Trend metrics
    avg_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prev_period_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rate_of_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trend_direction: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "up", "down", "flat"

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<MetricsTrend({self.metric_type} {self.period_days}d {self.trend_direction})>"


class MetricsAggregator:
    """Aggregates raw metric events into time-series data."""

    def __init__(self, db: Session):
        self.db = db

    def aggregate_events(
        self,
        metric_type: str,
        window: AggregateWindow,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        corps_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        force: bool = False
    ) -> int:
        """Aggregate raw events into time-series buckets.

        Args:
            metric_type: Type of metric to aggregate
            window: Time window for bucketing (1m, 5m, 1h, 1d)
            start_time: Start of time range (default: 24 hours ago)
            end_time: End of time range (default: now)
            corps_id: Optional corps filter
            agent_role: Optional role filter
            force: Force re-aggregation (default: skip existing)

        Returns:
            Number of aggregates created
        """
        from backend.services.metrics import MetricsEvent

        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        # Window size in seconds
        window_seconds = self._window_to_seconds(window)

        # Query raw events
        query = select(
            func.datetime(
                MetricsEvent.timestamp,
                f"-{window_seconds} seconds"
            ).label("bucket"),
            MetricsEvent.metric_type,
            MetricsEvent.corps_id,
            MetricsEvent.agent_role,
            func.count().label("count"),
            func.sum(MetricsEvent.value).label("sum_value"),
            func.min(MetricsEvent.value).label("min_value"),
            func.max(MetricsEvent.value).label("max_value"),
            func.avg(MetricsEvent.value).label("mean_value"),
        ).where(
            MetricsEvent.metric_type == metric_type,
            MetricsEvent.timestamp >= start_time,
            MetricsEvent.timestamp <= end_time,
        )

        if corps_id:
            query = query.where(MetricsEvent.corps_id == corps_id)
        if agent_role:
            query = query.where(MetricsEvent.agent_role == agent_role)

        query = query.group_by(
            "bucket",
            MetricsEvent.metric_type,
            MetricsEvent.corps_id,
            MetricsEvent.agent_role
        )

        results = self.db.execute(query).all()
        created = 0

        for row in results:
            bucket_start = row.bucket
            if isinstance(bucket_start, str):
                bucket_start = datetime.fromisoformat(bucket_start)
            if bucket_start.tzinfo is None:
                bucket_start = bucket_start.replace(tzinfo=timezone.utc)

            # Check if aggregate already exists
            existing = self.db.query(MetricsAggregate).filter_by(
                bucket_start=bucket_start,
                window=window.value,
                metric_type=metric_type,
                corps_id=row.corps_id,
                agent_role=row.agent_role,
            ).first()

            if existing and not force:
                continue

            # Calculate percentiles (approximate)
            percentiles = self._calculate_percentiles(
                metric_type,
                bucket_start,
                bucket_start + timedelta(seconds=window_seconds),
                corps_id or row.corps_id,
                agent_role or row.agent_role
            )

            aggregate = MetricsAggregate(
                bucket_start=bucket_start,
                window=window.value,
                metric_type=metric_type,
                corps_id=row.corps_id,
                agent_role=row.agent_role,
                count=row.count or 0,
                sum_value=row.sum_value,
                min_value=row.min_value,
                max_value=row.max_value,
                mean_value=row.mean_value,
                p50_value=percentiles.get("p50"),
                p95_value=percentiles.get("p95"),
                p99_value=percentiles.get("p99"),
            )
            self.db.add(aggregate)
            created += 1

        self.db.commit()
        return created

    def calculate_trends(
        self,
        metric_type: str,
        period_days: int = 7,
        end_time: Optional[datetime] = None,
        corps_id: Optional[str] = None,
        agent_role: Optional[str] = None
    ) -> Optional[MetricsTrend]:
        """Calculate trend for a metric over a period.

        Args:
            metric_type: Type of metric
            period_days: Number of days to analyze (7, 30, etc.)
            end_time: End of period (default: now)
            corps_id: Optional corps filter
            agent_role: Optional role filter

        Returns:
            MetricsTrend object or None if no data
        """
        from backend.services.metrics import MetricsEvent

        if end_time is None:
            end_time = datetime.now(timezone.utc)

        period_start = end_time - timedelta(days=period_days)
        prev_period_start = period_start - timedelta(days=period_days)

        # Current period average
        current_query = select(func.avg(MetricsEvent.value)).where(
            MetricsEvent.metric_type == metric_type,
            MetricsEvent.timestamp >= period_start,
            MetricsEvent.timestamp <= end_time,
            MetricsEvent.value.isnot(None)
        )

        if corps_id:
            current_query = current_query.where(MetricsEvent.corps_id == corps_id)
        if agent_role:
            current_query = current_query.where(MetricsEvent.agent_role == agent_role)

        current_avg = self.db.execute(current_query).scalar()

        # Previous period average
        prev_query = select(func.avg(MetricsEvent.value)).where(
            MetricsEvent.metric_type == metric_type,
            MetricsEvent.timestamp >= prev_period_start,
            MetricsEvent.timestamp < period_start,
            MetricsEvent.value.isnot(None)
        )

        if corps_id:
            prev_query = prev_query.where(MetricsEvent.corps_id == corps_id)
        if agent_role:
            prev_query = prev_query.where(MetricsEvent.agent_role == agent_role)

        prev_avg = self.db.execute(prev_query).scalar()

        # Calculate rate of change
        rate_of_change = None
        trend_direction = "flat"

        if current_avg is not None and prev_avg is not None and prev_avg != 0:
            rate_of_change = ((current_avg - prev_avg) / abs(prev_avg)) * 100
            if rate_of_change > 5:
                trend_direction = "up"
            elif rate_of_change < -5:
                trend_direction = "down"

        if current_avg is None:
            return None

        trend = MetricsTrend(
            period_start=period_start,
            period_end=end_time,
            period_days=period_days,
            metric_type=metric_type,
            corps_id=corps_id,
            agent_role=agent_role,
            avg_value=current_avg,
            prev_period_avg=prev_avg,
            rate_of_change=rate_of_change,
            trend_direction=trend_direction,
        )

        self.db.add(trend)
        self.db.commit()

        return trend

    def get_aggregates(
        self,
        metric_type: str,
        window: AggregateWindow,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        corps_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        limit: int = 1000
    ) -> List[MetricsAggregate]:
        """Query aggregated metrics.

        Args:
            metric_type: Type of metric
            window: Time window
            start_time: Start of time range
            end_time: End of time range
            corps_id: Filter by corps
            agent_role: Filter by role
            limit: Maximum results

        Returns:
            List of MetricsAggregate objects
        """
        query = select(MetricsAggregate).where(
            MetricsAggregate.metric_type == metric_type,
            MetricsAggregate.window == window.value,
        )

        if start_time:
            query = query.where(MetricsAggregate.bucket_start >= start_time)
        if end_time:
            query = query.where(MetricsAggregate.bucket_start <= end_time)
        if corps_id:
            query = query.where(MetricsAggregate.corps_id == corps_id)
        if agent_role:
            query = query.where(MetricsAggregate.agent_role == agent_role)

        query = query.order_by(MetricsAggregate.bucket_start.desc()).limit(limit)

        return self.db.execute(query).scalars().all()

    def cleanup_old_aggregates(
        self,
        retention_days: int = 30
    ) -> int:
        """Delete aggregates older than retention period.

        Args:
            retention_days: Keep aggregates from last N days

        Returns:
            Number of rows deleted
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        count = self.db.query(MetricsAggregate).filter(
            MetricsAggregate.created_at < cutoff
        ).delete()

        self.db.commit()
        return count

    # Private methods

    def _window_to_seconds(self, window: AggregateWindow) -> int:
        """Convert window enum to seconds."""
        mapping = {
            AggregateWindow.MINUTE: 60,
            AggregateWindow.FIVE_MINUTE: 300,
            AggregateWindow.HOUR: 3600,
            AggregateWindow.DAY: 86400,
        }
        return mapping[window]

    def _calculate_percentiles(
        self,
        metric_type: str,
        start_time: datetime,
        end_time: datetime,
        corps_id: Optional[str],
        agent_role: Optional[str]
    ) -> Dict[str, Optional[float]]:
        """Calculate percentiles for a metric in a time window."""
        from backend.services.metrics import MetricsEvent

        query = select(MetricsEvent.value).where(
            MetricsEvent.metric_type == metric_type,
            MetricsEvent.timestamp >= start_time,
            MetricsEvent.timestamp < end_time,
            MetricsEvent.value.isnot(None)
        )

        if corps_id:
            query = query.where(MetricsEvent.corps_id == corps_id)
        if agent_role:
            query = query.where(MetricsEvent.agent_role == agent_role)

        values = sorted([row[0] for row in self.db.execute(query).all()])

        if not values:
            return {"p50": None, "p95": None, "p99": None}

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
        }


def get_metrics_aggregator(db: Session) -> MetricsAggregator:
    """Get or create the metrics aggregator."""
    return MetricsAggregator(db)
