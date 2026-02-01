"""Tests for metrics collection system."""

import pytest
from datetime import datetime, timezone, timedelta
from backend.database import create_db_engine, create_session_factory
from backend.services.metrics import (
    MetricType,
    MetricEvent,
    MetricsEvent,
    MetricsCollector,
    record_event,
)


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_db_engine("sqlite:///:memory:")
    from backend.database import Base
    Base.metadata.create_all(engine)
    SessionLocal = create_session_factory(engine)
    session = SessionLocal()
    yield session
    session.close()


class TestMetricsCollector:
    """Test metrics collection and querying."""

    def test_record_event(self, db_session):
        """Test recording a single metric event."""
        collector = MetricsCollector(db_session)

        event = MetricEvent(
            timestamp=datetime.now(timezone.utc),
            metric_type=MetricType.REP_CREATED,
            corps_id="test-corps",
            rep_id="test-rep",
            value=1.0
        )

        collector.record(event)

        # Verify it was stored
        events = collector.get_events(metric_type=MetricType.REP_CREATED)
        assert len(events) == 1
        assert events[0].corps_id == "test-corps"
        assert events[0].rep_id == "test-rep"

    def test_filter_by_metric_type(self, db_session):
        """Test filtering events by metric type."""
        collector = MetricsCollector(db_session)
        now = datetime.now(timezone.utc)

        # Record multiple event types
        for i in range(3):
            collector.record(MetricEvent(
                timestamp=now + timedelta(seconds=i),
                metric_type=MetricType.REP_CREATED,
                corps_id="corps-1"
            ))

        for i in range(2):
            collector.record(MetricEvent(
                timestamp=now + timedelta(seconds=i),
                metric_type=MetricType.REP_COMPLETED,
                corps_id="corps-1"
            ))

        # Filter by type
        created = collector.get_events(metric_type=MetricType.REP_CREATED)
        completed = collector.get_events(metric_type=MetricType.REP_COMPLETED)

        assert len(created) == 3
        assert len(completed) == 2

    def test_filter_by_corps(self, db_session):
        """Test filtering events by corps."""
        collector = MetricsCollector(db_session)
        now = datetime.now(timezone.utc)

        # Record events for different corps
        collector.record(MetricEvent(
            timestamp=now,
            metric_type=MetricType.REP_CREATED,
            corps_id="corps-1"
        ))

        collector.record(MetricEvent(
            timestamp=now,
            metric_type=MetricType.REP_CREATED,
            corps_id="corps-2"
        ))

        # Filter by corps
        corps1_events = collector.get_events(corps_id="corps-1")
        corps2_events = collector.get_events(corps_id="corps-2")

        assert len(corps1_events) == 1
        assert len(corps2_events) == 1
        assert corps1_events[0].corps_id == "corps-1"

    def test_filter_by_time_range(self, db_session):
        """Test filtering events by time range."""
        collector = MetricsCollector(db_session)

        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)
        outside = now - timedelta(hours=2)

        # Record events at different times
        collector.record(MetricEvent(
            timestamp=outside,
            metric_type=MetricType.REP_CREATED,
            corps_id="corps-1"
        ))

        collector.record(MetricEvent(
            timestamp=now,
            metric_type=MetricType.REP_CREATED,
            corps_id="corps-1"
        ))

        # Query time range
        events = collector.get_events(
            start_time=start,
            end_time=end
        )

        assert len(events) == 1  # Only the event within range
        # Convert to UTC for comparison since database may return naive datetimes
        event_ts = events[0].timestamp
        if event_ts.tzinfo is None:
            event_ts = event_ts.replace(tzinfo=timezone.utc)
        assert event_ts <= end
        assert event_ts >= start

    def test_latency_percentiles(self, db_session):
        """Test latency percentile calculations."""
        collector = MetricsCollector(db_session)
        now = datetime.now(timezone.utc)

        # Record latency values: 10, 20, 30, 40, 50
        values = [10, 20, 30, 40, 50]
        for i, val in enumerate(values):
            collector.record(MetricEvent(
                timestamp=now + timedelta(seconds=i),
                metric_type=MetricType.QUERY_LATENCY,
                value=float(val),
                unit="ms",
                corps_id="corps-1"
            ))

        # Get percentiles
        stats = collector.get_latency_percentiles(
            MetricType.QUERY_LATENCY,
            corps_id="corps-1"
        )

        assert stats["count"] == 5
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["mean"] == 30.0
        assert stats["p50"] == 30.0  # median of 10,20,30,40,50
        assert stats["p95"] is not None
        assert stats["p99"] is not None

    def test_empty_latency_percentiles(self, db_session):
        """Test latency percentiles with no data."""
        collector = MetricsCollector(db_session)

        stats = collector.get_latency_percentiles(MetricType.QUERY_LATENCY)

        assert stats["count"] == 0
        assert stats["p50"] is None
        assert stats["p95"] is None
        assert stats["p99"] is None
        assert stats["min"] is None
        assert stats["max"] is None

    def test_throughput(self, db_session):
        """Test throughput calculation."""
        collector = MetricsCollector(db_session)

        now = datetime.now(timezone.utc)

        # Record 5 events at time T
        for i in range(5):
            collector.record(MetricEvent(
                timestamp=now,
                metric_type=MetricType.REP_COMPLETED,
                corps_id="corps-1"
            ))

        # Record 3 events at time T+60
        for i in range(3):
            collector.record(MetricEvent(
                timestamp=now + timedelta(seconds=60),
                metric_type=MetricType.REP_COMPLETED,
                corps_id="corps-1"
            ))

        # Get throughput with 60-second buckets
        throughput = collector.get_throughput(
            MetricType.REP_COMPLETED,
            interval_seconds=60,
            corps_id="corps-1"
        )

        assert len(throughput) == 2
        # First bucket should have 5 events
        assert throughput[0]["count"] == 5
        # Second bucket should have 3 events
        assert throughput[1]["count"] == 3

    def test_summary_metrics(self, db_session):
        """Test summary across metric types."""
        collector = MetricsCollector(db_session)
        now = datetime.now(timezone.utc)

        # Record various metric types
        for _ in range(3):
            collector.record(MetricEvent(
                timestamp=now,
                metric_type=MetricType.REP_CREATED,
                corps_id="corps-1"
            ))

        for _ in range(2):
            collector.record(MetricEvent(
                timestamp=now,
                metric_type=MetricType.REP_COMPLETED,
                corps_id="corps-1"
            ))

        # Get summary
        summary = collector.get_summary(corps_id="corps-1")

        assert summary[MetricType.REP_CREATED.value] == 3
        assert summary[MetricType.REP_COMPLETED.value] == 2

    def test_record_event_function(self, db_session):
        """Test the convenience record_event function."""
        now = datetime.now(timezone.utc)

        record_event(
            db_session,
            MetricType.REP_CREATED,
            corps_id="corps-1",
            rep_id="rep-1",
            value=42.5,
            unit="ms",
            tags={"test": "value"}
        )

        collector = MetricsCollector(db_session)
        events = collector.get_events(metric_type=MetricType.REP_CREATED)

        assert len(events) == 1
        assert events[0].rep_id == "rep-1"
        assert events[0].value == 42.5

    def test_concurrent_recording(self, db_session):
        """Test that multiple simultaneous records don't cause issues."""
        collector = MetricsCollector(db_session)
        now = datetime.now(timezone.utc)

        # Record multiple events rapidly
        for i in range(10):
            collector.record(MetricEvent(
                timestamp=now + timedelta(milliseconds=i),
                metric_type=MetricType.REP_CREATED,
                corps_id="corps-1",
                rep_id=f"rep-{i}"
            ))

        # All should be recorded
        events = collector.get_events(metric_type=MetricType.REP_CREATED)
        assert len(events) == 10

    def test_agent_session_metrics(self, db_session):
        """Test recording agent session metrics."""
        collector = MetricsCollector(db_session)
        now = datetime.now(timezone.utc)

        # Record agent session lifecycle
        collector.record(MetricEvent(
            timestamp=now,
            metric_type=MetricType.AGENT_SESSION_STARTED,
            corps_id="corps-1",
            agent_role="front_ensemble_tech",
            session_id="sess-1"
        ))

        collector.record(MetricEvent(
            timestamp=now + timedelta(seconds=300),
            metric_type=MetricType.AGENT_SESSION_COMPLETED,
            corps_id="corps-1",
            agent_role="front_ensemble_tech",
            session_id="sess-1",
            value=300.0,
            unit="seconds"
        ))

        # Filter by role
        events = collector.get_events(agent_role="front_ensemble_tech")
        assert len(events) == 2

        # Filter by session
        events = collector.get_events(session_id="sess-1")
        assert len(events) == 2

    def test_event_with_tags(self, db_session):
        """Test recording events with context tags."""
        collector = MetricsCollector(db_session)

        event = MetricEvent(
            timestamp=datetime.now(timezone.utc),
            metric_type=MetricType.REP_FAILED,
            corps_id="corps-1",
            rep_id="rep-1",
            tags={"error": "timeout", "retry_count": "3"}
        )

        collector.record(event)

        events = collector.get_events(rep_id="rep-1")
        assert len(events) == 1
        assert events[0].tags is not None
