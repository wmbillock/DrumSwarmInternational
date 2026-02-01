# Metronome System Agent — Implementation Prompt

## Objective

Build a standalone, cron-driven system-level heartbeat that keeps the entire DCI swarm marching autonomously every 5 minutes. The Metronome is **not part of any corps** — it operates above the corps hierarchy and orchestrates staff-level wake signals, work resumption, and swarm-wide status reporting.

## Scope

### 1. Cron Entry Point (`scripts/metronome/tick.sh`)

- Create a bash script at `scripts/metronome/tick.sh` that:
  - Acquires a lock file (`/tmp/metronome.lock` or similar) to prevent overlapping executions
  - Calls the backend's metronome endpoint (or invokes metronome logic directly via Python)
  - Logs all output to `logs/metronome/{TIMESTAMP}.log` (create directory if missing)
  - Releases the lock on exit (even on error)
  - Is idempotent: safe to run multiple times concurrently; second invocation waits or exits gracefully
- Register crontab entry: `*/5 * * * * /path/to/scripts/metronome/tick.sh` (user runs this manually or via automation later)
- Script **must not fail silently** — log all errors with timestamps

### 2. Ten-Hut / Resume-Hut Command Dispatch

- **Ten-Hut**: On each tick, send a wake signal to **every active corps**' `executive_director` agents
  - Command type: `ten-hut` (string message)
  - Sent via backend messaging system (use existing `send_message` or equivalent)
  - ED receives it, acknowledges it, and cascades to PC → caption heads → techs as needed
  - Message includes: timestamp, corps ID, expected response deadline
- **Resume-Hut**: On each tick, detect corps with stalled sessions/reps (pending for >N minutes, no recent activity)
  - Send `resume-hut` command to EDs of stalled corps only
  - Message includes: which sessions/reps are stalled, what the last seen timestamp was
  - EDs decide whether to kick those reps or change strategy
- **Non-targets**: Performers are **never** sent ten-hut/resume-hut directly — only staff

### 3. Status Gathering & Reporting

- After issuing commands, query each active corps for:
  - **Sessions**: Count of active, completed, failed (current tick only)
  - **Reps**: Count pending, in-progress, completed, failed (current tick only)
  - **Agent liveness**: ED, PC, caption heads responding (yes/no flags)
  - **Last successful tick**: Timestamp of last metronome tick that completed without errors
  - **Current rehearsal mode**: (BASICS, SECTIONALS, FULL_ENSEMBLE, RUN_THROUGH)
- Aggregate into a swarm-wide summary report:
  - Total active corps, total sessions, total reps by status
  - Corps-by-corps liveness matrix
  - Any corps that failed to respond on N consecutive ticks → alert ("RED FLAG: Corps {id} unresponsive for {N} ticks")
- Write report to `logs/metronome/{TIMESTAMP}.log` in a structured, readable format (JSON or plain text, consistent)

### 4. Error Handling & Resilience

- **Unreachable corps**: Log a warning with timestamp and corps ID, continue to next corps. Do not block the entire tick.
- **Timeout per corps**: Set a 30-second timeout for each corps wake attempt. If no response within 30s, log and move on.
- **Lock file**: Use flock or similar to prevent two ticks from running simultaneously. If lock is held, the second invocation logs a warning and exits (do not wait).
- **Alert mechanism**: If a corps fails to respond for N consecutive ticks (suggest N=3), log a RED FLAG alert in `logs/metronome/alerts.log` with timestamp and corps ID.
- **Graceful degradation**: If the metronome cannot reach the backend, log the error and exit with a non-zero code. Do not proceed with a partial tick.

## Acceptance Criteria

✅ **Script Creation & Registration**
- [ ] `scripts/metronome/tick.sh` exists, is executable, and runs without errors on first invocation
- [ ] Lock file mechanism prevents overlapping executions (verify by running two instances concurrently)
- [ ] Crontab entry (or instruction to add it) is documented or ready to use

✅ **Command Dispatch**
- [ ] `ten-hut` message sent to every active corps' ED on each tick (verified via logs)
- [ ] `resume-hut` sent only to corps with stalled work (verify stalled detection logic)
- [ ] Messages include timestamp and corps ID
- [ ] Performers are never directly messaged by the metronome (code inspection)

✅ **Status Gathering**
- [ ] Swarm-wide status report generated after each tick (sessions, reps, agent liveness)
- [ ] Report includes all active corps, aggregated counts, and liveness matrix
- [ ] Report written to `logs/metronome/{TIMESTAMP}.log` with readable format
- [ ] Corps-specific data matches database state (spot-check 3+ corps)

✅ **Error Handling**
- [ ] Unreachable corps logged with timestamp; tick continues (not blocked)
- [ ] Timeout per corps enforced (30s); exceeded timeouts logged
- [ ] Lock file blocks concurrent ticks (second invocation exits with warning)
- [ ] N-consecutive-failure alert logged to `alerts.log` (test with mock unresponsive corps)
- [ ] Backend unavailability causes graceful exit with error log (non-zero code)

✅ **Logging & Observability**
- [ ] All output logged with ISO 8601 timestamps to `logs/metronome/{TIMESTAMP}.log`
- [ ] Log entries include: tick start/end, corps awakened, commands sent, status aggregated, errors
- [ ] Alert log created and populated for RED FLAG events
- [ ] Logs are machine-readable (JSON or structured format) for future dashboard integration

✅ **Integration & Testing**
- [ ] Metronome works with existing backend (no new backend changes required, or minimal API extension)
- [ ] Manual test: Run `./scripts/metronome/tick.sh` multiple times, verify lock prevents overlap and logs appear
- [ ] Verify ED agents receive and acknowledge ten-hut messages in their logs
- [ ] Verify stalled work detection identifies actual stalled reps (define "stalled" as pending >5 min with no agent movement)

## Implementation Notes

- **Backend Integration**: If `backend/tools/metronome.py` exists and provides wake/status methods, use them. If not, use existing `send_message` API + direct DB queries for status.
- **Statelessness**: Each tick is independent. No persistent state between ticks (except lock file). Stalled detection is computed per-tick from DB timestamps.
- **Logging Folder**: Create `logs/metronome/` if it doesn't exist. Use ISO 8601 timestamps for filenames: `logs/metronome/2026-02-01T09:35:00Z.log`.
- **Alert Thresholds**: Default N=3 consecutive failures before RED FLAG. Configurable via env var (e.g., `METRONOME_ALERT_THRESHOLD`).
- **Future**: Dashboard integration (parsing these logs) is a follow-up show. For now, focus on correct logging format.

## Definition of Done

- [ ] Bash script runs successfully on a 5-minute cron cycle
- [ ] All four movements (script, commands, status, errors) are implemented and tested
- [ ] Logs are produced with every tick, no silent failures
- [ ] Devil's advocate passes: all acceptance criteria met, no ambiguities, no edge cases unhandled
