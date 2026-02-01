# Let's Build Some Metrics — Movement IV: Dashboard & Visualization

**Show Prompt for Program Coordinator**

---

## Show Concept

**Mission:** Transform the DCI swarm from a black box into a fully observable system with real-time visibility into system performance, corps health, agent efficiency, and bottleneck detection.

**Context:** The swarm executes thousands of tasks across multiple corps in parallel. Without observability, we cannot:
- Understand why a show is delayed
- Identify which agents are struggling
- Detect system bottlenecks before they cause failures
- Make data-driven decisions about resource allocation

**Solution:** Build a four-movement metrics pipeline (data collection → aggregation → scoring → visualization) that gives stakeholders (ED, PC, caption heads) actionable insights into system health.

**Movement IV's Role:** Create the user-facing dashboard that makes all the collected and aggregated metrics *visible, interactive, and actionable*.

---

## Musical Design

**Four Movements (Complete Specification):**

### Movement I: Data Collection & Instrumentation ✅ COMPLETE
- Instrument 6 metric categories (rep lifecycle, agent sessions, messages, query performance, system events, error tracking)
- Real-time event capture with 16 metric types
- MetricsCollector class with query interface
- 12 tests, all passing

### Movement II: Aggregation & Storage ✅ COMPLETE
- Time-series bucketing into 4 windows (1-min, 5-min, hourly, daily)
- Percentile calculation (p50, p95, p99) and trend analysis
- 30-day rolling retention with vacuum cleanup
- MetricsAggregator with trend velocity computations
- 12 tests, all passing

### Movement III: Scoreboards & API ✅ COMPLETE
- Corps leaderboard (composite scoring: 40% completion, 30% utilization, 20% duration, 10% errors)
- Agent role rankings by performance
- Bottleneck detection (operations exceeding p95 latency)
- Trend analysis (7-day and 30-day velocity)
- 4 API endpoints fully documented and tested

### Movement IV: Dashboard & Visualization 🏗️ IN PROGRESS (YOUR TASK)
- **MetricsDashboard:** Summary cards with sparklines, time range selector, auto-refresh
- **ScoreboardsPage:** Sortable corps and agent leaderboards with drill-down
- **PerformanceExplorer:** Custom metric analysis with multi-series charting
- Real-time WebSocket integration or polling fallback
- Responsive design (mobile/tablet/desktop) with Field Commander Brutalism aesthetic

---

## Visual Design

**Aesthetic:** Field Commander Brutalism — minimalist, data-forward, high contrast, real-time indicators.

**Typography:**
- Data/metrics: JetBrains Mono (monospace)
- Labels/UI: IBM Plex Sans (sans-serif)

**Color System:**
- Primary: `--color-primary` (blue accent)
- Status Good: `#52c41a` (green) — metric within normal range
- Status Warning: `#faad14` (orange) — approaching threshold
- Status Critical: `#f5222d` (red) — exceeding threshold
- Backgrounds: Dark-neutral with subtle gradients for depth
- Neutral: Grayscale for structure (borders, dividers)

**Component Patterns:**
- **Metric Cards:** Large bold number + unit, trend indicator (↑/↓), colored left border per status
- **Sparklines:** Tiny inline charts showing 24h trend
- **Status Badges:** Medal colors for top 3 leaderboard entries (gold, silver, bronze)
- **Tables:** Right-aligned numbers, sortable headers (click icon), hover highlight

**Responsive Breakpoints:**
- Mobile (<576px): 1-column grid, stacked tables
- Tablet (576-992px): 2-column grid, responsive tables
- Desktop (>992px): 3+ column grid, full table width

---

## Guard Design

**Role-Based Access Control (Hierarchy-Enforced):**

| Role | Can View | Cannot View | Use Cases |
|------|----------|-------------|-----------|
| **ED** | All metrics, all corps, system-wide trends | None (full access) | Strategic planning, problem diagnosis |
| **PC** | All metrics, assigned corps | Other corps' detailed debug info | Show-specific optimization |
| **Design Staff** | Metrics for assigned shows | Cross-corps comparisons | Task planning, resource requests |
| **Caption Heads** | Their corps metrics, their role metrics | Other corps data | Real-time agent monitoring, assignment decisions |
| **Techs** | Their assigned task metrics only | All other data | Task execution, progress feedback |
| **Performers** | Their own performance stats | Everything else | Personal progress tracking (future) |

