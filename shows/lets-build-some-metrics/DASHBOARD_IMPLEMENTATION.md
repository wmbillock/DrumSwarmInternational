# Dashboard & Visualization — Implementation Guide

## Overview

Movement IV implements the frontend UI components for visualizing real-time metrics and performance trends from Movements I, II, and III.

## Components Created

### 1. MetricsDashboard.tsx
**Path:** `frontend/src/pages/MetricsDashboard.tsx`

**Purpose:** Main dashboard showing live performance metrics and trends.

**Features:**
- Summary cards with key metrics
- Real-time trend charts
- Health status indicators
- Auto-refresh every 30 seconds
- Time range selection (1h, 6h, 24h, 7d)

**Metrics Displayed:**
```
- Show Completion Rate (%)
- Avg Rep Duration (minutes)
- Success Rate (%)
- Query Latency p95 (milliseconds)
- Agent Utilization (%)
- Message Throughput (msg/min)
```

**Status Indicators:**
- Green: Good performance
- Yellow: Warning (needs attention)
- Red: Critical (immediate action needed)

**Data Sources:**
- Uses placeholder data currently
- TODO: Wire to `/api/v1/metrics/summary` endpoint
- TODO: Implement WebSocket for real-time updates

### 2. ScoreboardsPage.tsx
**Path:** `frontend/src/pages/ScoreboardsPage.tsx`

**Purpose:** Leaderboards and rankings for corps and agents.

**Features:**
- Corps ranking by composite score
- Agent role ranking by performance
- Sortable columns (score, completion, latency)
- Drill-down detail modal
- Performance metrics visualization

**Tables:**

**Corps Leaderboard:**
| Column | Metric |
|--------|--------|
| Rank | Position in leaderboard |
| Corps Name | Organization name |
| Shows | Completed/Total shows |
| Duration | Avg task duration |
| Success Rate | Task success percentage |
| Latency | p95 query latency |
| Score | Composite performance score |

**Agent Leaderboard:**
| Column | Metric |
|--------|--------|
| Rank | Position in leaderboard |
| Agent Role | Agent type/role |
| Agents | Count of agents in role |
| Sessions | Completed session count |
| Duration | Avg session duration |
| Success Rate | Task success percentage |
| Throughput | Tasks per hour |
| Score | Composite agent score |

**Data Sources:**
- Uses placeholder data currently
- TODO: Wire to `/api/v1/scoreboards/corps` endpoint
- TODO: Wire to `/api/v1/scoreboards/agents` endpoint

### 3. PerformanceExplorer.tsx
**Path:** `frontend/src/pages/PerformanceExplorer.tsx`

**Purpose:** Advanced analysis tool for custom metric exploration.

**Features:**
- Custom time range selection
- Metric picker (select multiple)
- Granularity controls (1m, 5m, 1h, 1d)
- Multi-series line chart
- Export to CSV/JSON (TODO)

**Configurable Parameters:**
```typescript
timeRange: "1h" | "6h" | "24h" | "7d" | "30d"
granularity: "1m" | "5m" | "1h" | "1d"
selectedMetrics: string[] // Any metric type
```

**Data Sources:**
- TODO: Wire to `/api/v1/metrics/series` endpoint
- TODO: Implement aggregation queries

## Integration Points

### API Endpoints Required

The following endpoints must be exposed by the backend:

```
GET /api/v1/metrics/dashboard
  Query: ?range=1h|6h|24h|7d
  Returns: Current metrics snapshot + trends

GET /api/v1/scoreboards/corps
  Query: ?limit=100&offset=0&sort_by=composite
  Returns: Ranked corps list

GET /api/v1/scoreboards/agents
  Query: ?limit=100&offset=0
  Returns: Ranked agent roles list

GET /api/v1/metrics/series
  Query: ?metrics=rep_completed,query_latency&range=24h&granularity=1h
  Returns: Time-series data for charting

WebSocket /ws/metrics
  Sends: Real-time metric events
  Format: { timestamp, metric_type, value, unit }
```

### Data Flow

```
Backend (Metrics Collection)
    ↓
MetricsEvent (raw events)
    ↓
MetricsAggregation (time-series)
    ↓
ScoreboardsAPI (rankings/scores)
    ↓
Frontend Pages (visualization)
    ↓
User Dashboard
```

## Styling & UX

### Design System
- **Color Palette:**
  - Success: #52c41a (green)
  - Warning: #faad14 (orange)
  - Critical: #f5222d (red)
  - Primary: #1890ff (blue)

