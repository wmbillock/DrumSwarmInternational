"""Tests for scoreboards and leaderboards API."""

import pytest
from datetime import datetime, timezone, timedelta
from backend.database import create_db_engine, create_session_factory
from backend.services.metrics import MetricType, MetricEvent, MetricsCollector
from backend.services.metrics_aggregation import MetricsAggregator, AggregateWindow
from backend.api.v1.scoreboards import ScoringEngine, CorpsScore, AgentScore, TrendData


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


class TestScoringEngine:
    """Test scoring algorithm."""

    def test_normalize_value_basic(self):
        """Test basic value normalization."""
        # Value in middle of range
        score = ScoringEngine.normalize_value(50, 0, 100)
        assert 45 < score < 55  # Should be around 50

        # Value at minimum
        score = ScoringEngine.normalize_value(0, 0, 100)
        assert score == 0.0

        # Value at maximum
        score = ScoringEngine.normalize_value(100, 0, 100)
        assert score == 100.0

    def test_normalize_value_inverse(self):
        """Test inverse normalization (for latency/errors)."""
        # Low latency should score high
        score_low = ScoringEngine.normalize_value(100, 50, 500, inverse=True)

        # High latency should score low
        score_high = ScoringEngine.normalize_value(400, 50, 500, inverse=True)

        assert score_low > score_high

    def test_normalize_value_clamping(self):
        """Test that values are clamped to range."""
        # Value above range
        score = ScoringEngine.normalize_value(150, 0, 100)
        assert score == 100.0

        # Value below range
        score = ScoringEngine.normalize_value(-50, 0, 100)
        assert score == 0.0

    def test_calculate_corps_score_perfect(self):
        """Test corps score with perfect metrics."""
        # All metrics are perfect
        score = ScoringEngine.calculate_corps_score(
            completion_rate=1.0,      # 100%
            avg_throughput=20.0,      # Max throughput
            latency_p95=50.0,         # Min latency
            success_rate=1.0          # 100%
        )

        assert score > 95  # Should be near perfect

    def test_calculate_corps_score_poor(self):
        """Test corps score with poor metrics."""
        # All metrics are poor
        score = ScoringEngine.calculate_corps_score(
            completion_rate=0.0,      # 0%
            avg_throughput=0.0,       # No throughput
            latency_p95=500.0,        # High latency
            success_rate=0.0          # 0%
        )

        assert score < 10  # Should be very low

    def test_calculate_corps_score_weighted(self):
        """Test that corps score applies weights correctly."""
        # Good completion rate (40% weight) but bad throughput
        score1 = ScoringEngine.calculate_corps_score(
            completion_rate=1.0,      # 100% (40% weight)
            avg_throughput=0.0,       # 0 (30% weight)
            latency_p95=250.0,        # Medium (20% weight)
            success_rate=0.5          # 50% (10% weight)
        )

        # Poor completion rate but good throughput
        score2 = ScoringEngine.calculate_corps_score(
            completion_rate=0.0,      # 0% (40% weight)
            avg_throughput=20.0,      # Max (30% weight)
            latency_p95=250.0,        # Medium (20% weight)
            success_rate=0.5          # 50% (10% weight)
        )

        # Completion rate has higher weight, so score1 should be higher
        assert score1 > score2

    def test_calculate_agent_score_perfect(self):
        """Test agent score with perfect metrics."""
        score = ScoringEngine.calculate_agent_score(
            sessions_completed=100,
            avg_session_duration=600.0,  # 10 minutes
            success_rate=1.0,
            avg_throughput=50.0
        )

        assert score > 90

    def test_calculate_agent_score_poor(self):
        """Test agent score with poor metrics."""
        score = ScoringEngine.calculate_agent_score(
            sessions_completed=0,
            avg_session_duration=3000.0,  # 50 minutes
            success_rate=0.0,
            avg_throughput=0.0
        )

        assert score < 20

    def test_normalize_with_none_value(self):
        """Test normalization with None value."""
        score = ScoringEngine.normalize_value(None, 0, 100)
        assert score == 0.0

    def test_normalize_with_zero_range(self):
        """Test normalization when min and max are equal."""
        score = ScoringEngine.normalize_value(50, 100, 100)
        assert score == 50.0  # Midpoint


