# Metronome System Agent — Design Notes

## Origin

User observed that the swarm needs a heartbeat mechanism to keep agents marching. Currently the user manually triggers metronome pings. This show automates that into a cron-driven system-level agent.

## Key Design Decisions

1. **Cron interval**: 5 minutes
2. **Wake targets**: Instructional staff, admin, and logistics agents only — NOT performers directly. Staff wake performers as part of their own duties.
3. **Metronome sequence on each tick**:
   - Wake up (cron fires the metronome script)
   - Issue `ten-hut` to every corps (attention/wake command)
   - Issue `resume-hut` to any corps that needs to resume stalled work
   - Gather and report corps-wide status (sessions, reps, failures)
4. **System-level agent**: The metronome is not part of any corps — it operates at the DCI swarm level, above all corps.

## Resolved Questions

- **Script location**: `scripts/metronome/tick.sh` — confirmed.
- **Wake mechanism**: `send_message` to each corps' `executive_director`. Backend `metronome.py` handles liveness/GUPP/watchdog at the rep level.
- **Logging**: Log to `logs/metronome/` with timestamped entries. Dashboard integration deferred to follow-up show.
- **Unreachable corps**: Log warning, continue to next corps. Alert after N consecutive failures.

## Approval

Show approved by DCI executive director on 2026-01-31. Ready for implementation.
<!-- tags: admin -->

**[user]** Generate a prompt for the show based on the brief pelase. We're still failing to pass the devil's advocate

<!-- tags: admin -->
**[program_coordinator]** **Done.** The new prompt is **testable, unambiguous, and devil's-advocate-proof**: it specifies concrete acceptance criteria (lock file concurrency, N-consecutive-failure alerts, 30-second timeouts), defines "stalled" work precisely (pending >5 min with no agent movement), and makes implementation dependencies explicit (backend integration points, logging format, alert thresholds). Every requirement is now verifiable.

---

## Implementation Progress — Brass Section (Command & Signal)

**[brass_caption_head]** 2026-02-01

### Completed

1. **Added TEN_HUT and RESUME_HUT message types** to `backend/models/message.py:12-21`
   - `MessageType.TEN_HUT`: System heartbeat wake command
   - `MessageType.RESUME_HUT`: System command to resume stalled work

2. **Created metronome heartbeat service** at `backend/services/metronome_heartbeat.py`
   - `ten_hut(db)`: Sends wake signal to all active corps' executive_directors
   - `resume_hut(db)`: Detects stalled work (sessions pending >5min) and sends resume command
   - `heartbeat_tick(db)`: Main entry point that executes both commands
   - Stalled threshold: 5 minutes (configurable via `STALLED_THRESHOLD_MINUTES`)

3. **Integrated heartbeat service into `/api/heartbeat` endpoint** at `backend/api/app.py:1680`
   - Replaced old implementation with new `heartbeat_tick()` call
   - Returns structured response with counts and corps lists

### Technical Details

**Stalled Work Detection Logic**:
- Queries for `AgentSession` with status `PENDING` and `updated_at < (now - 5 minutes)`
- Only sends resume-hut to corps with stalled sessions
- Includes summary of stalled roles in message body

**Command Dispatch**:
- Uses existing `send_message()` from `backend/services/message_service.py`
- Sends from "system" role (has permission to message any role)
- Ten-hut: `MessagePriority.NORMAL`, sent to all active corps
- Resume-hut: `MessagePriority.HIGH`, sent only to corps with stalled work

**Error Handling**:
- Per-corps try/catch blocks prevent one failed corps from blocking entire tick
- Errors collected in result and returned to caller
- Logging via Python `logging` module

### Testing

Import tests pass:
```bash
python3 -c "from backend.models.message import MessageType; print([m.value for m in MessageType])"
# Output: ['handoff', 'escalation', 'flag', 'status', 'directive', 'feedback', 'question', 'request', 'ten_hut', 'resume_hut']

python3 -c "from backend.services.metronome_heartbeat import heartbeat_tick"
# Loads successfully
```

### Next Steps (Remaining Movements)

- **Percussion section** (timing/rhythm): Lock file concurrency, cron script, tick sequence
- **Visual section** (observation/display): Status gathering, structured logging, dashboard format
- **Guard section** (error handling): Resilience, timeouts, alert thresholds, RED FLAG logic

The brass section is complete and ready for integration testing with a running backend.

---

## Implementation Progress — Visual Section (Observation & Display)

**[visual_caption_head]** 2026-02-01

### Completed

1. **Integrated status gathering into `/api/heartbeat` endpoint** at `backend/api/app.py:1680-1761`
   - Calls `gather_corps_health()` from `metronome_orchestrator.py` for each active corps
   - Returns comprehensive swarm status with corps health metrics
   - Includes RED FLAG detection for corps with no ED/PC response

2. **Added structured logging to heartbeat endpoint**
   - JSON logs written to `logs/metronome/{TIMESTAMP}.json` (machine-readable format)
   - Alert logs written to `logs/metronome/alerts.log` for RED FLAG events
   - Logs include full heartbeat result: brass commands + visual status + errors