**Data Privacy:**
- Never expose individual message content in metrics
- Agent names/IDs visible only to ED/PC/Design Staff
- Query times aggregated, never individual queries exposed
- Error messages sanitized (no secrets/credentials in logs)

**Implementation:**
- Every API endpoint filters data by caller's role + assigned corps
- Frontend respects role permissions (hide tabs/buttons if not authorized)
- WebSocket filters events by role on server side

---

## General Effect

**Purpose:** Movement IV delivers on the promise of observability by making system health *visible, interactive, and actionable* to all stakeholder levels.

**Impact on Stakeholders:**
- **ED:** Spot-check system health in <30 seconds, identify systemic issues, make resource allocation decisions
- **PC:** Monitor show progress in real-time, detect reps stuck in transition, coordinate recovery
- **Caption Heads:** See if their agents are overwhelmed, reassign work proactively
- **Techs/Performers:** Self-serve progress feedback (future expansion)

**Success Criteria (Measurable):**
1. **Performance Threshold:** Dashboard loads in <2 seconds (p95) with <5% rerender latency
2. **Data Currency:** Metrics lag behind live state by <1 minute (via polling/WebSocket)
3. **User Adoption:** PC checks dashboard ≥3x per show, shows improved decision latency
4. **Reliability:** System uptime >99.5%, no data loss in metric events
5. **Completeness:** All metrics from Movements I-III displayed, <1% missing data points

**Visual Feedback:**
- Green status badges = system performing nominally
- Orange status badges = human attention needed
- Red status badges = intervention required immediately
- Sparklines show trend direction at a glance (↑ improving, ↓ declining)
- Auto-refresh every 30-60 seconds keeps data fresh without overwhelming

---

## Constraints

**Technical Constraints:**
1. **No Backend Modifications:** Movement III API endpoints are frozen; frontend must consume as-is
2. **No New Databases:** Use existing SQLite metrics store; no new persistence layers
3. **No New LLM Clients:** System has one shared LLM instance; frontend is pure React (no AI agent calls)
4. **Backward Compatibility:** Dashboard must work with Movements I-III unchanged; no cascading migrations required
5. **Performance Budget:**
   - Page load: <2 seconds (p95)
   - API response: <1 second (p95)
   - Chart render: <500ms
   - Memory: <100MB sustained
6. **Role-Filtering Enforcement:** All API queries must respect caller's hierarchy level and assigned corps

**Operational Constraints:**
1. Code must pass TypeScript strict mode (`--strict`)
2. No console warnings or errors in production
3. All components must have unit tests (>80% coverage)
4. Responsive on mobile, tablet, desktop without separate build
5. Dark mode support deferred to post-launch polish phase

---

## Deliverables

**Movement IV Deliverables (Complete File List):**

### Frontend Pages (3 files)
```
frontend/src/pages/
├── MetricsDashboard.tsx (250-350 lines)      Summary cards + trends, auto-refresh
├── ScoreboardsPage.tsx (300-400 lines)       Corps/Agent rankings with sorting & drill-down
└── PerformanceExplorer.tsx (250-350 lines)   Custom metric analysis with multi-series charting
```

### React Components (4 files)
```
frontend/src/components/
├── MetricsCard.tsx (80-120 lines)             Metric display + sparkline + status
├── TrendChart.tsx (120-180 lines)             Multi-series line chart (Recharts wrapper)
├── Leaderboard.tsx (150-200 lines)            Sortable ranked table with medal badges
└── AlertPanel.tsx (100-150 lines)             Alert feed with dismissal + auto-cleanup
```

### Tests (7 files, >80% coverage)
```
frontend/src/components/__tests__/
├── MetricsCard.test.tsx (40-60 lines)        Rendering, status colors, sparklines
├── TrendChart.test.tsx (50-80 lines)         Multi-series plotting, responsive sizing
├── Leaderboard.test.tsx (60-100 lines)       Sorting, highlighting, pagination
└── AlertPanel.test.tsx (40-60 lines)         Alert display, dismissal, cleanup

frontend/src/pages/__tests__/
├── MetricsDashboard.integration.test.tsx (80-120 lines)   API integration, time range
├── ScoreboardsPage.integration.test.tsx (80-120 lines)    Tab switching, sorting, drill-down
└── PerformanceExplorer.integration.test.tsx (80-120 lines) Metric picker, export, baseline
```

