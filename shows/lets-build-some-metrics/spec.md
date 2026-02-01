# Let's Build Some Metrics — Show Spec

## Overview

A comprehensive metrics and instrumentation system for the DCI Swarm, providing real-time visibility into:
- Task throughput and completion rates
- Agent activity and utilization
- Performance latency across operations
- Error rates and resilience patterns
- Corps health and progression metrics

## Show Concept

The DCI Swarm operates as a multi-agent orchestration system with complex interactions across corps, shows, seasons, and performances. Without instrumentation, we have no visibility into what's working, where bottlenecks exist, or how performance evolves over time. This show implements a complete metrics pipeline: from raw data collection to real-time dashboard visualization.

## Four-Movement Structure

### Movement I: Data Collection & Instrumentation
**Objective:** Instrument core swarm operations to capture raw performance metrics.

**Key Metrics to Collect:**
- **Task Metrics**
  - Rep completion rate (reps → completed / total reps)
  - Average rep duration (time from assigned → completed)
  - Rep status transitions (pending → assigned → in_progress → review → completed)
  - Rep failure rate and error patterns

- **Agent Metrics**
  - Agent session duration
  - Agent activity per session (messages sent, tools called, state transitions)
  - Agent utilization by role (active sessions / available agents)
  - Agent memory consumption and context snapshots

- **Corps Metrics**
  - Corps status progression (initializing → winter_camps → on_tour → completed)
  - Rehearsal mode transitions (basics → sectionals → full_ensemble → run_through)
  - Show completion rate per corps
  - Agent assignment success/failure

- **System-Level Metrics**
  - Message throughput (messages sent/received per minute)
  - Database query latency
  - Background task execution times (metronome ticks, archival, scoring)
  - Concurrent active sessions

**Deliverables:**
1. Instrumentation code in `backend/services/metrics.py` with:
   - `MetricsCollector` class for event recording
   - Event types enum (TASK_STARTED, TASK_COMPLETED, AGENT_SESSION_CREATED, etc.)
   - Database schema for metrics storage

2. Integration points in:
   - `backend/services/task_manager.py` — rep state changes
   - `backend/services/agent_runtime.py` — agent session lifecycle
   - `backend/api/app.py` — message throughput
   - `backend/database.py` — query timing

3. Structured logging with fields:
   - Timestamp, metric_type, corps_id, agent_role, value
   - Tags for slicing/filtering

### Movement II: Aggregation & Storage
**Objective:** Build the pipeline to aggregate raw metrics into time-series data.

**Key Responsibilities:**
- Time-series bucketing (1-min, 5-min, hourly aggregates)
- Percentile calculations (p50, p95, p99 latencies)
- Trend analysis and rate-of-change detection
- Data retention and archival (30-day rolling window)
- Query interface for analytics

**Deliverables:**
1. `backend/services/metrics_aggregation.py` with:
   - Time-series aggregation engine
   - Bucketing strategies
   - Query builder for common patterns

2. Metrics tables:
   - `metrics_events` (raw events)
   - `metrics_aggregates` (bucketed/aggregated data)
   - `metrics_alerts` (threshold violations)

### Movement III: Scoreboards & Leaderboards
**Objective:** Design and implement real-time scoreboards ranking corps and agents.

**Key Scoreboards:**
- **Corps Health Board** — Rank corps by show completion rate, agent utilization, avg task duration
- **Agent Leaderboard** — Top-performing agents by session count, avg task completion time, success rate
- **Performance Trends** — Weekly/monthly rollups showing velocity changes
- **Bottleneck Detection** — Operations exceeding p95 latency thresholds

**Deliverables:**
1. `backend/api/v1/scoreboards.py` with endpoints:
   - `GET /api/v1/scoreboards/corps` — Corps rankings
   - `GET /api/v1/scoreboards/agents` — Agent rankings
   - `GET /api/v1/scoreboards/trends` — Historical trends

