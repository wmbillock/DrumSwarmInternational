# Lets Build Some Metrics - Movement IV Dashboard

## Objective
Build the frontend dashboard that visualizes metrics and performance data from the metrics collection pipeline (Movements I-III are complete). Implement three React pages with interactive charts, scoreboards, and real-time updates.

## Deliverables
- frontend/src/pages/MetricsDashboard.tsx: Summary cards with sparklines, time range selector (1h/6h/24h/7d), auto-refresh 30s, status indicators (green/yellow/red)
- frontend/src/pages/ScoreboardsPage.tsx: Sortable corps and agent leaderboards with drill-down, medal badges for top 3, pagination
- frontend/src/pages/PerformanceExplorer.tsx: Custom metric analysis, multi-series line chart, metric picker, data export CSV/JSON
- frontend/src/components/MetricsCard.tsx: Individual metric display with sparkline and status
- frontend/src/components/TrendChart.tsx: Multi-series line chart (Recharts wrapper)
- frontend/src/components/Leaderboard.tsx: Sortable ranked table with medal badges
- frontend/src/components/AlertPanel.tsx: Alert feed with dismissal and auto-cleanup
- 7 test files with >80% coverage
- All pages wired to existing backend API endpoints

## Constraints
- No backend modifications (Movement III endpoints frozen)
- No new databases or LLM clients
- Use v1.ts for API calls
- Performance: page load <2s, API <1s, chart render <500ms, memory <100MB
- Field Commander Brutalism: JetBrains Mono for data, IBM Plex Sans for labels
- Responsive: 1-col mobile, 2-col tablet, 3-col desktop

## Acceptance Criteria
- All three pages load with live data from backend API
- Interactive features work: sorting, filtering, time range, drill-down
- Real-time updates via WebSocket or polling (<1min lag)
- Status indicators correctly reflect data thresholds
- 20+ unit tests, 10+ integration tests passing
- TypeScript strict mode, zero console errors
- Page load <2 seconds p95