### Estimated Line Count Summary
```
Pages:       800-1,100 lines (implementation)
Components:  450-650 lines (implementation)
Tests:       430-640 lines (test code)
Total:       ~1,680-2,390 lines (all combined)
Expected Coverage: >85%
```

**API Endpoints (Already Implemented in Movement III):**
```
✅ GET /api/v1/metrics/dashboard?range=24h
✅ GET /api/v1/scoreboards/corps?sort_by=composite&limit=100
✅ GET /api/v1/scoreboards/agents?limit=100
✅ GET /api/v1/scoreboards/trends?window=7d
✅ GET /api/v1/metrics/series?metrics=rep_completed&range=24h&granularity=1h
✅ WebSocket /ws/metrics (real-time event stream)
```

---

## Evaluation Rubric

**Pass Threshold:** 78/100

**Scoring Breakdown (50/25/15/10):**

### Functionality (50 points) — REQUIRED: >39/50
- [ ] 10 pts: All three pages load and display data from backend API
- [ ] 10 pts: All interactive features work (sorting, filtering, time range, drill-down)
- [ ] 10 pts: Real-time updates implemented (WebSocket OR polling, <1min lag)
- [ ] 10 pts: Error handling + loading states for all async operations
- [ ] 10 pts: Status indicators (green/yellow/red) correctly reflect data thresholds

### Code Quality (25 points) — REQUIRED: >19/25
- [ ] 5 pts: TypeScript strict mode, zero console errors, proper typing
- [ ] 5 pts: Components under 300 lines, good separation of concerns
- [ ] 5 pts: Proper use of React hooks (memoization, lazy loading where needed)
- [ ] 5 pts: Accessible (ARIA labels, keyboard navigation, semantic HTML)
- [ ] 5 pts: Consistent styling using design system (fonts, colors, spacing)

### Operational (15 points) — REQUIRED: >11/15
- [ ] 5 pts: <2s page load time (p95), <1s API response time
- [ ] 5 pts: >80% test coverage, all tests passing
- [ ] 5 pts: Responsive on mobile/tablet/desktop, no layout breaks

### Edge Cases (10 points) — REQUIRED: >7/10
- [ ] 3 pts: Handles empty data (no reps, no agents)
- [ ] 3 pts: Handles API failures gracefully (retry logic, fallback UI)
- [ ] 4 pts: Handles large datasets (1000+ entities) without lag

**Grade Interpretation:**
- 100: Exemplary — exceeds spec, excellent UX, shipping quality
- 90-99: Excellent — all requirements met, minor polish needed
- 78-89: Satisfactory — core functionality complete, acceptable for release
- 60-77: Needs Work — missing features or significant bugs
- <60: Incomplete — major missing pieces, not ready for release

---

## Your Mission

**Goal:** Build the frontend UI dashboard that visualizes metrics and performance data from the metrics collection pipeline (Movements I-III are complete).

**Scope:** Implement three React pages with interactive charts, scoreboards, and real-time updates that give stakeholders visibility into system performance, corps rankings, and trend analysis.

**Success Criteria:**
- Metrics dashboard loads in <2 seconds with live data
- Scoreboards show current rankings with drill-down capability
- Performance explorer allows custom metric analysis
- All pages automatically update as new metrics arrive
- Frontend builds without errors and all tests pass

---

## Current State (Movements I-III Complete)

### ✅ Movement I: Data Collection & Instrumentation
- `backend/services/metrics.py` — Comprehensive metrics recording system
- 16 metric types: rep lifecycle, agent sessions, messages, system events
- `MetricsCollector` class provides query interface: `get_events()`, `get_latency_percentiles()`, `get_throughput()`
- 12 tests, all passing

### ✅ Movement II: Aggregation & Storage
- `backend/services/metrics_aggregation.py` — Time-series bucketing and trend analysis
- 4 time windows: 1-min, 5-min, hourly, daily aggregates
- `MetricsAggregator` computes p50/p95/p99 percentiles, trend rates, velocity trends
- 12 tests, all passing
- Data retention: 30-day rolling window

### ✅ Movement III: Scoreboards & Leaderboards (In Progress)
- `backend/api/v1/scoreboards.py` — API endpoints for rankings
- **Implemented Endpoints:**
  - `GET /api/v1/scoreboards/corps` — Corps rankings with composite scores
  - `GET /api/v1/scoreboards/agents` — Agent role rankings
  - `GET /api/v1/scoreboards/trends` — 7-day/30-day velocity trends
  - `GET /api/v1/scoreboards/bottlenecks` — Operations exceeding p95 latency