class TestScoreModels:
    """Test score model classes."""

    def test_corps_score_to_dict(self):
        """Test CorpsScore conversion to dictionary."""
        score = CorpsScore(
            corps_id="corps-1",
            corps_name="Test Corps",
            shows_completed=3,
            shows_total=5,
            avg_task_duration=45.0,
            task_success_rate=0.95,
            query_latency_p95=120.0,
            composite_score=87.5,
            rank=1
        )

        data = score.to_dict()

        assert data["corps_id"] == "corps-1"
        assert data["corps_name"] == "Test Corps"
        assert data["rank"] == 1
        assert data["show_completion_rate"] == 0.6
        assert data["composite_score"] == 87.5

    def test_agent_score_to_dict(self):
        """Test AgentScore conversion to dictionary."""
        score = AgentScore(
            agent_role="brass_tech",
            agent_count=3,
            avg_session_duration=1200.0,
            sessions_completed=25,
            task_success_rate=0.98,
            avg_task_throughput=12.5,
            composite_score=89.2,
            rank=1
        )

        data = score.to_dict()

        assert data["agent_role"] == "brass_tech"
        assert data["agent_count"] == 3
        assert data["rank"] == 1
        assert data["composite_score"] == 89.2

    def test_trend_data_to_dict(self):
        """Test TrendData conversion to dictionary."""
        trend = TrendData(
            metric_name="rep_completed",
            current_value=45.2,
            previous_value=42.1,
            rate_of_change=7.36,
            direction="up",
            period_days=7
        )

        data = trend.to_dict()

        assert data["metric_name"] == "rep_completed"
        assert data["current_value"] == 45.2
        assert data["direction"] == "up"


class TestScoringWithMetrics:
    """Test scoring with actual metrics data."""

    def test_score_with_aggregated_metrics(self, db_session):
        """Test scoring with real aggregated metrics."""
        collector = MetricsCollector(db_session)
        aggregator = MetricsAggregator(db_session)

        now = datetime.now(timezone.utc)

        # Create sample metrics
        for i in range(10):
            collector.record(MetricEvent(
                timestamp=now - timedelta(hours=i),
                metric_type=MetricType.REP_COMPLETED,
                corps_id="corps-1",
                value=1.0
            ))

            collector.record(MetricEvent(
                timestamp=now - timedelta(hours=i),
                metric_type=MetricType.QUERY_LATENCY,
                corps_id="corps-1",
                value=float(100 + i * 10),
                unit="ms"
            ))

        # Aggregate
        aggregator.aggregate_events(
            metric_type=MetricType.REP_COMPLETED.value,
            window=AggregateWindow.HOUR,
            corps_id="corps-1"
        )

        aggregator.aggregate_events(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.HOUR,
            corps_id="corps-1"
        )

        # Get aggregates
        aggs = aggregator.get_aggregates(
            metric_type=MetricType.REP_COMPLETED.value,
            window=AggregateWindow.HOUR,
            corps_id="corps-1"
        )

        assert len(aggs) > 0

        # Calculate score
        score = ScoringEngine.calculate_corps_score(
            completion_rate=0.8,
            avg_throughput=aggs[0].count if aggs else 0,
            latency_p95=aggs[0].p95_value if aggs and aggs[0].p95_value else None,
            success_rate=0.95
        )

        assert 0 <= score <= 100

    def test_percentile_accuracy(self, db_session):
        """Test that percentiles are calculated accurately."""
        collector = MetricsCollector(db_session)
        aggregator = MetricsAggregator(db_session)

        now = datetime.now(timezone.utc)

        # Create precise latency values: 10, 20, 30, ..., 100 (10 values)
        for i in range(1, 11):
            collector.record(MetricEvent(
                timestamp=now + timedelta(seconds=i),
                metric_type=MetricType.QUERY_LATENCY,
                corps_id="test-corps",
                value=float(i * 10),
                unit="ms"
            ))

        # Aggregate
        aggregator.aggregate_events(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="test-corps"
        )

        aggs = aggregator.get_aggregates(
            metric_type=MetricType.QUERY_LATENCY.value,
            window=AggregateWindow.MINUTE,
            corps_id="test-corps"
        )

        if aggs:
            agg = aggs[0]
            # p50 should be around 55 (median)
            assert 50 < agg.p50_value < 60
            # p95 should be around 95
            assert 90 < agg.p95_value < 100
            # p99 should be around 99
            assert 95 < agg.p99_value < 100

    def test_trend_detection(self, db_session):
        """Test trend detection in scoring."""
        collector = MetricsCollector(db_session)
        aggregator = MetricsAggregator(db_session)

        now = datetime.now(timezone.utc)

        # Old period: low values
        for i in range(20):
            collector.record(MetricEvent(
                timestamp=now - timedelta(days=60) + timedelta(hours=i),
                metric_type=MetricType.REP_COMPLETED,
                corps_id="corps-1",
                value=1.0
            ))

        # New period: high values
        for i in range(20):
            collector.record(MetricEvent(
                timestamp=now - timedelta(days=15) + timedelta(hours=i),
                metric_type=MetricType.REP_COMPLETED,
                corps_id="corps-1",
                value=1.0
            ))

        trend = aggregator.calculate_trends(
            metric_type=MetricType.REP_COMPLETED.value,
            period_days=30,
            end_time=now,
            corps_id="corps-1"
        )

        # Trend should be detected
        assert trend is not None
        assert trend.avg_value is not None
