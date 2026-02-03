# Lets Build Some Metrics

## Goal
Transform the DCI swarm from a black box into a fully observable system with real-time visibility into system performance, corps health, agent efficiency, and bottleneck detection.

## Acceptance Criteria
1. MetricsDashboard.tsx page with summary cards, sparklines, time range selector (1h/6h/24h/7d), auto-refresh every 30s
2. ScoreboardsPage.tsx with sortable corps and agent leaderboards, drill-down on row click, medal badges for top 3
3. PerformanceExplorer.tsx with custom metric analysis, multi-series line chart, data export CSV/JSON
4. All three pages wired to backend API endpoints (GET /api/v1/metrics/dashboard, GET /api/v1/scoreboards/corps, /agents, /trends, GET /api/v1/metrics/series)
5. Real-time updates via WebSocket /ws/metrics or polling fallback
6. Status indicators: green (good), yellow (warning), red (critical)
7. MetricsCard, TrendChart, Leaderboard, AlertPanel components implemented
8. 20+ unit tests, 10+ integration tests, >80% coverage
9. Page load <2 seconds p95
10. TypeScript strict mode, zero console errors
11. Responsive: 1-col mobile, 2-col tablet, 3-col desktop
12. Field Commander Brutalism aesthetic: JetBrains Mono for data, IBM Plex Sans for labels

## Constraints
- No backend modifications (Movement III API endpoints are frozen)
- No new databases or LLM clients
- Use v1.ts for API calls
- Performance budget: page load <2s, API response <1s, chart render <500ms, memory <100MB