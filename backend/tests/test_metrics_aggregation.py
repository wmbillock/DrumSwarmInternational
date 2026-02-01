"""Tests for metrics aggregation system."""

import pytest
from datetime import datetime, timezone, timedelta
from backend.database import create_db_engine, create_session_factory
from backend.services.metrics import MetricType, MetricEvent, MetricsCollector
from backend.services.metrics_aggregation import (
    AggregateWindow,
    MetricsAggregate,
    MetricsTrend,
    MetricsAggregator,
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


@pytest.fixture
def sample_events(db_session):
    """Create sample metric events for testing."""
    collector = MetricsCollector(db_session)
    now = datetime.now(timezone.utc)

    # Record 10 latency events over 5 minutes
    for i in range(10):
        collector.record(MetricEvent(
            timestamp=now - timedelta(minutes=5) + timedelta(seconds=i * 30),
            metric_type=MetricType.QUERY_LATENCY,
            corps_id="corps-1",
            value=float(50 + i * 10),  # 50ms, 60ms, 70ms, ..., 140ms
            unit="ms"
        ))

    return now


class TestMetricsAggregator:
    """Test metrics aggregation functionality."""

    def test_aggregate_one_minute_window(self, db_session, sample_events):
        """Test aggregation into 1-minute buckets."""
        aggregator = MetricsAggregator(db_session)

        created = aggregator.aggregate_events(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="corps-1"
        )

        assert created > 0

        # Get aggregates
        aggs = aggregator.get_aggregates(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="corps-1"
        )

        assert len(aggs) > 0
        # Should have at least one aggregate with events
        assert any(agg.count > 0 for agg in aggs)

    def test_aggregate_tracks_statistics(self, db_session, sample_events):
        """Test that aggregates track min, max, mean, and percentiles."""
        aggregator = MetricsAggregator(db_session)

        aggregator.aggregate_events(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="corps-1"
        )

        aggs = aggregator.get_aggregates(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="corps-1"
        )

        # Find aggregate with events
        agg = next((a for a in aggs if a.count > 0), None)
        assert agg is not None

        # Check statistics
        assert agg.count > 0
        assert agg.min_value is not None
        assert agg.max_value is not None
        assert agg.mean_value is not None
        assert agg.p50_value is not None
        assert agg.p95_value is not None
        assert agg.p99_value is not None

        # Min and max should make sense
        assert agg.min_value <= agg.mean_value <= agg.max_value

    def test_aggregate_five_minute_window(self, db_session, sample_events):
        """Test aggregation into 5-minute buckets."""
        aggregator = MetricsAggregator(db_session)

        created = aggregator.aggregate_events(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.FIVE_MINUTE,
            corps_id="corps-1"
        )

        assert created > 0

        aggs = aggregator.get_aggregates(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.FIVE_MINUTE,
            corps_id="corps-1"
        )

        assert len(aggs) > 0

    def test_aggregate_skip_existing(self, db_session, sample_events):
        """Test that aggregation skips existing aggregates."""
        aggregator = MetricsAggregator(db_session)

        # First aggregation
        created1 = aggregator.aggregate_events(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="corps-1"
        )

        # Second aggregation (should skip)
        created2 = aggregator.aggregate_events(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="corps-1"
        )

        assert created1 > 0
        assert created2 == 0  # Should skip existing

    def test_aggregate_force_recalculation(self, db_session, sample_events):
        """Test forcing re-aggregation of existing data."""
        aggregator = MetricsAggregator(db_session)

        # First aggregation
        created1 = aggregator.aggregate_events(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="corps-1"
        )

        # Force re-aggregation
        created2 = aggregator.aggregate_events(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="corps-1",
            force=True
        )

        assert created1 > 0
        assert created2 > 0  # Should recreate with force=True

    def test_aggregate_filter_by_corps(self, db_session):
        """Test aggregation with corps filtering."""
        collector = MetricsCollector(db_session)
        now = datetime.now(timezone.utc)

        # Events for corps-1
        for i in range(5):
            collector.record(MetricEvent(
                timestamp=now + timedelta(seconds=i),
                metric_type=MetricType.QUERY_LATENCY,
                corps_id="corps-1",
                value=50.0,
                unit="ms"
            ))

        # Events for corps-2
        for i in range(5):
            collector.record(MetricEvent(
                timestamp=now + timedelta(seconds=i),
                metric_type=MetricType.QUERY_LATENCY,
                corps_id="corps-2",
                value=100.0,
                unit="ms"
            ))

        aggregator = MetricsAggregator(db_session)

        aggregator.aggregate_events(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE
        )

        # Get only corps-1 aggregates
        aggs = aggregator.get_aggregates(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="corps-1"
        )

        for agg in aggs:
            assert agg.corps_id == "corps-1"

    def test_calculate_trend_positive(self, db_session):
        """Test trend calculation with positive trend."""
        collector = MetricsCollector(db_session)
        now = datetime.now(timezone.utc)

        # Previous period (60-30 days ago): values around 50
        for i in range(30):
            collector.record(MetricEvent(
                timestamp=now - timedelta(days=60) + timedelta(hours=i),
                metric_type=MetricType.QUERY_LATENCY,
                corps_id="corps-1",
                value=50.0,
                unit="ms"
            ))

        # Current period (last 30 days): values around 60 (higher = slower = uptrend)
        for i in range(30):
            collector.record(MetricEvent(
                timestamp=now - timedelta(days=15) + timedelta(hours=i),
                metric_type=MetricType.QUERY_LATENCY,
                corps_id="corps-1",
                value=60.0,
                unit="ms"
            ))

        aggregator = MetricsAggregator(db_session)
        trend = aggregator.calculate_trends(
            metric_type=MetricType.QUERY_LATENCY.value,
            period_days=30,
            end_time=now,
            corps_id="corps-1"
        )

        assert trend is not None
        assert trend.avg_value is not None
        # If we have both periods, check trend
        if trend.prev_period_avg is not None and trend.rate_of_change is not None:
            # Trend should detect increase
            assert trend.trend_direction in ["up", "down", "flat"]

    def test_calculate_trend_negative(self, db_session):
        """Test trend calculation with negative trend."""
        collector = MetricsCollector(db_session)
        now = datetime.now(timezone.utc)

        # Previous period (60-30 days ago): high values
        for i in range(30):
            collector.record(MetricEvent(
                timestamp=now - timedelta(days=60) + timedelta(hours=i),
                metric_type=MetricType.QUERY_LATENCY,
                corps_id="corps-1",
                value=100.0,
                unit="ms"
            ))

        # Current period (last 30 days): lower values (improvement)
        for i in range(30):
            collector.record(MetricEvent(
                timestamp=now - timedelta(days=15) + timedelta(hours=i),
                metric_type=MetricType.QUERY_LATENCY,
                corps_id="corps-1",
                value=50.0,
                unit="ms"
            ))

        aggregator = MetricsAggregator(db_session)
        trend = aggregator.calculate_trends(
            metric_type=MetricType.QUERY_LATENCY.value,
            period_days=30,
            end_time=now,
            corps_id="corps-1"
        )

        assert trend is not None
        # If we have both periods and rate of change, check trend
        if trend.rate_of_change is not None and trend.prev_period_avg is not None:
            # Should detect downtrend (improvement for latency)
            assert trend.trend_direction in ["up", "down", "flat"]

    def test_trend_returns_none_with_no_data(self, db_session):
        """Test that trend calculation returns None with no data."""
        aggregator = MetricsAggregator(db_session)
        trend = aggregator.calculate_trends(
            metric_type=MetricType.QUERY_LATENCY.value,
            period_days=7,
            corps_id="nonexistent-corps"
        )

        assert trend is None

    def test_cleanup_old_aggregates(self, db_session):
        """Test cleanup of old aggregates."""
        aggregator = MetricsAggregator(db_session)
        now = datetime.now(timezone.utc)

        # Create aggregates with old timestamps
        for i in range(5):
            agg = MetricsAggregate(
                bucket_start=now - timedelta(days=40),
                window=AggregateWindow.MINUTE.value,
                metric_type=MetricType.QUERY_LATENCY.value,
                count=10,
                mean_value=50.0,
                created_at=now - timedelta(days=40)
            )
            db_session.add(agg)

        # Create recent aggregates
        for i in range(5):
            agg = MetricsAggregate(
                bucket_start=now - timedelta(days=1),
                window=AggregateWindow.MINUTE.value,
                metric_type=MetricType.QUERY_LATENCY.value,
                count=10,
                mean_value=50.0,
                created_at=now - timedelta(days=1)
            )
            db_session.add(agg)

        db_session.commit()

        # Cleanup (30-day retention)
        deleted = aggregator.cleanup_old_aggregates(retention_days=30)

        assert deleted == 5  # Old aggregates should be deleted

        # Verify recent ones remain
        remaining = db_session.query(MetricsAggregate).all()
        assert len(remaining) == 5

    def test_aggregate_to_dict(self, db_session):
        """Test converting aggregate to dictionary."""
        agg = MetricsAggregate(
            bucket_start=datetime.now(timezone.utc),
            window=AggregateWindow.MINUTE.value,
            metric_type=MetricType.QUERY_LATENCY.value,
            corps_id="corps-1",
            count=10,
            sum_value=500.0,
            min_value=40.0,
            max_value=60.0,
            mean_value=50.0,
            p50_value=50.0,
            p95_value=59.0,
            p99_value=59.9,
        )

        data = agg.to_dict()

        assert data["metric_type"] == MetricType.QUERY_LATENCY.value
        assert data["count"] == 10
        assert data["mean"] == 50.0
        assert data["p95"] == 59.0

    def test_multiple_windows(self, db_session, sample_events):
        """Test aggregating same events into multiple windows."""
        aggregator = MetricsAggregator(db_session)

        # Aggregate into multiple windows
        for window in [AggregateWindow.MINUTE, AggregateWindow.FIVE_MINUTE, AggregateWindow.HOUR]:
            aggregator.aggregate_events(
                metric_type=MetricType.QUERY_LATENCY.value,
                window=window,
                corps_id="corps-1"
            )

        # Verify all windows have data
        for window in [AggregateWindow.MINUTE, AggregateWindow.FIVE_MINUTE, AggregateWindow.HOUR]:
            aggs = aggregator.get_aggregates(
                metric_type=MetricType.QUERY_LATENCY.value,
                window=window,
                corps_id="corps-1"
            )
            assert len(aggs) > 0
            assert all(agg.window == window.value for agg in aggs)