2. Scoring algorithm with weighting:
   - Completion rate (40% weight)
   - Throughput (30% weight)
   - Latency (20% weight)
   - Error rate (10% weight)

### Movement IV: Dashboard & Visualization
**Objective:** Build the UI dashboard presenting live stats, charts, and scoreboard views.

**Key Pages:**
- **Metrics Dashboard** — Summary cards, trend sparklines, live feeds
- **Scoreboards Tab** — Corps and agent rankings with drill-down
- **Performance Explorer** — Time-range selector, metric picker, charting
- **Alerts Panel** — Threshold violations and anomaly detection

**Deliverables:**
1. Frontend pages in `frontend/src/pages/`:
   - `MetricsDashboard.tsx`
   - `ScoreboardsPage.tsx`
   - `PerformanceExplorer.tsx`

2. React components in `frontend/src/components/`:
   - `MetricsCard.tsx` — Summary cards
   - `TrendChart.tsx` — Sparklines and line charts
   - `Leaderboard.tsx` — Ranked tables
   - `AlertPanel.tsx` — Live alerts

## Acceptance Criteria

### Movement I: Data Collection & Instrumentation
- ✅ Metrics collection API is integrated into task lifecycle (rep state changes trigger events)
- ✅ Agent session metrics are recorded (start, activity, completion)
- ✅ Message throughput is tracked (threaded messages, broadcast messages)
- ✅ System metrics (database latency) are sampled at regular intervals
- ✅ At least 10 metric types are captured with proper timestamps and context

### Movement II: Aggregation & Storage
- ✅ Raw metrics are automatically bucketed into 1-min, 5-min, hourly windows
- ✅ Percentile calculations (p50, p95, p99) are available for all latency metrics
- ✅ Metrics are queryable by time range, metric type, and filter dimensions
- ✅ Data retention policy enforces 30-day rolling window (older data auto-deleted)
- ✅ Query performance for a 7-day window is <500ms

### Movement III: Scoreboards & Leaderboards
- ✅ Corps board ranks corps by composite score (shows completion, efficiency, quality)
- ✅ Agent board ranks agents by session count and task success rate
- ✅ Trend board shows 7-day and 30-day velocity changes
- ✅ Bottleneck detection identifies operations exceeding p95 latency
- ✅ Scoreboard updates reflect new events within 5 minutes

### Movement IV: Dashboard & Visualization
- ✅ Metrics dashboard loads in <2 seconds and displays live data
- ✅ Scoreboards tab shows current rankings and allows drill-down into agent/corps detail
- ✅ Performance explorer allows custom time ranges and metric selection
- ✅ Alert panel highlights threshold violations with timestamp and context
- ✅ UI updates automatically as new metrics arrive (WebSocket or polling)

## Technical Constraints

- **No new LLM clients** — Use existing `backend.api.app._task_manager.llm_client`
- **Metrics storage** — SQLite database (no external services)
- **Data freshness** — Aggregates refresh every 1 minute minimum
- **Performance** — Query APIs respond in <1 second for 7-day windows
- **Backward compatibility** — No changes to existing `Rep`, `AgentSession`, or `Corps` models

## Evaluation Rubric

| Dimension | Weight | Pass Threshold |
|-----------|--------|-----------------|
| **Functionality** | 50% | All 4 movements complete acceptance criteria (≥90%) |
| **Code Quality** | 25% | Well-structured, tested (>80% coverage), documented |
| **Operational** | 15% | <1s query latency, <5min aggregate refresh, 30-day retention |
| **Devil's Advocate** | 10% | Handles edge cases: concurrent writes, stale queries, data gaps |

**Show Pass Threshold: ≥78/100**

## Next Steps

1. Create sets and segments under each movement in the database
2. Assign reps to each segment
3. Implement in order: Data Collection → Aggregation → Scoreboards → Dashboard
4. Each movement must complete and pass review before next begins
