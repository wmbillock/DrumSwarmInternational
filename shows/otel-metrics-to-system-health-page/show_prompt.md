# Show Prompt: OTEL Metrics to System Health Page

## Objective
Surface Claude Code native OpenTelemetry metrics (token usage, cost, sessions, lines of code, commits, active time) on the existing /system page by routing metrics through Prometheus OTLP receiver and backend proxy endpoints.

## Architecture
Claude Code CLI sessions (corps agents) -> OTEL (http/protobuf) -> Prometheus (with --web.enable-otlp-receiver) -> PromQL via httpx -> Backend proxy endpoint -> JSON -> SystemHealth.tsx (new telemetry panel). No separate OTEL Collector.

## File Changes

### 1. NEW: scripts/prometheus.yml
Minimal Prometheus config:
global:
  scrape_interval: 15s
  evaluation_interval: 15s

### 2. MODIFY: dci (project root CLI script at /Users/mattbillock/Development/dci-swarm/dci)
Add PROMETHEUS_PORT variable near line 28: PROMETHEUS_PORT=${DCI_PROMETHEUS_PORT:-9090}

In cmd_ten_hut(), after frontend startup (after line 100), add Prometheus startup: check if prometheus command exists, kill_port, nohup prometheus with --config.file=$SCRIPTS_DIR/prometheus.yml --web.listen-address=:$PROMETHEUS_PORT --web.enable-otlp-receiver --enable-feature=otlp-deltatocumulative --storage.tsdb.retention.time=7d --storage.tsdb.path=$PROJECT_ROOT/.prometheus-data, log success or warn if not installed.

In cmd_parade_rest(), after orphaned agent kills (after line 125), add: kill_port $PROMETHEUS_PORT

In cmd_check_step(), after TMUX check, add Prometheus health check via curl http://localhost:$PROMETHEUS_PORT/-/healthy

### 3. MODIFY: backend/services/llm_client.py
In ClaudeCLIClient.chat(), before the subprocess.Popen call at ~line 350, build otel_env = os.environ.copy() with CLAUDE_CODE_ENABLE_TELEMETRY=1, OTEL_METRICS_EXPORTER=otlp, OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf, OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:9090/api/v1/otlp. Pass env=otel_env to BOTH Popen calls (initial ~line 350 and retry-resume ~line 392).

### 4. MODIFY: backend/api/v1/system.py
Add import httpx at top. Add PROMETHEUS_URL = http://localhost:9090. Add TELEMETRY_QUERIES dict mapping metric names to PromQL queries using claude_code_ prefix (underscores not dots). Add helper _extract_value(). Add async endpoint GET /system/telemetry returning tokens (input/output/cache_read/cache_creation), cost_usd, sessions, lines_of_code (added/removed), commits, pull_requests, active_time (cli_seconds/user_seconds). Use asyncio.gather for parallel Prometheus queries. Return 503 JSONResponse with available:false on ConnectError. Add async endpoint GET /system/telemetry/timeseries with params metric, range, step. Query Prometheus query_range API. Return series with labels and timestamp/value pairs.

PromQL queries: sum(claude_code_token_usage{type=input}) or vector(0), sum(claude_code_cost_usage) or vector(0), sum(claude_code_session) or vector(0), sum(claude_code_lines_of_code{type=added}) or vector(0), etc.

Add _parse_range() helper for range strings (s/m/h/d/w multipliers).

### 5. MODIFY: frontend/src/services/v1.ts
Add TelemetryData interface (available, tokens, cost_usd, sessions, lines_of_code, commits, pull_requests, active_time, detail). Add TimeseriesPoint (timestamp, value) and TimeseriesData (available, metric, range, step, series, detail) interfaces. Add getSystemTelemetry() and getSystemTelemetryTimeseries(metric, range, step) functions with .catch() returning {available:false}.

### 6. MODIFY: frontend/src/pages/SystemHealth.tsx
Add TelemetryData and TimeseriesData imports from v1. Add telemetry and tokenTimeseries state. Add fetchTelemetry callback using Promise.all. Update useEffect to call both fetchHealth and fetchTelemetry on 15s interval. Add formatNumber() (M/K formatting), formatDuration() (h/m/s), and Sparkline component (CSS-only bars, no chart library). Add SWARM TELEMETRY Panel after Corps Health panel. Show graceful fallback when telemetry unavailable. Show tokens, cost, sessions, code lines, active time in monospace. Show sparkline for token usage timeseries with color coding by type.

## Dependencies
httpx must be in backend dependencies. prometheus binary optional (graceful degradation).

## Testing
1. Backend starts without errors
2. GET /api/v1/system/telemetry returns available:false with 503 when Prometheus down
3. Frontend shows fallback message when telemetry unavailable
4. dci ten-hut starts Prometheus if installed
5. dci parade-rest kills Prometheus
6. dci check-step shows Prometheus status
7. TypeScript compiles: cd frontend && npx tsc --noEmit

## Deliverables
- scripts/prometheus.yml - New Prometheus config file
- dci - Modified CLI with Prometheus start/stop/check
- backend/services/llm_client.py - Modified with OTEL env vars on CLI subprocess
- backend/api/v1/system.py - Modified with telemetry and timeseries endpoints
- frontend/src/services/v1.ts - Modified with telemetry API functions and types
- frontend/src/pages/SystemHealth.tsx - Modified with SWARM TELEMETRY panel

## Constraints
- Do NOT modify existing endpoints, only add new ones
- Do NOT change existing SystemHealth component structure, only add new panel below
- Telemetry panel must degrade gracefully when Prometheus unavailable
- Use existing Panel component from ui module
- Match brutalist design aesthetic (monospace, uppercase labels, minimal color)
- httpx must be added to backend dependencies

## Acceptance Criteria
1. GET /api/v1/system/telemetry returns JSON with available:true when Prometheus up, 503 with available:false when down
2. GET /api/v1/system/telemetry/timeseries returns time-series data from Prometheus
3. SystemHealth page shows SWARM TELEMETRY panel with token counts, cost, sessions, LOC, active time
4. Fallback message shown when telemetry not configured
5. CSS-only sparklines render for token usage trend
6. dci CLI manages Prometheus lifecycle (start/stop/check)
7. Claude CLI sessions emit OTEL metrics via env vars
8. TypeScript compiles without errors