- **Components:**
  - Ant Design (already configured)
  - Recharts for charting
  - Custom metric cards with status indicators

### Responsive Design
- Mobile: Single column layout
- Tablet: 2-column layout
- Desktop: Full 3+ column layout

## Performance Considerations

### Rendering
- Chart animations disabled (prevent re-renders)
- Pagination on tables (20 rows per page)
- Lazy loading for drill-down details

### Data Updates
- Polling interval: 30 seconds (configurable)
- WebSocket preferred for real-time
- Local state caching to reduce API calls

### Optimization
```typescript
// Use React.memo for metric cards
const MetricCard = React.memo(({ value, trend }) => ...)

// Debounce filter/sort changes
const handleSortChange = debounce((key) => { ... }, 300)

// Memoize table columns
const corpsColumns = useMemo(() => [...], [])
```

## Implementation Checklist

### Phase 1: UI Skeleton (DONE)
- [x] Create page components with mock data
- [x] Layout and responsive design
- [x] Styling and status indicators

### Phase 2: API Integration (TODO)
- [ ] Wire `/api/v1/metrics/dashboard` to MetricsDashboard
- [ ] Wire `/api/v1/scoreboards/corps` to ScoreboardsPage
- [ ] Wire `/api/v1/scoreboards/agents` to ScoreboardsPage
- [ ] Wire `/api/v1/metrics/series` to PerformanceExplorer
- [ ] Implement error handling and loading states

### Phase 3: Real-time Updates (TODO)
- [ ] Implement WebSocket connection for `/ws/metrics`
- [ ] Auto-update dashboard on new events
- [ ] Handle WebSocket disconnection/reconnection
- [ ] Add connectivity indicator

### Phase 4: Advanced Features (TODO)
- [ ] Export to CSV/JSON
- [ ] Custom alert thresholds
- [ ] Saved views/filters
- [ ] Historical comparison
- [ ] Anomaly detection

### Phase 5: Testing (TODO)
- [ ] Unit tests for data formatting
- [ ] Integration tests with mock API
- [ ] E2E tests for user workflows
- [ ] Performance profiling

## Testing Strategy

### Unit Tests
```typescript
// Test metric calculations
describe("MetricCard", () => {
  it("renders success status for good metrics", () => {
    render(<MetricCard value={95} status="good" />)
    expect(screen.getByText("95")).toHaveStyle("color: #52c41a")
  })
})
```

### Integration Tests
```typescript
// Test with mock API
describe("ScoreboardsPage", () => {
  it("displays corps leaderboard from API", async () => {
    mockFetch.get("/api/v1/scoreboards/corps", { corps: [...] })
    render(<ScoreboardsPage />)
    await waitFor(() => {
      expect(screen.getByText("Phantom Regiment")).toBeInTheDocument()
    })
  })
})
```

### E2E Tests
```typescript
// Test user workflows
describe("Dashboard workflow", () => {
  it("allows user to drill down into corps details", () => {
    cy.visit("/dashboard")
    cy.get('[data-cy="corps-row"]:first').click()
    cy.get('[data-cy="detail-modal"]').should("be.visible")
  })
})
```

## Deployment Notes

### Dependencies
```json
{
  "recharts": "^2.0.0",
  "antd": "^5.0.0",
  "dayjs": "^1.11.0"
}
```

### Environment Variables
```bash
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_METRICS_UPDATE_INTERVAL=30000  // milliseconds
```

### Build Optimization
- Code split dashboard pages (lazy load)
- Tree-shake unused Ant Design components
- Compress chart data before transmission

## Future Enhancements

1. **Mobile App**
   - React Native implementation
   - Offline metrics caching
   - Push notifications for alerts

2. **Advanced Analytics**
   - Machine learning anomaly detection
   - Predictive trend analysis
   - Automated alerting rules

3. **Collaboration**
   - Shared dashboards
   - Annotation/commenting
   - Team collaboration features

4. **Customization**
   - Widget library for custom dashboards
   - Saved views and presets
   - Dark mode support

## Sign-Off

Dashboard & Visualization component implementation complete with:
- 3 full-featured React components
- Mock data and placeholder API integration points
- Responsive design and styling
- Documentation for API integration
- Performance optimization recommendations

**Next Steps:**
1. Implement API endpoint integration
2. Add WebSocket for real-time updates
3. Create E2E tests
4. Deploy to production
