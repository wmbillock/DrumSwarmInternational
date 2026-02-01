# Data Collection & Instrumentation — Design Notes

## Session: Front Ensemble Tech — February 1, 2026

### Objective
Instrument the DCI Swarm system to capture raw performance metrics: task throughput, latency, error rates, agent utilization.

### Analysis

The DCI Swarm consists of:
- **Corps** — Organizational units with states (initializing → winter_camps → on_tour → completed)
- **Agents** — LLM-powered workers in roles (ED, PC, brass_tech, front_ensemble_tech, etc.)
- **Reps** — Discrete work items with states (pending → assigned → in_progress → review → completed/failed)
- **Messages** — Async communication system (threads, messages, archives)
- **Shows/Seasons/Competitions** — Performance tracking structure

**Key Observation:** The system already tracks state transitions but has no instrumentation to measure:
- How long does a rep actually take to complete? (latency)
- What's our throughput? (reps completed per hour/day)
- Which agents are most active? (utilization)
- Where do failures happen? (error patterns)
- Is the system speeding up or slowing down? (trends)

### Design

I will instrument the system at these critical points:

#### 1. **Rep Lifecycle Metrics** (highest priority)
   - When: Rep transitions from pending → assigned → in_progress → review → completed
   - Capture: timestamp, rep_id, segment_id, status, assigned_to
   - Calculate: duration per state, total end-to-end time

#### 2. **Agent Session Metrics**
   - When: Agent session created, updated, completed
   - Capture: session_id, agent_role, corps_id, status, duration
   - Calculate: sessions per agent per day, avg duration, activity count

#### 3. **Message Throughput**
   - When: Message posted to thread
   - Capture: timestamp, thread_id, from_role, to_role, message_type
   - Calculate: messages per minute, bottlenecks by role pair

#### 4. **Database Query Latency**
   - When: Major queries execute
   - Capture: query_type, duration_ms, rows_affected
   - Calculate: p50, p95, p99 latencies per query type

#### 5. **Corps Progression**
   - When: Corps state changes
   - Capture: corps_id, old_status, new_status, timestamp
   - Calculate: time to reach each stage, success rate

### Implementation Strategy

**Phase 1: Measurement Infrastructure**
1. Create `backend/services/metrics.py` with:
   - `Event` dataclass for structured event recording
   - `MetricsCollector` class for recording and querying
   - Enum for all metric types

2. Create database schema:
   - `metrics_events` table (immutable event log)
   - Indexed on: timestamp, metric_type, corps_id, segment_id

3. Integration points:
   - Hook into `Rep.status` property setter or `rep_service.transition_rep()`
   - Hook into `AgentSession.status` changes
   - Hook into `Message` creation
   - Hook into `task_manager.execute_agent()` for latency

**Phase 2: Event Recording**
- Wire up collectors at each integration point
- Ensure no performance impact (async logging)
- Add configuration for sampling if needed

**Phase 3: Basic Querying**
- `get_events(metric_type, time_range, filters)` — retrieve raw events
- `get_latency_percentiles(query_type, time_range)` — p50/p95/p99
- `get_throughput(time_range)` — reps per hour, messages per minute

**Phase 4: Testing**
- Unit tests for MetricsCollector
- Integration tests for rep→event mapping
- Performance tests (ensure <5ms overhead per record)

### Deliverables for Movement I

1. **`backend/services/metrics.py`** (~300 lines)
   - `MetricType` enum
   - `MetricEvent` dataclass
   - `MetricsCollector` class

2. **Database schema** (alembic migration or schema patch)
   - `CREATE TABLE metrics_events (...)`

3. **Integration in:**
   - `backend/services/rep_service.py` — hook transition_rep()
   - `backend/services/agent_runtime.py` — hook session lifecycle
   - `backend/services/messaging_service.py` — hook message creation

4. **Tests**
   - `backend/tests/test_metrics_collection.py` (~150 lines)
   - Coverage: collection, filtering, latency calculations

### Edge Cases & Resilience

1. **Concurrent Metrics Recording**
   - Database ensures atomicity
   - No locks needed (append-only log)

2. **Stale/Missing Events**
   - Events are immutable; no correction needed
   - Aggregation layers handle gaps

3. **Performance Degradation**
   - If metrics recording slows system, enable sampling
   - Only record 1-in-100 events during high load

4. **Data Cleanup**
   - Retention: keep 30 days of raw events
   - Aggregation layer handles historical compression

### Definition of Done

For this rep (`de1e1cba...`), completion means:

✅ **Code**
- [ ] `backend/services/metrics.py` implemented and tested
- [ ] Database schema for `metrics_events` created
- [ ] Integration points wired up in rep_service, agent_runtime
- [ ] 3+ integration tests passing

✅ **Verification**
- [ ] 10+ different metric types being recorded
- [ ] Metrics are queryable by time range and filter
- [ ] No performance regression (queries <5ms)

✅ **Documentation**
- [ ] Docstrings on all public classes/functions
- [ ] Example usage in test file

---

## Work Log

### Session Start: 2026-02-01 14:00 UTC
- Analyzed segment structure
- Created show spec with full 4-movement breakdown
- Documented Movement I design and implementation strategy
- Identified 5 key metric areas to instrument
- Ready to implement Phase 1: Measurement Infrastructure

**Next Rep:** `c8288dcb...` (Aggregation & Storage movement)
