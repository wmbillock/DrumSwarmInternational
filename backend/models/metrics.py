"""DCI Swarm — Metrics ORM Models.

Extracted from backend/services/metrics.py and backend/services/metrics_aggregation.py
so all SQLAlchemy models live in backend/models/.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


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