- **Scoring Algorithm:**
  - Show completion rate: 40% weight
  - Agent utilization efficiency: 30% weight
  - Average task duration: 20% weight
  - Error/failure rate: 10% weight
- Scores refresh within 5 minutes of new metric events

### 🏗️ Movement IV: Your Task

**Three frontend pages already have UI skeleton with mock data.** Your job is to:

1. **Wire them to the backend API** (scoreboards and metrics endpoints already exist)
2. **Implement real-time updates** (WebSocket or polling)
3. **Add interactive features** (sorting, filtering, drill-down)
4. **Test everything** (unit + integration tests)

---

## Deliverables for Movement IV

### Pages to Complete (UI skeleton exists, wire to real data)

#### 1. MetricsDashboard.tsx (`frontend/src/pages/MetricsDashboard.tsx`)
**Purpose:** Summary view of system health with key performance indicators.

**Key Metrics to Display:**
- Show Completion Rate (%) — completed reps / total reps
- Avg Rep Duration (minutes) — time from assigned → completed
- Success Rate (%) — completed / (completed + failed)
- Query Latency p95 (milliseconds) — database query performance
- Agent Utilization (%) — active agents / total available
- Message Throughput (msg/min) — message volume over time

**Features:**
- Summary metric cards with sparkline trend visualization
- Time range selector: 1h, 6h, 24h, 7d (default 24h)
- Status indicators: green (good), yellow (warning), red (critical)
- Auto-refresh every 30 seconds
- Responsive grid layout (1 col mobile, 2 col tablet, 3 col desktop)

**API Integration:**
- Call `GET /api/v1/metrics/dashboard?range=24h` on mount
- Parse response into metric cards with trend sparklines
- Update on 30-second interval

**Components Used:**
- `MetricsCard.tsx` — individual metric display with sparkline
- `TrendChart.tsx` — sparkline visualization

#### 2. ScoreboardsPage.tsx (`frontend/src/pages/ScoreboardsPage.tsx`)
**Purpose:** Real-time leaderboards showing corps and agent rankings.

**Tab 1: Corps Leaderboard**
- Show rank, corps name, shows completed/total, avg duration, success rate, latency, composite score
- Sortable columns (click header to sort ascending/descending)
- Color-coded score badges (gold/silver/bronze for top 3)
- Row click opens detail modal with trend chart
- Pagination (20 rows per page)

**Tab 2: Agent Leaderboard**
- Show rank, agent role, agent count, session count, avg duration, success rate, throughput, score
- Sortable, color-coded
- Agent role drill-down to see individual agents

**Tab 3: Trends (7-day velocity)**
- Show 7-day trend in show completion rate by corps
- Show 7-day trend in message throughput
- Show 7-day trend in query latency (p95)
- Direction indicators (↑ up, ↓ down, → flat)

**API Integration:**
- `GET /api/v1/scoreboards/corps?limit=100&offset=0&sort_by=composite` on load
- `GET /api/v1/scoreboards/agents?limit=100&offset=0` on load
- `GET /api/v1/scoreboards/trends?window=7d` for trend data
- Refresh every 5 minutes (or on WebSocket update)

**Components Used:**
- `Leaderboard.tsx` — ranked table with sorting
- Ant Design Table with custom columns
- Detail modal on row click

#### 3. PerformanceExplorer.tsx (`frontend/src/pages/PerformanceExplorer.tsx`)
**Purpose:** Advanced analysis tool for custom metric exploration over time.

**Features:**
- **Time Range Selector:** Custom date picker (default last 24h)
- **Granularity Control:** 1m, 5m, 1h, 1d bucket size
- **Metric Picker:** Checkboxes to select which metrics to chart
  - Rep completion rate
  - Query latency (p50, p95, p99)
  - Message throughput
  - Agent utilization
  - Error rate
  - Session duration
- **Multi-Series Line Chart** showing selected metrics with different colors
- **Data Export:** Button to download as CSV/JSON
- **Baseline Comparison:** Checkbox to overlay previous period for comparison

**API Integration:**
- `GET /api/v1/metrics/series?metrics=rep_completed,query_latency&range=24h&granularity=1h`
- Parse response into chart format
- Lazy load as user changes filters

**Components Used:**
- `TrendChart.tsx` — multi-series line chart
- Recharts library for charting
- DatePicker for time range

---

## React Components to Implement or Update

### New/Updated Components

