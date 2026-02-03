# OTEL Metrics to System Health Page

## Goal
Surface Claude Code's native OpenTelemetry metrics (token usage, cost, sessions, lines of code, commits, active time) on the existing `/system` page via Prometheus.

## Acceptance Criteria
1. `./dci ten-hut` starts Prometheus on port 9090 with OTLP receiver enabled
2. `./dci parade-rest` kills Prometheus
3. `./dci check-step` verifies Prometheus health
4. ClaudeCLIClient sets OTEL env vars when spawning claude CLI
5. `GET /api/v1/system/telemetry` returns current metric totals from Prometheus (503 when unavailable)
6. `GET /api/v1/system/telemetry/timeseries?metric=token_usage&range=1h&step=60` returns time-series data (503 when unavailable)
7. `frontend/src/services/v1.ts` has `getSystemTelemetry()` and `getSystemTelemetryTimeseries()` functions
8. SystemHealth.tsx shows telemetry panel with token counts, cost, sessions, LOC, active time
9. Telemetry panel polls every 15s
10. Graceful fallback when Prometheus is unavailable
11. `cd frontend && npx tsc --noEmit` compiles
12. `python -m pytest backend/tests/ -v` passes (no new failures)