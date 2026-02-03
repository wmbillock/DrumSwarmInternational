# Acceptance Checklist

- MetricsDashboard provides summary cards, sparklines, time range selector, and auto-refresh.
- ScoreboardsPage has sortable corps/agent leaderboards with medal badges and drill-down.
- PerformanceExplorer provides multi-series line chart and CSV/JSON exports.
- Metrics pages use existing v1 API calls without backend changes.
- Real-time updates attempt WebSocket `/ws/metrics` with polling fallback.
- Status indicators present for good/warning/critical thresholds.
- MetricsCard, TrendChart, Leaderboard, AlertPanel components implemented and used.
- Metrics test coverage includes 30+ component/page tests.