#### `MetricsCard.tsx`
```typescript
interface MetricsCardProps {
  title: string
  value: number | string
  unit: string
  trend?: number  // percentage change
  status: "good" | "warning" | "critical"
  sparklineData?: Array<{ time: string; value: number }>
}
```
**Responsibilities:**
- Display large metric number with label
- Show trend sparkline (if data provided)
- Color code based on status
- Show up/down arrow for trend direction

#### `TrendChart.tsx`
```typescript
interface TrendChartProps {
  data: Array<{ timestamp: string; [key: string]: number }>
  metrics: string[]  // keys to plot
  title?: string
  height?: number
}
```
**Responsibilities:**
- Render line chart with Recharts
- Multi-series support
- Responsive sizing
- Tooltip on hover

#### `Leaderboard.tsx`
```typescript
interface LeaderboardProps {
  title: string
  data: Array<any>
  columns: ColumnType[]
  onRowClick?: (record: any) => void
  sortable?: boolean
  pagination?: { pageSize: number }
}
```
**Responsibilities:**
- Render sortable table
- Handle column sorting
- Highlight top 3 (gold/silver/bronze)
- Pagination controls

#### `AlertPanel.tsx`
```typescript
interface AlertPanelProps {
  alerts: Array<{
    id: string
    timestamp: string
    severity: "info" | "warning" | "error"
    message: string
    metric: string
  }>
}
```
**Responsibilities:**
- Render live alert feed
- Color code by severity
- Dismiss individual alerts
- Auto-remove old alerts after 5 minutes

---

## Integration Checklist

### Phase 1: API Integration (Highest Priority)
- [ ] **MetricsDashboard.tsx**
  - [ ] Call `/api/v1/metrics/dashboard?range=24h` on mount
  - [ ] Map response to MetricsCard props
  - [ ] Implement time range selector
  - [ ] Hook up 30-second auto-refresh
  - [ ] Add error handling and loading state

- [ ] **ScoreboardsPage.tsx**
  - [ ] Call `/api/v1/scoreboards/corps` on mount
  - [ ] Call `/api/v1/scoreboards/agents` on load
  - [ ] Map response to Leaderboard component
  - [ ] Implement tab switching
  - [ ] Add sorting on column click
  - [ ] Implement row click detail modal

- [ ] **PerformanceExplorer.tsx**
  - [ ] Call `/api/v1/metrics/series` when filters change
  - [ ] Implement metric picker checkboxes
  - [ ] Hook up date range picker
  - [ ] Render multi-series chart
  - [ ] Add export to CSV button

### Phase 2: Real-Time Updates (Medium Priority)
- [ ] Set up WebSocket connection to `/ws/metrics` (or fallback to polling)
- [ ] Auto-update MetricsDashboard when new events arrive
- [ ] Auto-update ScoreboardsPage when rankings change (every 5 min)
- [ ] Show connection status indicator in UI

### Phase 3: Interactive Features (Medium Priority)
- [ ] Detail modal on corps/agent row click showing history
- [ ] Filter by corps on metrics pages
- [ ] Save/export custom dashboards
- [ ] Keyboard shortcuts for navigation

### Phase 4: Testing (High Priority — Required Before Merge)
- [ ] Unit tests for metric card formatting
- [ ] Integration tests with mock API
- [ ] Component render tests
- [ ] Real-time update tests
- [ ] Performance tests (ensure <2s load time)

### Phase 5: Polish (Low Priority)
- [ ] Dark mode support
- [ ] Accessibility (ARIA labels, keyboard navigation)
- [ ] Mobile-responsive refinement
- [ ] Animation/transition smoothing

---

## API Reference (Already Implemented in Backend)

### GET /api/v1/metrics/dashboard
**Query Parameters:**
```
range: "1h" | "6h" | "24h" | "7d"  [default: "24h"]
```

**Response:**
```json
{
  "timestamp": "2026-02-01T14:30:00Z",
  "metrics": {
    "rep_completion_rate": {
      "current": 92.5,
      "unit": "%",
      "trend": 2.3,
      "status": "good",
      "sparkline": [
        { "time": "2026-02-01T14:00:00Z", "value": 90.2 },
        { "time": "2026-02-01T14:15:00Z", "value": 91.8 }
      ]
    },
    "avg_rep_duration": {
      "current": 45.2,
      "unit": "minutes",
      "trend": -5.1,
      "status": "good",
      "sparkline": [...]
    },
    "success_rate": {...},
    "query_latency_p95": {...},
    "agent_utilization": {...},
    "message_throughput": {...}
  }
}
```

