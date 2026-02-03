# Show Prompt: OTEL Metrics to System Health Page

## Objective
Surface Claude Code native OpenTelemetry metrics (token usage, cost, sessions, LOC, commits, active time) on the existing /system page via Prometheus. Create scripts/prometheus.yml, modify the dci CLI, backend system endpoints, frontend v1.ts client, and SystemHealth.tsx page.

## Deliverables
- scripts/prometheus.yml - Minimal Prometheus config with OTLP receiver
- dci CLI modifications - ten-hut starts Prometheus, parade-rest stops it, check-step verifies health
- backend/services/llm_client.py - OTEL env vars on ClaudeCLIClient subprocess calls
- backend/api/v1/system.py - GET /system/telemetry and GET /system/telemetry/timeseries endpoints
- frontend/src/services/v1.ts - getSystemTelemetry() and getSystemTelemetryTimeseries() functions
- frontend/src/pages/SystemHealth.tsx - Telemetry panel with polling and graceful fallback


You are implementing OpenTelemetry metrics integration for the DCI Swarm system. This involves 5 files across backend, frontend, and CLI.

## Context
- Project root: the git repo root (has `dci` CLI script, `backend/`, `frontend/` dirs)
- Backend is FastAPI at `backend/api/v1/`
- Frontend is React+TypeScript at `frontend/src/`
- CLI script is `./dci` (bash)
- The system page is at `frontend/src/pages/SystemHealth.tsx`
- V1 API client is at `frontend/src/services/v1.ts`
- LLM client is at `backend/services/llm_client.py`
- System routes are at `backend/api/v1/system.py`

## Step 1: Create `scripts/prometheus.yml`

Create a minimal Prometheus config file:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# No scrape targets needed - we receive metrics via OTLP push
scrape_configs: []
```

## Step 2: Modify `dci` CLI script

Find the `ten-hut` command handler and add Prometheus startup:
- Start Prometheus in background: `prometheus --config.file=scripts/prometheus.yml --web.listen-address=:9090 --web.enable-otlp-receiver --enable-feature=otlp-deltatocumulative &`
- Store PID in `.prometheus.pid`
- Echo status message

Find the `parade-rest` command handler and add:
- Kill Prometheus using stored PID file `.prometheus.pid`
- Clean up PID file

Find the `check-step` command handler and add:
- Check if Prometheus is running via `curl -s http://localhost:9090/-/healthy`
- Report status

## Step 3: Modify `backend/services/llm_client.py`

In the `ClaudeCLIClient` class, find where it spawns the `claude` subprocess (likely in a `run`, `execute`, `chat`, or `_run_cli` method). Add these environment variables to the subprocess env:

```python
import os

# In the method that calls subprocess/asyncio.create_subprocess_exec for claude:
env = os.environ.copy()
env.update({
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:9090/api/v1/otlp",
})
# Pass env=env to the subprocess call
```

Do NOT create a new LLM client. Only modify the existing ClaudeCLIClient.

## Step 4: Modify `backend/api/v1/system.py`

Add two new endpoints. Add `import httpx` at the top.

### GET /api/v1/system/telemetry

Query Prometheus for current totals:

```python
PROMETHEUS_URL = "http://localhost:9090"

@router.get("/system/telemetry")
async def get_system_telemetry():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            metrics = {}
            queries = {
                "token_usage": 'sum(claude_code_token_usage_total) or vector(0)',
                "cost_usd": 'sum(claude_code_cost_usd_total) or vector(0)',
                "sessions": 'sum(claude_code_sessions_total) or vector(0)',
                "lines_of_code": 'sum(claude_code_lines_of_code) or vector(0)',
                "commits": 'sum(claude_code_commits_total) or vector(0)',
                "active_time_seconds": 'sum(claude_code_active_time_seconds_total) or vector(0)',
            }
            for key, query in queries.items():
                resp = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
                data = resp.json()
                if data.get("status") == "success" and data.get("data", {}).get("result"):
                    metrics[key] = float(data["data"]["result"][0]["value"][1])
                else:
                    metrics[key] = 0.0
            return {"status": "ok", "metrics": metrics}
    except (httpx.ConnectError, httpx.TimeoutException):
        raise HTTPException(status_code=503, detail="Prometheus unavailable")
```

### GET /api/v1/system/telemetry/timeseries