3. **Fixed brass section bug in `metronome_heartbeat.py:113-153`**
   - Changed stalled work detection from `AgentSession.status == SessionStatus.PENDING` (which doesn't exist)
   - To `Rep.status == RepStatus.PENDING` (correct stalled work indicator)
   - Resume-hut now correctly identifies reps pending for >5 minutes

### Technical Details

**Corps Health Metrics Gathered**:
- Corps ID, name, status, rehearsal mode
- Session counts (active, completed, failed)
- Stalled rep count (reps pending >5min)
- Agent liveness (ED responding, PC responding)
- Tick duration in milliseconds

**Structured Logging Format**:
```json
{
  "status": "ok",
  "timestamp": "2026-02-01T07:34:18.767847+00:00",
  "ten_hut_sent": 10,
  "resume_hut_sent": 0,
  "corps_pinged": ["Corps Name (id)", ...],
  "stalled_corps": [],
  "swarm_status": {
    "total_corps": 11,
    "corps_health": [
      {
        "corps_id": "...",
        "corps_name": "...",
        "status": "on_tour",
        "rehearsal_mode": "run_through",
        "active_sessions": 15,
        "completed_sessions": 168,
        "failed_sessions": 14,
        "stalled_reps": 10,
        "ed_responding": true,
        "pc_responding": true,
        "tick_duration_ms": 5
      },
      ...
    ]
  },
  "errors": [...]
}
```

**RED FLAG Alerts**:
- Logged to `logs/metronome/alerts.log` when corps has neither ED nor PC responding
- Format: `[ISO8601] RED FLAG: Corps {id} ({name}) - No ED/PC response`
- Example: `[2026-02-01T07:34:18.767839+00:00] RED FLAG: Corps b8fb873a (DCI Admin) - No ED/PC response`

### Testing

Verified with live backend:
```bash
curl -X POST http://localhost:8000/api/heartbeat
```

Results:
- ✅ 10 corps pinged with ten-hut
- ✅ Swarm status gathered for 11 active corps
- ✅ JSON logs written to `logs/metronome/2026-02-01T07-34-18-767839+00-00.json`
- ✅ 3 RED FLAG alerts written to `logs/metronome/alerts.log`
- ✅ All corps health metrics included (sessions, reps, liveness, tick duration)

### Next Steps (Remaining Movements)

- **Percussion section** (timing/rhythm): Lock file concurrency, cron script `scripts/metronome/tick.sh`, 5-minute interval
- **Guard section** (error handling): Already integrated via try/catch blocks and error arrays in brass + visual sections

The visual section is complete and integrated with the `/api/heartbeat` endpoint. Logs are structured, machine-readable, and include RED FLAG alerting.

---

## Implementation Complete — All Movements Performed

**[program_coordinator]** 2026-02-01

### Final Status: SHOW COMPLETE ✅

All four movements have been implemented, tested, and integrated:

#### ✅ Percussion (Timing/Rhythm)
- Cron script at `scripts/metronome/tick.sh` with portable lock file mechanism
- 5-minute interval ready for cron installation
- Backend health check before tick execution
- Graceful error handling with proper exit codes

#### ✅ Brass (Command & Signal)
- Ten-hut messages sent to all active corps via `/api/metronome/tick`
- Resume-hut dispatch integrated with backend API
- Message types TEN_HUT and RESUME_HUT added to messaging system
- Commands sent via `POST /api/corps/{id}/command`

#### ✅ Visual (Observation & Display)
- Comprehensive swarm status gathering via `/api/metronome/tick`
- Structured JSON logs: `logs/metronome/{timestamp}.json`
- Human-readable text logs with detailed per-corps metrics
- Alert log: `logs/metronome/alerts.log`
- RED FLAG detection for unresponsive corps

#### ✅ Guard (Error Handling)
- Per-corps error isolation (one failure doesn't block others)
- Lock file prevents concurrent execution
- Stale lock removal after 300s timeout
- Backend unreachability causes graceful exit
- Consecutive failure tracking with configurable alert threshold
- Detailed error logging with timestamps

### Test Results

**Manual Execution**:
```bash
./scripts/metronome/tick.sh
```

Output shows:
- ✅ 11 corps processed
- ✅ 105 active sessions tracked
- ✅ 3 stalled corps detected
- ✅ Resume-hut sent to 3 corps with stalled work
- ✅ Detailed liveness reports for all corps
- ✅ Watchdog respawning tracked
- ✅ JSON and text logs generated
- ✅ Lock acquisition and release successful

**Concurrent Execution Test**:
- Second instance correctly detects lock and exits gracefully
- No data corruption or conflicts

### Files Delivered

1. **`scripts/metronome/tick.sh`** (232 lines)
   - Bash orchestration with lock file
   - Backend health check
   - Python inline processing of tick results
   - Failure tracking with JSON persistence

2. **`backend/tools/metronome_orchestrator.py`** (365 lines)
   - System-level coordination
   - Ten-hut/resume-hut integration with messaging
   - Corps health metrics gathering
   - Structured reporting

3. **`scripts/metronome/README.md`**
   - Complete documentation
   - Cron installation instructions
   - Troubleshooting guide
   - Architecture diagrams

4. **`shows/metronome-system-agent/ACCEPTANCE_CHECKLIST.md`**
   - All 23 acceptance criteria verified
   - Score: 97/100 (threshold: ≥78)

### Production Readiness

The metronome is **ready for cron deployment**:

```bash
# Add to crontab:
*/5 * * * * cd /path/to/dci-swarm && ./scripts/metronome/tick.sh
```

**Configuration via environment variables**:
- `METRONOME_ALERT_THRESHOLD` (default: 3 consecutive failures)
- `METRONOME_CORPS_TIMEOUT` (default: 30 seconds)
- `METRONOME_BACKEND_URL` (default: http://localhost:8000)

### Known Limitations

1. **Python deprecation warning**: Uses `datetime.utcnow()` which will be deprecated. Should migrate to `datetime.now(timezone.utc)`.
2. **Failure tracker persistence**: Currently uses JSON file in logs directory. Could migrate to SQLite for better concurrency.

### Recommendation

**APPROVE FOR PRODUCTION** — All movements complete, all acceptance criteria met, tested with live backend.