### GET /api/v1/scoreboards/corps
**Query Parameters:**
```
limit: 100
offset: 0
sort_by: "composite" | "completion" | "latency" | "duration"  [default: "composite"]
```

**Response:**
```json
{
  "total": 25,
  "corps": [
    {
      "rank": 1,
      "corps_id": "uuid",
      "corps_name": "Phantom Regiment",
      "shows_completed": 8,
      "shows_total": 10,
      "avg_task_duration": 42.5,
      "task_success_rate": 95.2,
      "query_latency_p95": 125.4,
      "composite_score": 94.8
    },
    ...
  ]
}
```

### GET /api/v1/scoreboards/agents
**Query Parameters:**
```
limit: 100
offset: 0
```

**Response:**
```json
{
  "total": 12,
  "agents": [
    {
      "rank": 1,
      "agent_role": "music_writer",
      "agent_count": 5,
      "session_count": 127,
      "avg_session_duration": 38.2,
      "task_success_rate": 96.1,
      "throughput_per_hour": 3.2,
      "composite_score": 96.3
    },
    ...
  ]
}
```

### GET /api/v1/scoreboards/trends
**Query Parameters:**
```
window: "7d" | "30d"  [default: "7d"]
```

**Response:**
```json
{
  "period": "7d",
  "trends": [
    {
      "metric": "rep_completion_rate",
      "direction": "up",
      "rate_of_change": 2.5,
      "start_value": 88.2,
      "end_value": 92.3
    },
    ...
  ]
}
```

### GET /api/v1/metrics/series
**Query Parameters:**
```
metrics: "rep_completed,query_latency,message_throughput"  [comma-separated]
range: "1h" | "6h" | "24h" | "7d"  [default: "24h"]
granularity: "1m" | "5m" | "1h" | "1d"  [default: auto-select]
```

**Response:**
```json
{
  "metrics": [
    {
      "name": "rep_completed",
      "unit": "count",
      "data": [
        { "timestamp": "2026-02-01T13:00:00Z", "value": 45 },
        { "timestamp": "2026-02-01T14:00:00Z", "value": 52 }
      ]
    },
    ...
  ]
}
```

### WebSocket /ws/metrics (Optional — Preferred for Real-Time)
**Connection:** Open persistent WebSocket to receive metric updates

**Message Format:**
```json
{
  "type": "metric_update",
  "timestamp": "2026-02-01T14:30:12Z",
  "metric_type": "rep_completed",
  "corps_id": "uuid",
  "value": 1,
  "unit": "count"
}
```

**Behavior:**
- Server sends new metric events as they occur
- Client automatically updates dashboard without polling
- Graceful fallback to polling if WebSocket unavailable

---

## Testing Strategy

### Unit Tests (Highest Priority)

**MetricsCard.test.tsx**
```typescript
describe("MetricsCard", () => {
  it("renders metric value and unit", () => {
    render(<MetricsCard value={92.5} unit="%" title="Completion Rate" status="good" />)
    expect(screen.getByText("92.5%")).toBeInTheDocument()
  })

  it("shows green status for good metrics", () => {
    const { container } = render(<MetricsCard value={95} status="good" />)
    expect(container.querySelector(".status-good")).toBeInTheDocument()
  })

  it("renders sparkline when data provided", () => {
    const data = [{ time: "1h", value: 90 }, { time: "2h", value: 92 }]
    render(<MetricsCard sparklineData={data} />)
    expect(screen.getByRole("img", { hidden: true })).toBeInTheDocument()
  })
})
```

**Leaderboard.test.tsx**
```typescript
describe("Leaderboard", () => {
  it("renders sorted table of ranked entities", () => {
    const data = [
      { rank: 1, name: "Corps A", score: 95 },
      { rank: 2, name: "Corps B", score: 92 }
    ]
    render(<Leaderboard data={data} />)
    expect(screen.getByText("Corps A")).toBeInTheDocument()
  })

  it("handles column sort click", () => {
    const onSort = jest.fn()
    render(<Leaderboard data={[]} onSortChange={onSort} />)
    fireEvent.click(screen.getByText("Score"))
    expect(onSort).toHaveBeenCalled()
  })

  it("highlights top 3 with medal colors", () => {
    const data = [
      { rank: 1, name: "A", score: 95 },
      { rank: 2, name: "B", score: 92 },
      { rank: 3, name: "C", score: 90 }
    ]
    const { container } = render(<Leaderboard data={data} />)
    expect(container.querySelector(".rank-1")).toHaveClass("gold")
  })
})
```

