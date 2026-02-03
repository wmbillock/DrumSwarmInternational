## OTEL Metrics to System Health Page

Surface Claude Code native OpenTelemetry metrics on the existing /system page.

### Architecture
Claude Code CLI sessions (corps agents) → OTEL (http/protobuf) → Prometheus (with --web.enable-otlp-receiver) → PromQL via httpx → Backend proxy endpoint → JSON → SystemHealth.tsx (new telemetry panel)

No separate OTEL Collector — Prometheus receives OTLP directly.

### Acceptance Criteria
1. `scripts/prometheus.yml` exists with minimal config (global scrape_interval, no scrape targets needed)
2. `dci` CLI script modified: ten-hut starts Prometheus on port 9090 with --web.enable-otlp-receiver --enable-feature=otlp-deltatocumulative; parade-rest kills it; check-step verifies health
3. `backend/services/llm_client.py` ClaudeCLIClient sets OTEL env vars (CLAUDE_CODE_ENABLE_TELEMETRY=1, OTEL_METRICS_EXPORTER=otlp, OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf, OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:9090/api/v1/otlp) when spawning claude CLI
4. `backend/api/v1/system.py` has GET /api/v1/system/telemetry (current totals) and GET /api/v1/system/telemetry/timeseries (time-series for charts) using httpx.AsyncClient to query Prometheus; returns 503 gracefully when Prometheus unavailable
5. `frontend/src/services/v1.ts` has getSystemTelemetry() and getSystemTelemetryTimeseries(metric, range, step)
6. `frontend/src/pages/SystemHealth.tsx` has new SWARM TELEMETRY section with token counts, cost, sessions, LOC, active time, CSS-only sparklines, 15s polling, graceful fallback message

### Available Claude Code OTEL Metrics
- claude_code.session (session starts)
- claude_code.token.usage (type: input/output/cacheRead/cacheCreation, model)
- claude_code.cost.usage (model)
- claude_code.lines_of_code (type: added/removed)
- claude_code.commit (git commits)
- claude_code.pull_request (PRs created)
- claude_code.code_edit_tool.decision (accept/reject)
- claude_code.active_time (type: cli/user)