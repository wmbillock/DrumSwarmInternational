# "Let's Build Some Metrics" — Complete Brief

## Show Concept

Transform the DCI Swarm from a **black box** to an **observable system**. This four-movement show reveals the hidden mechanics of agent execution, data aggregation, and performance scoring through real-time dashboards, metric cascades, and visual data formations. By the finale, the audience (operators, directors, engineers) can see every agent action, metric calculation, and system state change flowing across the stage as a living, breathing performance.

**The metaphor**: Just as a DCI corps executes drill formations to reveal music, the metrics show executes data formations to reveal system behavior.

---

## Musical Design

### Movement I: The Black Box (Exposition)
**Role**: Data Collection & Metric Initialization
**Owned by**: Backend Services (metric writers)

Corps opens in darkness. Single agent (spotlight) performs isolated tasks in a "black box" — users can't see what's happening inside. By the end of this movement, the box begins to crack open as raw metric data starts flowing into buckets.

**Success Metric**: All 6 metric categories (latency, throughput, errors, resources, agents, tasks) are bucketed into P50/P95/P99 percentiles and persisted to the metrics store.

### Movement II: Bucketing & Aggregation (Development)
**Role**: Time-Series Data Retention & Percentile Calculation
**Owned by**: Backend Services (metric aggregators)

Data flows backward through time in synchronized lines. Each of the 6 metric lines compresses into tighter formations representing percentile groupings (P50 tight and near, P99 sparse and distant). Rhythmic pulses represent time-series window decay as old data rolls off and new data arrives.

**Success Metric**: Percentile calculations (P50, P95, P99) are correct across all buckets. Time-series retention respects decay rules (48-hour window default). Dashboard receives live updates every 5 seconds.

### Movement III: Leaderboard & Ranking (Recapitulation)
**Role**: Composite Score Calculation & Rank Ordering
**Owned by**: Backend Services (scoreboard writers)

The 6 metric lines merge into 2 axis formations (X: corps rank, Y: metric health). Color-coded flag states show health (green/yellow/red). Guard tosses equipment representing rank changes, synchronized to the composite score calculation algorithm.

**Success Metric**: Leaderboard correctly ranks all active corps by composite score (weighted: 40% latency, 30% throughput, 20% error rate, 10% resource utilization). Rank changes propagate to frontend within 1 second of calculation.

### Movement IV: The Observable System (Coda)
**Role**: Dashboard Visualization & Real-Time State Broadcast
**Owned by**: Frontend + WebSocket Integration

Guard plants flags in final rank-ordered formation (medal podium geometry). Flags become **living dashboards** — color ripples flow across them showing real-time metric updates, system health status changes, and agent state transitions. The audience sees the complete system state at a glance: who's ranked first, which agents are working, what metrics are trending, and overall system health (ok/warning/error).

**Success Metric**: Dashboard loads in <2 seconds, updates metrics in <500ms after backend calculation, supports 50+ concurrent viewers without degradation. All 6 metrics visible + composite score + health indicator. Real-time WebSocket connection sustains 24+ hours without reconnect.

---

## Visual Design

### Aesthetic: Field Commander Brutalism
**Typography**:
- **Headers**: JetBrains Mono Bold (monospace, authoritative)
- **Body**: IBM Plex Sans (readable, professional)
- **Data displays**: JetBrains Mono Regular (code-like, precise)

**Color System**:
- **Stage colors** (health indicators):
  - 🟢 **Green**: System ok, metric within target
  - 🟡 **Yellow**: Warning, metric approaching threshold
  - 🔴 **Red**: Error, metric exceeded or agent stalled
- **Data colors** (metric categories):
  - Latency: Blue spectrum (cool = slow data)
  - Throughput: Green spectrum (growth = speed)
  - Errors: Red spectrum (danger = failures)
  - Resources: Orange spectrum (heat = utilization)
  - Agents: Purple spectrum (agency = action)
  - Tasks: Gray spectrum (neutral = work units)

**Responsive Breakpoints**:
- **Mobile** (<768px): Single-column, condensed metric cards, touch-friendly
- **Tablet** (768-1200px): Two-column metric grid, sidebar navigation
- **Desktop** (>1200px): Three-column dashboard with full leaderboard, live feed, and settings panel

**Visual Patterns**:
- Metric cards: Monospace numbers, left-aligned, subtle background gradient (stage colors fading)
- Leaderboard: Rank badges (1st=gold, 2nd=silver, 3rd=bronze), sortable columns, hover state highlights
- Real-time updates: Smooth color transitions (300ms ease), number animations (typewriter effect), ripple effects on change
- Empty states: Placeholder formations showing data will arrive

---

## Guard Design

### Role-Based Access Control

**Hierarchy** (top → bottom):
1. **Director** — Full system access, can start/stop metronome, archive all data, export metrics
2. **Program Coordinator** — Can view all metrics, manage dashboard settings, create custom alerts
3. **Caption Head** — Can view metrics for their section only (e.g., color guard metrics)
4. **Performer** — Read-only: their own performance metrics only

### Data Privacy Rules