### Integration Tests (Medium Priority)

**MetricsDashboard.integration.test.tsx**
```typescript
describe("MetricsDashboard", () => {
  it("loads metrics from API and displays them", async () => {
    mockFetch.get("/api/v1/metrics/dashboard?range=24h", {
      metrics: {
        rep_completion_rate: { current: 92.5, unit: "%" }
      }
    })

    render(<MetricsDashboard />)
    await waitFor(() => {
      expect(screen.getByText("92.5%")).toBeInTheDocument()
    })
  })

  it("updates on time range change", async () => {
    render(<MetricsDashboard />)
    fireEvent.click(screen.getByText("7d"))
    await waitFor(() => {
      expect(mockFetch.lastCall().url).toContain("range=7d")
    })
  })
})
```

**ScoreboardsPage.integration.test.tsx**
```typescript
describe("ScoreboardsPage", () => {
  it("displays corps leaderboard from API", async () => {
    mockFetch.get("/api/v1/scoreboards/corps", {
      corps: [
        { rank: 1, corps_name: "Phantom", composite_score: 95 }
      ]
    })

    render(<ScoreboardsPage />)
    await waitFor(() => {
      expect(screen.getByText("Phantom")).toBeInTheDocument()
    })
  })

  it("switches between corps and agent tabs", async () => {
    render(<ScoreboardsPage />)
    fireEvent.click(screen.getByRole("tab", { name: "Agents" }))
    await waitFor(() => {
      expect(mockFetch.lastCall().url).toContain("/scoreboards/agents")
    })
  })
})
```

---

## Performance Requirements

**Load Time:** <2 seconds for full dashboard render
- Implement lazy loading for tabs
- Code-split pages (use React.lazy)
- Debounce filter/sort operations

**Chart Rendering:** <500ms
- Use Recharts with `isAnimationActive={false}` for initial render
- Memoize chart data with `useMemo`
- Use virtual scrolling for large tables

**API Response:** <1s
- Backend endpoints already optimized
- Frontend should cache for 30 seconds (or use WebSocket)

**Memory:** Keep under 100MB
- Limit chart data points (e.g., max 1000 points per chart)
- Paginate large leaderboards (20-50 rows per page)

---

## Styling & Design System