```python
@router.get("/system/telemetry/timeseries")
async def get_system_telemetry_timeseries(
    metric: str = "token_usage",
    range: str = "1h",
    step: int = 60
):
    metric_map = {
        "token_usage": 'sum(claude_code_token_usage_total) or vector(0)',
        "cost_usd": 'sum(claude_code_cost_usd_total) or vector(0)',
        "sessions": 'sum(claude_code_sessions_total) or vector(0)',
        "lines_of_code": 'sum(claude_code_lines_of_code) or vector(0)',
        "commits": 'sum(claude_code_commits_total) or vector(0)',
        "active_time_seconds": 'sum(claude_code_active_time_seconds_total) or vector(0)',
    }
    query = metric_map.get(metric)
    if not query:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")
    try:
        import time
        end = time.time()
        # Parse range string like '1h', '30m', '24h'
        unit = range[-1]
        val = int(range[:-1])
        seconds = val * (3600 if unit == 'h' else 60 if unit == 'm' else 1)
        start = end - seconds

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{PROMETHEUS_URL}/api/v1/query_range", params={
                "query": query,
                "start": start,
                "end": end,
                "step": step
            })
            data = resp.json()
            if data.get("status") == "success":
                results = data.get("data", {}).get("result", [])
                points = []
                if results:
                    for ts, val in results[0].get("values", []):
                        points.append({"timestamp": ts, "value": float(val)})
                return {"status": "ok", "metric": metric, "points": points}
            return {"status": "ok", "metric": metric, "points": []}
    except (httpx.ConnectError, httpx.TimeoutException):
        raise HTTPException(status_code=503, detail="Prometheus unavailable")
```

Make sure to import HTTPException from fastapi if not already imported.

## Step 5: Modify `frontend/src/services/v1.ts`

Add these two functions (follow the existing patterns in the file for API_BASE, fetch calls, etc.):

```typescript
export async function getSystemTelemetry(): Promise<{
  status: string;
  metrics: {
    token_usage: number;
    cost_usd: number;
    sessions: number;
    lines_of_code: number;
    commits: number;
    active_time_seconds: number;
  };
}> {
  const res = await fetch(`${API_BASE}/system/telemetry`);
  if (!res.ok) throw new Error(`Telemetry fetch failed: ${res.status}`);
  return res.json();
}

export async function getSystemTelemetryTimeseries(
  metric: string = 'token_usage',
  range: string = '1h',
  step: number = 60
): Promise<{
  status: string;
  metric: string;
  points: Array<{ timestamp: number; value: number }>;
}> {
  const params = new URLSearchParams({ metric, range, step: String(step) });
  const res = await fetch(`${API_BASE}/system/telemetry/timeseries?${params}`);
  if (!res.ok) throw new Error(`Telemetry timeseries fetch failed: ${res.status}`);
  return res.json();
}
```

## Step 6: Modify `frontend/src/pages/SystemHealth.tsx`

Add a telemetry section to the existing page. Import the new v1.ts functions. Add state and polling:

```typescript
import { getSystemTelemetry } from '../services/v1';

// Inside the component:
const [telemetry, setTelemetry] = useState<any>(null);
const [telemetryError, setTelemetryError] = useState(false);

useEffect(() => {
  const fetchTelemetry = async () => {
    try {
      const data = await getSystemTelemetry();
      setTelemetry(data.metrics);
      setTelemetryError(false);
    } catch {
      setTelemetryError(true);
    }
  };
  fetchTelemetry();
  const interval = setInterval(fetchTelemetry, 15000);
  return () => clearInterval(interval);
}, []);
```

Render a telemetry panel section (use the existing page's styling patterns - the brutalist CSS theme):
- Title: "TELEMETRY (via Prometheus)"
- If telemetryError: show "Prometheus unavailable - telemetry data not collected" in a muted/warning style
- If telemetry data available, show a grid of metric cards:
  - Token Usage: `telemetry.token_usage.toLocaleString()`
  - Cost: `$${telemetry.cost_usd.toFixed(4)}`
  - Sessions: `telemetry.sessions`
  - Lines of Code: `telemetry.lines_of_code.toLocaleString()`
  - Commits: `telemetry.commits`
  - Active Time: format seconds to human readable (e.g., "2h 15m")
- Use CSS-only sparkline-style bars if desired (simple div with width proportional to value)
- Keep styling consistent with the existing brutalist theme on the page

## Important Constraints
- Do NOT create new files beyond `scripts/prometheus.yml`
- Do NOT install new npm packages
- Do NOT create new LLM clients
- Add `httpx` to backend requirements if not already present (check `requirements.txt` or `pyproject.toml` first - it may already be there)
- The `range` parameter name in the timeseries endpoint shadows a Python builtin - use it as-is for API simplicity but be aware
- All React hooks must be called before any early returns in components

## Verification Commands
```bash
cd frontend && npx tsc --noEmit
python -m pytest backend/tests/ -v
```