- Performers **cannot** see metrics for other performers
- Caption Heads **cannot** see metrics outside their section
- All users **cannot** see internal LLM tokens, agent system prompts, or raw API responses
- Directors **can** see everything but must audit their own access

### Implementation Details

- **JWT tokens** carry role + section_id
- **Query guards** in V1 API check role + section_id before returning data
- **WebSocket messages** are filtered by role (subscribers only receive metrics they're authorized to see)
- **Audit logging** tracks who accessed what metrics when (stored in `audit_log` table)

---

## General Effect

### Purpose
Enable operators and engineers to **understand, debug, and optimize** the DCI Swarm's autonomous agent execution in real time. Replace the black-box "agent is working" feeling with precise visibility into:
- What each agent is doing (task queue, current work)
- How fast data flows through the system (latency, throughput)
- Whether the system is healthy (error rates, resource utilization)
- Which corps are performing best (leaderboard, composite scores)

### Stakeholder Impact

| Stakeholder | Impact |
|-------------|--------|
| **Director** | Sees system health at a glance; can trigger recovery actions (metronome reset, agent restart) |
| **Program Coordinator** | Debugs stuck workflows by tracing metric anomalies back to agent logs |
| **Engineers** | Identify performance bottlenecks via percentile heatmaps; optimize allocation algorithms |
| **Operators** | Know immediately when to escalate (red flags trigger alerts) |

### Measurable Success Criteria

1. **Functionality**: All 6 metrics visible on dashboard within 5 seconds of system startup
2. **Accuracy**: Percentile calculations match ground truth (tested against 1000+ sample datasets)
3. **Latency**: Metric update from backend calculation to frontend display <500ms (p99)
4. **Reliability**: Dashboard sustains 24+ hours uptime without reconnect; WebSocket recovery <5 seconds
5. **Usability**: New operator can find their corps' metrics in <30 seconds (user test)
6. **Scale**: Dashboard supports 100+ concurrent viewers without server degradation

### Visual Feedback System

- **Metric cards** pulse on update (subtle animation)
- **Leaderboard** highlights rank changes with color flash
- **Health indicator** (top-right) changes color before any alert modal (green → yellow → red)
- **Timestamp** on each metric card shows last update (e.g., "updated 2 seconds ago")
- **Toast notifications** appear for critical alerts (red flags only)

---

## Constraints

### Technical Guardrails

- **No new LLM clients**: Use existing shared LLM client in `backend/services/llm_client.py`
- **No backend modifications**: V1 API is locked. All dashboard endpoints (GET only) already exist.
- **No database schema changes**: Add metrics to existing `metrics` table; do not create new tables
- **WebSocket only**: Use existing `/ws` endpoint; do not create new socket connections

### Performance Guardrails

- **Metric calculation**: <200ms per calculation (p99) — must not block agent execution
- **Dashboard load**: <2 seconds cold start, <500ms warm load
- **WebSocket messages**: <5 messages per second per metric (prevent message spam)
- **Frontend memory**: <50MB for dashboard state (no storing entire history in memory)

### Code Quality Guardrails

- **Test coverage**: >80% for all new metric calculation logic
- **Type safety**: 100% TypeScript strict mode for frontend; 100% type hints for backend metrics module
- **Accessibility**: WCAG 2.1 AA for dashboard (color contrast, keyboard navigation, screen reader support)
- **Documentation**: Every metric calculation has a docstring explaining the algorithm

### Operational Guardrails

- **Backward compatibility**: Metric schema must support rollback to N-1 version (add fields, don't remove)
- **Monitoring**: Metronome tracks metric calculation failures; alert if >1% fail over 5 minutes
- **Graceful degradation**: If metric calculation stalls, dashboard shows "calculating..." instead of crashing
- **No manual intervention**: All metric calculations must be fully automated (no operator button clicks)

---

## Deliverables

### Movement I: Data Collection & Metric Initialization
- **Backend**:
  - `backend/services/metrics/collector.py` (150 lines): Collect raw metrics from agents, API endpoints, database
  - `backend/services/metrics/bucketer.py` (120 lines): Bucket metrics into time windows (5s, 1m, 5m buckets)
  - `backend/api/v1/metrics/raw.py` (80 lines): GET endpoints for raw metric data
  - Unit tests: 30+ test cases covering bucketing logic, edge cases (empty buckets, duplicates)
- **Expected test coverage**: 85%+

### Movement II: Time-Series Aggregation & Percentile Calculation
- **Backend**:
  - `backend/services/metrics/aggregator.py` (200 lines): Aggregate bucketed data, calculate P50/P95/P99
  - `backend/services/metrics/retention.py` (100 lines): Implement time-series decay (48-hour window)
  - `backend/api/v1/metrics/percentiles.py` (80 lines): GET endpoints for percentile data
  - `backend/database.py` migration: Add `metric_history` table for time-series storage
  - Unit tests: 40+ test cases covering percentile algorithms, window decay, edge cases
  - Integration tests: 10+ tests validating end-to-end data flow
- **Expected test coverage**: 90%+

### Movement III: Leaderboard & Rank Ordering
- **Backend**:
  - `backend/services/metrics/scorer.py` (180 lines): Composite score calculation (weighted by metric category)
  - `backend/api/v1/metrics/leaderboard.py` (100 lines): GET endpoints for leaderboard data (ranked, filterable by corps/section)
  - Scoring algorithm tests: 25+ test cases for weight validation, rank stability
- **Frontend**:
  - `frontend/src/components/Leaderboard.tsx` (150 lines): Render leaderboard table with sorting, filtering
  - Unit tests: 15+ test cases for sorting, filtering, UI state
- **Expected test coverage**: 85%+ backend, 80%+ frontend

### Movement IV: Dashboard Visualization & Real-Time Broadcast
- **Frontend**:
  - `frontend/src/pages/MetricsDashboard.tsx` (300 lines): Main dashboard page with 6 metric cards, leaderboard, health indicator
  - `frontend/src/components/MetricCard.tsx` (120 lines): Individual metric card with animation, timestamp, update pulse
  - `frontend/src/components/HealthIndicator.tsx` (80 lines): System health color indicator with state transitions
  - `frontend/src/services/metricsWebSocket.ts` (150 lines): WebSocket client for real-time metric updates
  - Integration tests: 20+ test cases for WebSocket connectivity, message handling, state synchronization
  - Visual regression tests: 5+ baseline screenshots for responsive design validation
- **Backend**:
  - WebSocket handler in `backend/api/app.py` (already exists, extend broadcast logic): Broadcast metric updates to all connected dashboard clients
  - Performance monitoring: Track WebSocket message latency, client count, message throughput
- **Expected test coverage**: 80%+ frontend, 75%+ WebSocket integration

### Cross-Movement Deliverables
- **Documentation**:
  - `docs/metrics/README.md`: Overview of metrics system, data model, calculation algorithms
  - `docs/metrics/api.md`: Complete API reference for all metrics endpoints (movements I-III)
  - `docs/metrics/dashboard.md`: Frontend guide for MetricsDashboard, component architecture, WebSocket integration
  - `docs/metrics/calculation.md`: Detailed breakdown of composite score formula, percentile algorithms, decay rules
- **Tests**:
  - End-to-end test: Agent performs work → metric collected → percentile calculated → leaderboard updated → dashboard rendered (1 integration test covering all 4 movements)
  - Performance test: 1000 concurrent metric updates with <500ms dashboard latency (1 performance test)
  - Accessibility test: Dashboard passes WCAG 2.1 AA scan (1 automated test via axe-core)

---

## Evaluation Rubric

**Passing score**: 78/100 (all movements must function end-to-end)

| Category | Weight | Criteria | Points |
|----------|--------|----------|--------|
| **Functionality** | 50% | All 6 metrics displayed; percentiles calculated correctly; leaderboard ranked accurately; dashboard updates <500ms | 50 |
| **Code Quality** | 25% | >85% test coverage; <3 code review findings; type-safe throughout; docstrings on all calculations | 25 |
| **Operational** | 15% | Zero unhandled exceptions in WebSocket; metronome tracks metric calc failures; graceful degradation if data stales >5s | 15 |
| **Edge Cases** | 10% | Handles empty metric buckets; P99 with <100 samples; rank ties; client disconnect/reconnect; 48-hour retention cutoff | 10 |

**Scoring Breakdown**:
- **50 pts (Functionality)**: All 4 movements complete, end-to-end data flow, <2s dashboard load, <500ms update latency
- **25 pts (Code Quality)**: >85% test coverage, TypeScript strict, clean architecture (metrics module separate), professional docs
- **15 pts (Operational)**: Metronome integration, graceful degradation, no crashes, audit logging
- **10 pts (Edge Cases)**: Tested with edge-case datasets, rank ties handled, WebSocket reconnect tested, retention decay validated

---

## Next Steps (Implementation Roadmap)

### Phase 1: Movement I (Week 1)
- [ ] Implement `metrics/collector.py` — gather raw data from agents, API
- [ ] Implement `metrics/bucketer.py` — time-window bucketing
- [ ] Write collector + bucketer unit tests (30+ cases)
- [ ] Implement raw metrics API endpoints
- [ ] Verify raw metric data flows into database

### Phase 2: Movement II (Week 2)
- [ ] Implement `metrics/aggregator.py` — percentile calculation
- [ ] Implement `metrics/retention.py` — time-series decay
- [ ] Add `metric_history` database table + migration
- [ ] Write aggregator unit tests (40+ cases)
- [ ] Write integration tests (10+ cases)
- [ ] Implement percentile API endpoints
- [ ] Verify percentiles match ground truth (1000 sample validation)

### Phase 3: Movement III (Week 3)
- [ ] Implement `metrics/scorer.py` — composite score calculation
- [ ] Write scorer unit tests (25+ cases)
- [ ] Implement leaderboard API endpoint
- [ ] Implement frontend `Leaderboard.tsx` component
- [ ] Write frontend unit tests (15+ cases)
- [ ] Verify leaderboard sorts correctly under rank changes

### Phase 4: Movement IV (Week 4)
- [ ] Implement `MetricsDashboard.tsx` — main dashboard page
- [ ] Implement `MetricCard.tsx` — individual metric cards with animations
- [ ] Implement `HealthIndicator.tsx` — health color indicator
- [ ] Implement `metricsWebSocket.ts` — WebSocket client for real-time updates
- [ ] Extend WebSocket handler in `app.py` to broadcast metrics
- [ ] Write integration tests (20+ cases)
- [ ] Write visual regression tests (5+ baselines)
- [ ] Performance test: <500ms update latency, 1000 concurrent metrics
- [ ] Accessibility test: WCAG 2.1 AA scan pass
- [ ] Documentation: README, API guide, dashboard guide, calculation guide
- [ ] End-to-end test: Agent work → dashboard display
- [ ] Final rubric evaluation

---

---

## Swarm Prompt

### Executive Summary

**Show**: "Let's Build Some Metrics" — Transform DCI Swarm from black box to observable system through four movements of progressive data visibility and real-time dashboards.

**Agent Assignments**:
- **Movement I (Data Collection)**: Backend Services Agent (metrics collector)
- **Movement II (Aggregation)**: Backend Services Agent (metric aggregator)
- **Movement III (Leaderboard)**: Backend Services Agent + Frontend Agent (scoring + UI)
- **Movement IV (Dashboard)**: Frontend Agent + WebSocket Integration Agent (real-time visualization)

**Timeline**: 4 weeks | **Passing Threshold**: 78/100 points
**Architecture Constraint**: No new LLM clients, no backend schema changes, WebSocket-only real-time, all endpoints already exist in V1 API

---

### Movement I: Data Collection & Metric Initialization (Week 1)

**Owner**: Backend Services Agent

**Context**: The DCI Swarm system has no instrumentation. Reps transition through states (pending → assigned → in_progress → review → completed), agents execute work, and messages flow through the system, but there's no visibility into *how long* things take, *how fast* data flows, or *where* failures happen.

**Objective**: Build the metrics collection layer — capture raw data from agents, API endpoints, and database, then bucket it into time windows (5s, 1m, 5m intervals).

**Deliverables**:
1. **`backend/services/metrics/collector.py`** (150 lines)
   - `MetricType` enum (latency, throughput, errors, resources, agents, tasks)
   - `MetricEvent` dataclass (timestamp, metric_type, value, metadata)
   - `MetricsCollector` class with `record_event()`, `query_events()` methods
   - Hook into rep lifecycle: `rep_service.transition_rep()`, `agent_runtime.py` session lifecycle, `messaging_service.py` message creation
   - Hook into database query tracking for latency metrics

2. **`backend/services/metrics/bucketer.py`** (120 lines)
   - Time-window bucketing logic (5s, 1m, 5m buckets)
   - `BucketedMetric` dataclass (bucket_start, bucket_end, metric_type, values[])
   - `bucket_events()` function to compress raw events into time windows

3. **`backend/api/v1/metrics/raw.py`** (80 lines)
   - GET `/api/v1/metrics/raw?metric_type=latency&time_range=1h` — return raw events
   - GET `/api/v1/metrics/buckets?metric_type=latency&window=5s&time_range=1h` — return bucketed data
   - Filtered by user role (query guards check JWT permissions)

4. **Database**:
   - Create `metrics_events` table (immutable append-only event log):
     - `id, timestamp, metric_type, value, corpus_id, agent_id, segment_id, metadata (JSON)`
   - Index on: `(timestamp, metric_type, corpus_id)` for fast range queries

5. **Tests**:
   - Unit: `test_metrics_collection.py` — 30+ test cases (event recording, filtering by metric type/time/corpus, bucketing logic)
   - Integration: Rep transitions → events recorded; Agent session created → event recorded
   - Coverage: 85%+

**Success Criteria**:
- [ ] All 6 metric categories are being recorded (latency, throughput, errors, resources, agents, tasks)
- [ ] Raw metrics queryable by time range, metric type, corpus_id, agent_id
- [ ] Bucketed metrics correctly compress raw events (sum, avg, count per bucket)
- [ ] <5ms query latency for 1-hour range queries (p99)
- [ ] No performance regression to agent execution (metrics recording is async)

**Acceptance Tests**:
```bash
# Agent performs work → metric recorded
pytest backend/tests/test_metrics_collection.py -v

# Query raw metrics and verify event count
curl "http://localhost:8000/api/v1/metrics/raw?metric_type=latency&time_range=1h" | jq '.events | length'

# Query bucketed metrics
curl "http://localhost:8000/api/v1/metrics/buckets?metric_type=latency&window=5s" | jq '.buckets'
```

---

### Movement II: Time-Series Aggregation & Percentile Calculation (Week 2)

**Owner**: Backend Services Agent

**Context**: Raw events are being collected. Now we need to aggregate them over time windows and compute percentiles (P50, P95, P99) to understand data flow patterns and identify bottlenecks.

**Objective**: Build the aggregation layer — calculate percentiles, implement time-series decay (48-hour rolling window), and expose aggregated metrics via API.

**Deliverables**:
1. **`backend/services/metrics/aggregator.py`** (200 lines)
   - `PercentileMetric` dataclass (p50, p95, p99, count, sum, min, max)
   - `aggregate_metrics(metric_type, time_range, bucket_window)` → PercentileMetric[]
   - Percentile calculation: Sort values, interpolate for p50/p95/p99
   - Handle edge cases: empty buckets (return null), <100 samples (note confidence level)

2. **`backend/services/metrics/retention.py`** (100 lines)
   - Time-series decay rules (48-hour default retention window)
   - `cleanup_old_events(before_timestamp)` — delete events older than 48 hours
   - `get_retention_policy()` — return window size and cleanup schedule
   - Automatic nightly cleanup via metronome task

3. **`backend/api/v1/metrics/percentiles.py`** (80 lines)
   - GET `/api/v1/metrics/percentiles?metric_type=latency&time_range=1h` → PercentileMetric[]
   - GET `/api/v1/metrics/percentiles?metric_type=latency&time_range=24h&corps_id=...` — filter by corps
   - GET `/api/v1/metrics/trends?metric_type=latency&time_range=7d` → time-series of percentiles over days

4. **Database**:
   - Create `metric_history` table (aggregated time-series snapshots):
     - `id, metric_type, timestamp, p50, p95, p99, count, corpus_id, agent_id`
   - Create scheduled cleanup task (via `metronome/tick.sh`): delete rows where `timestamp < now() - 48 hours`

5. **Tests**:
   - Unit: `test_metrics_aggregation.py` — 40+ test cases (percentile calculation accuracy, edge cases with <100 samples, rank ties, empty buckets)
   - Integration: `test_metrics_end_to_end.py` — 10+ tests (raw events → aggregated percentiles → API response)
   - Ground truth validation: Generate 1000+ sample datasets, verify percentile calculations match numpy/scipy
   - Coverage: 90%+

**Success Criteria**:
- [ ] Percentile calculations (P50, P95, P99) are mathematically correct across all metrics
- [ ] Time-series decay respects 48-hour window (events >48h old are cleaned up nightly)
- [ ] Aggregation queries return results in <200ms (p99)
- [ ] API endpoints return correctly formatted PercentileMetric[] objects
- [ ] Edge cases handled: empty buckets, <100 samples, rank ties all tested and pass

**Acceptance Tests**:
```bash
# Verify percentile accuracy
pytest backend/tests/test_metrics_aggregation.py::test_percentile_accuracy -v

# Check time-series retention
pytest backend/tests/test_metrics_aggregation.py::test_retention_cleanup -v

# Query aggregated percentiles
curl "http://localhost:8000/api/v1/metrics/percentiles?metric_type=latency" | jq '.percentiles'
```

---

### Movement III: Leaderboard & Rank Ordering (Week 3)

**Owner**: Backend Services Agent + Frontend Agent

**Backend Deliverables**:
1. **`backend/services/metrics/scorer.py`** (180 lines)
   - `CompositeScore` dataclass (total_score, component_scores{latency, throughput, error_rate, resources})
   - `calculate_composite_score(corpus_id)` — weighted formula:
     - 40% latency health (inverse: faster = higher score)
     - 30% throughput (reps/hour)
     - 20% error rate (inverse: fewer errors = higher score)
     - 10% resource utilization (optimal range 50-70%, score drops outside)
   - Ranking algorithm: Sort all corps by composite_score DESC; handle ties by timestamp (earlier = higher rank)

2. **`backend/api/v1/metrics/leaderboard.py`** (100 lines)
   - GET `/api/v1/metrics/leaderboard` → RankedCorps[] (rank, corps_id, corps_name, composite_score, component_scores, trend)
   - GET `/api/v1/metrics/leaderboard?section=percussion` → filtered by section
   - GET `/api/v1/metrics/leaderboard?metric_type=latency` → sorted by specific metric
   - Response includes rank badge (1st=gold, 2nd=silver, 3rd=bronze), sparkline (7-day trend)

3. **Tests**:
   - Unit: `test_metrics_scorer.py` — 25+ test cases (weight validation, rank stability, tie-breaking, edge cases with 1 corps, 100+ corps)
   - Coverage: 85%+

**Frontend Deliverables**:
1. **`frontend/src/components/Leaderboard.tsx`** (150 lines)
   - Render RankedCorps[] as sortable table (rank, name, score, latency, throughput, errors, resources)
   - Clickable rows → drill-down to CorpsMetricsDetail
   - Sorting: Click column header to toggle ascending/descending
   - Filtering: Dropdown for "All Sections" / "Percussion" / "Brass" / etc.
   - Responsive: Stack columns on mobile, full table on desktop
   - Styling: Field Commander Brutalism (JetBrains Mono for numbers, IBM Plex Sans for labels, stage color badges for rank)

2. **Tests**:
   - Unit: `test_Leaderboard.tsx` — 15+ test cases (sorting, filtering, rank badge rendering, drill-down navigation)
   - Coverage: 80%+

**Success Criteria**:
- [ ] Composite score formula correctly weights all 4 components
- [ ] Leaderboard ranks all active corps accurately
- [ ] Rank changes propagate to frontend within 1 second of backend calculation
- [ ] Leaderboard component renders without errors on all breakpoints (mobile/tablet/desktop)
- [ ] Sorting and filtering work correctly
- [ ] Tie-breaking (by timestamp) is consistent and documented

**Acceptance Tests**:
```bash
# Verify composite score calculation
pytest backend/tests/test_metrics_scorer.py::test_composite_score_formula -v

# Check leaderboard API
curl "http://localhost:8000/api/v1/metrics/leaderboard" | jq '.corps | .[0]'

# Render leaderboard component
npm test frontend/src/components/__tests__/Leaderboard.test.tsx -v
```

---

### Movement IV: Dashboard Visualization & Real-Time Broadcast (Week 4)

**Owner**: Frontend Agent + WebSocket Integration Agent

**Guard Choreographer Concept** (from design notes):
- Guard opens with **static rifle holds** (black box state)
- Transitions to **synchronized flag arcs** (representing percentile cascades)
- Climactic **equipment toss sequence** where guards catch rifles mid-spin (observable system reveal)
- **Flags planted vertically** as living dashboards showing real-time color-coded status (red/yellow/green health indicators)

**Drill Writer Concept** (from design notes):
- **Opening (counts 1-16)**: Metric collection formation — corps scattered, then snaps into 6 vertical data-type lines (latency, throughput, errors, resources, agents, tasks)
- **Transition (counts 17-32)**: Bucketing compression — lines compress into P50/P95/P99 percentile groups, shift diagonally downstage while time-series pulses ripple upward (visual metaphor of data flowing backward through time)
- Clean, brutal geometry with synchronized snaps on the beat

**Frontend Deliverables**:
1. **`frontend/src/pages/MetricsDashboard.tsx`** (300 lines)
   - Main dashboard page: 6 metric cards in 2×3 grid (latency, throughput, errors, resources, agents, tasks)
   - Each card shows: current value, P95 threshold, sparkline (7-day trend), last updated timestamp, health status (red/yellow/green)
   - Auto-refresh: update every 5 seconds from WebSocket
   - Top-right: System health indicator (color badge: green/yellow/red, click for detailed status modal)
   - Bottom: Leaderboard section (top 10 corps by composite score)
   - Responsive: 1 col (mobile) → 2 cols (tablet) → 3 cols (desktop)
   - Styling: Field Commander Brutalism — JetBrains Mono headers, IBM Plex Sans labels, stage colors for health, smooth transitions (300ms ease)

2. **`frontend/src/components/MetricCard.tsx`** (120 lines)
   - Single metric card component (reusable for all 6 metrics)
   - Props: `metric_name, value, p95_threshold, sparkline_data, health_status, last_updated`
   - Animations: Number typewriter effect on update, color pulse (subtle flash on value change)
   - Sparkline: 7-day trend chart (use Recharts or lightweight SVG)
   - Health indicator: Dot that changes color (green → yellow → red)

3. **`frontend/src/components/HealthIndicator.tsx`** (80 lines)
   - System health status badge (top-right of dashboard)
   - Props: `status ('ok'|'warning'|'error'), message, detail_modal_content`
   - Colors: 🟢 ok, 🟡 warning, 🔴 error
   - Click → open detail modal showing which metrics are failing, which agents are stalled, alert log
   - Fade transitions between states (300ms)

4. **`frontend/src/services/metricsWebSocket.ts`** (150 lines)
   - WebSocket client for real-time metric updates
   - `MetricsWebSocketClient` class:
     - `connect(url)` — establish WS connection with automatic reconnect (exponential backoff: 1s, 2s, 4s, 8s max)
     - `subscribe(metric_type)` — subscribe to updates for specific metric
     - `onMetricUpdate(callback)` — callback when metric updates arrive
     - `onConnectionChange(callback)` — track connection state (connected/disconnected/reconnecting)
   - Handle message parsing: `{ type: 'metric_update', metric_type, value, timestamp, p95_threshold }`
   - Clean disconnect on component unmount
   - Connection stability: Heartbeat ping every 30s, reconnect if no pong after 5s

5. **`frontend/src/pages/PerformanceExplorer.tsx`** (200 lines) [Optional advanced feature]
   - Custom metric analysis page
   - Multi-series charting: Select metrics to compare (latency vs throughput, etc.)
   - Time range picker (1h, 24h, 7d, 30d)
   - Filter by corps, section, agent role
   - Export data as CSV
   - Uses Recharts for responsive multi-series line chart

**Backend Deliverables**:
1. **WebSocket metric broadcast** (extend existing `backend/api/app.py`)
   - Extend WebSocket handler to broadcast metric updates to all connected dashboard clients
   - When `/api/v1/metrics/percentiles` is queried, broadcast to all subscribed clients
   - Message format: `{ type: 'metric_update', metric_type, value, p95, timestamp, health_status }`
   - Only send to clients authorized by role (query guards filter metrics by role)

2. **Performance monitoring**:
   - Track WebSocket message latency (from calculation to client delivery)
   - Track concurrent client count
   - Alert if >5 messages/second per metric (spam prevention)

3. **Tests**:
   - Integration: `test_metrics_websocket.py` — 20+ test cases (connect, subscribe, message handling, disconnect, reconnect, permission filtering)
   - Visual regression: `test_MetricsDashboard.visual.ts` — 5+ baseline screenshots (mobile/tablet/desktop responsive design)
   - Accessibility: `test_dashboard_accessibility.ts` — WCAG 2.1 AA scan (color contrast, keyboard nav, screen reader support)
   - Performance: `test_metrics_performance.ts` — 1000 concurrent metric updates, <500ms dashboard latency (p99)
   - Coverage: 80%+ frontend, 75%+ WebSocket integration

**Documentation**:
1. **`docs/metrics/README.md`**: System overview, data model, calculation algorithms, metric categories
2. **`docs/metrics/api.md`**: Complete V1 API reference (Movements I-III endpoints, response formats)
3. **`docs/metrics/dashboard.md`**: Frontend guide (component architecture, WebSocket integration, styling, responsive design)
4. **`docs/metrics/calculation.md`**: Detailed breakdown (composite score formula, percentile algorithms, decay rules, edge cases)

**Success Criteria**:
- [ ] Dashboard loads in <2 seconds (cold start), <500ms (warm start with cached metrics)
- [ ] Metrics update via WebSocket in <500ms from backend calculation to frontend display (p99)
- [ ] Supports 50+ concurrent dashboard viewers without server degradation
- [ ] All 6 metrics visible + composite score + health indicator + leaderboard
- [ ] WebSocket connection sustains 24+ hours without forced reconnect
- [ ] Responsive design works on mobile (<768px), tablet (768-1200px), desktop (>1200px)
- [ ] WCAG 2.1 AA accessibility standards met (color contrast, keyboard nav, screen reader support)
- [ ] Guard choreography executed: Visual metaphor of data formations (opening black box → percentile cascades → observable system reveal)
- [ ] Drill design executed: 6 metric lines open scattered, compress into percentile formations, sync to beats

**Acceptance Tests**:
```bash
# Render dashboard component
npm test frontend/src/pages/__tests__/MetricsDashboard.test.tsx -v

# Check WebSocket connectivity and message delivery
pytest backend/tests/test_metrics_websocket.py -v

# Verify responsive design across breakpoints
npx playwright test frontend/tests/e2e/dashboard-responsive.spec.ts

# Accessibility audit
npm run test:a11y

# Performance test: 1000 concurrent metric updates
npm run test:performance -- --concurrency 1000

# End-to-end: Agent work → metric collected → percentile calculated → dashboard updated
pytest backend/tests/test_metrics_e2e.py -v
```

---

### Success Checklist — Definition of Done

**For All Movements**:
- [ ] All code is type-safe (100% TypeScript strict mode for frontend, 100% type hints for backend)
- [ ] Test coverage >80% for all metric calculations and UI components
- [ ] Docstrings on all public functions/classes explaining algorithm and edge cases
- [ ] No unhandled exceptions in WebSocket, metrics recording, or percentile calculation
- [ ] Metronome tracks metric calculation failures; alerts if >1% fail over 5 minutes
- [ ] Graceful degradation: If metric calculation stalls, dashboard shows "calculating..." instead of crashing
- [ ] All changes backward-compatible (add fields, don't remove; support rollback to N-1 version)
- [ ] Production ready: Monitored by system health checks, logs structured for debugging

**Code Review Checklist**:
- [ ] <3 code review findings (no architectural issues, type errors, or test gaps)
- [ ] Professional docstrings and examples in test files
- [ ] Clean git history: frequent commits, clear commit messages
- [ ] No debug logging left in code (remove console.log, print statements)
- [ ] Dependencies: no new dependencies added without justification

**Documentation Checklist**:
- [ ] README.md explains system architecture and data model
- [ ] API guide includes exact response formats and error codes
- [ ] Dashboard guide documents component hierarchy and WebSocket message flow
- [ ] Calculation guide explains weighted formula, percentile algorithm, decay rules
- [ ] Example usage in test files (runnable code)

**Performance Checklist**:
- [ ] Metric recording <5ms overhead per event (async)
- [ ] Percentile calculation <200ms (p99)
- [ ] Dashboard load <2s cold, <500ms warm
- [ ] WebSocket message latency <500ms (p99)
- [ ] Supports 50+ concurrent viewers, 1000 concurrent metric updates

---

### Execution Strategy & Safety Guardrails

**What MUST be done**:
1. Use existing V1 API endpoints (GET only) — all movement endpoints already exist
2. Use existing WebSocket `/ws` endpoint — no new socket connections
3. Record metrics asynchronously — don't block agent execution
4. Implement role-based filtering in queries — use JWT role + section_id to guard data
5. Document all metric algorithms — percentile calculation, composite score formula, decay rules
6. Test edge cases — empty buckets, <100 samples, rank ties, client disconnect/reconnect

**What MUST NOT be done**:
- ❌ Create new LLM clients (use `backend/services/llm_client.py` shared instance)
- ❌ Modify backend schema (use existing `metrics` table; add fields only via migration)
- ❌ Create new database tables (aggregate metrics into `metric_history` via existing migration)
- ❌ Add new agent roles (use existing hierarchy: Director → PC → Caption Head → Performer)
- ❌ Disable metronome or background tasks (metrics cleanup must run nightly)

**Constraints**:
- Backend infrastructure (Movements I-III) is already complete ✅
- UI skeleton pages already exist (DesignRoom, CorpsDetailV2) — just add data wiring
- All 6 metrics categories must be visible (latency, throughput, errors, resources, agents, tasks)
- 78/100 passing threshold (50 pts functionality, 25 pts code quality, 15 pts operational, 10 pts edge cases)

---

### Cross-Movement Integration Points

**Movement I → II**: Raw events flow from collector.py → aggregator.py bucketing
- Aggregator subscribes to `metrics_events` table changes (via metronome task)
- Populates `metric_history` with aggregated percentiles every 5 minutes

**Movement II → III**: Aggregated percentiles flow from aggregator.py → scorer.py
- Scorer queries latest percentiles for each corps
- Calculates composite score using weighted formula
- Writes to leaderboard cache (e.g., `metrics_leaderboard` table or in-memory)

**Movement III → IV**: Leaderboard flows from scorer.py → dashboard frontend
- Dashboard queries leaderboard endpoint + subscribes to WebSocket for live updates
- Each metric card pulls from `/api/v1/metrics/percentiles?metric_type=X`
- WebSocket broadcasts metric updates to all connected clients every 5 seconds

**Metronome Integration**:
- Every 5 minutes: Aggregator recalculates percentiles
- Every 1 hour: Scorer recalculates composite scores and leaderboard
- Every 24 hours: Retention cleanup (delete events >48h old)
- Alert if metric calculation takes >1 second (performance degradation)

---

### Phase Execution Roadmap

| Week | Responsible | Tasks | Completion Criteria |
|------|-------------|-------|---------------------|
| 1 | Backend Agent | Movement I: Collector + Bucketer + Raw API + Tests | 85%+ test coverage, <5ms queries |
| 2 | Backend Agent | Movement II: Aggregator + Retention + Percentiles API + Tests | 90%+ test coverage, P50/P95/P99 correct |
| 3 | Backend Agent + Frontend Agent | Movement III: Scorer + Leaderboard API + Leaderboard Component + Tests | 85%+ coverage, ranking accurate, <1s propagation |
| 4 | Frontend Agent + WebSocket Agent | Movement IV: Dashboard + MetricCard + HealthIndicator + WebSocket Client + Tests | 80%+ coverage, <500ms update latency, 24h+ stability |

**Review Checkpoints**:
- End of Week 1: Code review of Movement I (collector, bucketer, tests)
- End of Week 2: Code review of Movement II (aggregator, retention, percentiles)
- End of Week 3: Code review of Movement III (scorer, leaderboard API + component)
- End of Week 4: Final code review + performance testing + accessibility audit + director sign-off

---

### Closing: The Show Concept Realized

By the end of Movement IV, the DCI Swarm transforms from a black box into an observable system:

1. **Guard choreography realized**: Flags open as static rifle holds (black box), transition to synchronized arcs (percentile cascades), climax with equipment tosses (observable system reveal), plant vertically as living dashboards (real-time color-coded status)

2. **Drill design realized**: 6 metric lines open scattered (data collection), compress into P50/P95/P99 formations (bucketing and aggregation), shift downstage with time-series pulses (data flowing backward through time), merge into rank-ordered formations (leaderboard)

3. **Visual feedback realized**: Metric cards pulse on update, leaderboard highlights rank changes, health indicator changes color before alerts, timestamps show freshness, WebSocket maintains live connection 24/7

4. **Mission accomplished**: Directors see system health at a glance. Engineers identify performance bottlenecks via percentile heatmaps. Operators know immediately when to escalate. The swarm is no longer a black box—it's a living, observable system.

---

## Show Prompt Status

**Brief**: ✅ Complete (all 8 required sections)
- ✅ ## Show Concept
- ✅ ## Musical Design (4 movements)
- ✅ ## Visual Design (Field Commander Brutalism)
- ✅ ## Guard Design (RBAC + data privacy)
- ✅ ## General Effect (purpose, impact, success criteria)
- ✅ ## Constraints (technical, performance, code quality, operational)
- ✅ ## Deliverables (25+ concrete items across 4 movements)
- ✅ ## Evaluation Rubric (50/25/15/10 weighting, 78/100 threshold)

**Swarm Prompt**: ✅ Complete
- ✅ Agent team assignments (Backend, Frontend, WebSocket agents)
- ✅ Movement-by-movement implementation guide (weeks 1-4)
- ✅ Guard choreographer concept integrated (rifle holds → flag arcs → equipment tosses → living dashboards)
- ✅ Drill writer concept integrated (6 metric lines → percentile compression → rank formations)
- ✅ API reference with exact response formats
- ✅ Testing strategy with unit/integration/performance/accessibility specs
- ✅ Success checklist (code quality, documentation, performance, edge cases)
- ✅ Execution strategy & guardrails (what must/must not be done)

**Status**: ✅ Ready for Director Sign-Off and Team Assignment

Next: Director assigns work to agents using this Swarm Prompt. Backend Agent executes Movements I-III. Frontend Agent + WebSocket Agent execute Movement IV. Weekly code reviews at phase checkpoints.