**Use existing design system from project:**
- Font: JetBrains Mono (data), IBM Plex Sans (labels)
- Colors:
  - Primary: `--color-primary` (blue)
  - Success: `--color-success` (green, #52c41a)
  - Warning: `--color-warning` (orange, #faad14)
  - Error: `--color-error` (red, #f5222d)
- Spacing: Use Ant Design grid system
- Shadows: Use Ant Design elevation tokens

**Responsive Breakpoints:**
- Mobile: <576px — 1 column layout
- Tablet: 576-992px — 2 column layout
- Desktop: >992px — 3+ column layout

**Example Card Styling:**
```tsx
<Card style={{
  borderLeft: `4px solid ${status === 'good' ? '#52c41a' : '#faad14'}`,
  padding: '24px'
}}>
  <Statistic
    title="Completion Rate"
    value={92.5}
    suffix="%"
    prefix={trend > 0 ? '↑' : '↓'}
    valueStyle={{ color: status === 'good' ? '#52c41a' : '#faad14' }}
  />
</Card>
```

---

## Guard Rails (What NOT to Do)

❌ **Don't:**
- Create new LLM clients or AI integrations (system has one shared instance)
- Modify the backend metrics collection/aggregation (Movements I-II are locked)
- Add new database migrations without documenting in CLAUDE.md
- Hardcode API URLs (use environment variables)
- Build custom charting library (use Recharts or Ant Design)
- Implement backend endpoints (focus on frontend consuming existing APIs)

✅ **Do:**
- Use v1 API client (`frontend/src/services/v1.ts`)
- Test thoroughly before merge
- Keep components small (<300 lines)
- Use React hooks and functional components
- Memoize expensive calculations
- Document any new conventions in CLAUDE.md

---

## Success Checklist (Definition of Done)

### Code Complete ✅
- [ ] All 3 pages integrated with backend API endpoints
- [ ] All metric calculations and formatters working
- [ ] Real-time updates implemented (WebSocket or polling)
- [ ] Error handling for API failures
- [ ] Loading states for async operations
- [ ] No console errors or warnings

### Tested ✅
- [ ] 20+ unit tests for components
- [ ] 10+ integration tests with mock API
- [ ] MetricsDashboard loads in <2 seconds
- [ ] Charts render without lag
- [ ] All tests passing with >80% coverage

### Documented ✅
- [ ] Inline code comments for complex logic
- [ ] README section on dashboard architecture
- [ ] API integration guide for future devs
- [ ] Instructions for adding new metrics

### Production Ready ✅
- [ ] No TypeScript errors (`npm run tsc --noEmit`)
- [ ] Responsive on mobile, tablet, desktop
- [ ] Accessible (ARIA labels, keyboard nav)
- [ ] Performance budget met (<2s load)
- [ ] All dependencies pinned in package.json

---

## File Structure Reference

**Frontend pages created (UI skeleton exists, your job to wire data):**
```
frontend/src/pages/
├── MetricsDashboard.tsx       ← Summary metrics + trends
├── ScoreboardsPage.tsx         ← Corps & agent rankings
└── PerformanceExplorer.tsx     ← Custom metric analysis

frontend/src/components/
├── MetricsCard.tsx             ← Individual metric display
├── TrendChart.tsx              ← Sparkline/line charts
├── Leaderboard.tsx             ← Ranked tables
└── AlertPanel.tsx              ← Alert feed
```

**Backend endpoints ready (Movement III):**
```
GET /api/v1/metrics/dashboard
GET /api/v1/scoreboards/corps
GET /api/v1/scoreboards/agents
GET /api/v1/scoreboards/trends
GET /api/v1/metrics/series
WebSocket /ws/metrics
```

---

## Roll Call & Roles

**Your Role:** Program Coordinator
- Ensure quality gates passed
- Track progress through test suite
- Coordinate with design staff on UI/UX
- Flag blockers early

**Your Team:**
- **Frontend Developer:** Implements React components, wires APIs, tests
- **Backend Engineer:** Provides metrics endpoints (already done), supports debugging
- **QA Engineer:** Runs integration tests, performance profiling

**Your Escalation Path:**
- ED (Executive Director) — design direction, priority questions
- Tech Leads — architecture decisions, performance issues
- Caption Heads — role-specific metrics or feature requests

---

## Phase Execution Order (Recommended)

1. **Week 1: API Integration** (40% effort)
   - Wire all three pages to their API endpoints
   - Implement time range/filter selectors
   - Add error handling and loading states

2. **Week 2: Real-Time + Features** (30% effort)
   - Implement WebSocket or polling updates
   - Add interactive features (sorting, drill-down, export)
   - Fine-tune responsive design

3. **Week 3: Testing + Polish** (20% effort)
   - Write comprehensive test suite
   - Performance profiling and optimization
   - Accessibility audit
   - Dark mode (if time permits)

4. **Week 4: Deployment** (10% effort)
   - Code review against this spec
   - Load testing on prod-like data
   - Documentation update
   - Rollout + monitoring

---

## Appendix: Monitoring Checklist

**Post-launch, monitor these metrics:**
- Dashboard page load time (target: <2s p95)
- API endpoint response time (target: <1s p95)
- Chart render time (target: <500ms)
- WebSocket connection uptime (target: 99.9%)
- Frontend error rate (target: <0.1%)
- Memory usage on MetricsDashboard (target: <100MB)

**Alert thresholds:**
- 🟡 Yellow: Page load >3s, API response >1.5s
- 🔴 Red: Page load >5s, API response >3s, WebSocket down >5min

---

## Final Notes

**Movement IV builds on solid foundation.**
- Movements I & II (data collection + aggregation) are battle-tested
- Movement III (scoreboards API) provides all needed endpoints
- Your job: make the data *visible and actionable* to users

**Focus on clarity.**
- Status indicators (green/yellow/red) at a glance
- Drill-down from summary → detail without friction
- Real-time updates build confidence in system health

**Quality gate: Test before merge.**
- No feature without test
- No merge without <2s load time confirmed
- No deployment without QA sign-off

---

**Ready to build? Let's go! 🎺**

---

*This prompt was synthesized from the show spec and is authoritative for Movement IV implementation.*
*For questions on Movements I-III or backend API details, reference `/shows/lets-build-some-metrics/spec.md` and `/shows/lets-build-some-metrics/PROGRESS.md`.*
