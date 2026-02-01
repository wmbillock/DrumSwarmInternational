# Metronome System Agent

The Metronome is a standalone, cron-driven system-level heartbeat that keeps the entire DCI swarm marching autonomously. It operates at the DCI layer (above all corps) and orchestrates:

1. **Ten-Hut (Wake Signals)** — Wakes all active corps' executive directors
2. **Resume-Hut (Stalled Work Detection)** — Alerts corps with stalled reps
3. **Status Gathering** — Collects swarm-wide health metrics
4. **Alert Generation** — Flags unresponsive corps and critical issues

## Architecture

```
┌──────────────────┐
│  Cron (5 min)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   tick.sh        │  ← Lock file, logging, error handling
│   (Bash)         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ metronome_       │  ← Ten-hut/resume-hut dispatch
│ orchestrator.py  │  ← Status gathering & reporting
│ (Python)         │  ← Per-corps tick() integration
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Logs & Reports  │
│  - {timestamp}.log
│  - {timestamp}.json
│  - alerts.log
└──────────────────┘
```

## Setup

### 1. Manual Test

```bash
./scripts/metronome/tick.sh
```

Expected output:
- Lock acquired
- Corps awakened (ten-hut messages logged)
- Stalled reps detected (resume-hut messages logged)
- Swarm status report generated
- JSON and log files created in `logs/metronome/`
- Lock released

### 2. Cron Installation

Add to your crontab (`crontab -e`):

```cron
*/5 * * * * cd /path/to/dci-swarm && ./scripts/metronome/tick.sh >> logs/metronome/cron.log 2>&1
```

**Important**: Replace `/path/to/dci-swarm` with the actual project root path.

### 3. Environment Variables (Optional)

```bash
export METRONOME_ALERT_THRESHOLD=3      # Number of consecutive failures before RED FLAG
export METRONOME_CORPS_TIMEOUT=30        # Timeout per corps (seconds)
export METRONOME_BACKEND_URL=http://localhost:8000  # Backend API URL (future use)
```

## Lock File Mechanism

- **File**: `/tmp/metronome.lock`
- **Timeout**: 300 seconds (5 minutes)
- **Behavior**:
  - If lock file exists and process is running → Exit gracefully
  - If lock file is stale (>300s) → Remove and proceed
  - If lock process is dead → Remove and proceed

This prevents overlapping executions when a tick takes longer than the cron interval.

## Logging

### Text Logs (`logs/metronome/{timestamp}.log`)

Human-readable output with:
- ISO 8601 timestamps
- Per-corps health status
- Ten-hut/resume-hut dispatches
- Alerts and warnings
- Execution summary

### JSON Reports (`logs/metronome/{timestamp}.json`)

Machine-readable structured data:
```json
{
  "timestamp": "2026-02-01T07:30:21.253093+00:00",
  "total_corps": 11,
  "active_corps": 11,
  "corps_health": [
    {
      "corps_id": "...",
      "corps_name": "The Mid Boca Raton Freelancers",
      "status": "on_tour",
      "rehearsal_mode": "run_through",
      "active_sessions": 12,
      "stalled_reps": ["rep_id_1", "rep_id_2"],
      "ed_responding": true,
      "pc_responding": true
    }
  ],
  "alerts": [
    "RED FLAG: Corps xyz (Name) - No ED/PC response"
  ]
}
```

### Alert Log (`logs/metronome/alerts.log`)

Persistent log of RED FLAG events:
```
[2026-02-01T07:30:21.253093+00:00] RED FLAG: Corps b8fb873a (DCI Admin) - No ED/PC response
```

## Commands Dispatched

### Ten-Hut (Wake Signal)

Sent to **every active corps' executive director** on each tick.

**Purpose**: Keep the swarm marching. EDs acknowledge and cascade to their staff.

**Future Integration**: Will send actual messages via the messaging system. Currently logs only.

### Resume-Hut (Stalled Work Alert)

Sent to **executive directors of corps with stalled reps**.

**Stalled Definition**: Reps pending for >5 minutes with no agent activity.

**Purpose**: Alert leadership that work is blocked. ED decides whether to kick, reassign, or escalate.

**Future Integration**: Will include specific rep IDs and last-seen timestamps in message payload.

## Health Metrics

For each corps, the metronome gathers:
- **Sessions**: Active, completed, failed counts
- **Reps**: Pending, in-progress, completed, failed counts
- **Agent Liveness**: ED and PC responding (yes/no)
- **Stalled Work**: List of rep IDs pending >5 minutes
- **Tick Duration**: Time spent processing this corps

Aggregated into swarm-wide totals:
- Total corps
- Active corps (ON_TOUR or WINTER_CAMPS)
- Total sessions
- Total reps

## Error Handling

### Per-Corps Errors

If a corps tick fails (e.g., database error, timeout):
- Error logged
- Added to alerts
- Tick continues with next corps
- **No cascading failure**

### Backend Unavailability

If the database is unreachable:
- Fatal error logged
- Script exits with code 1
- Lock released
- **Cron will retry in 5 minutes**

### Concurrent Execution

If two ticks overlap (e.g., previous tick hasn't finished):
- Second instance detects lock
- Logs warning and exits
- **No duplicate work**

## Watchdog Integration

The metronome integrates with the existing per-corps watchdog system (`backend/tools/metronome.py`):

- **Liveness Monitoring**: Checks if agents are alive
- **Rep Reclamation**: Resets orphaned reps to pending
- **GUPP Enforcement**: Kicks idle agents
- **Watchdog Chain**: Flags dead critical roles (timing_judge, drum_major, caption heads)

Circuit breaker: If a role has 5+ short-lived sessions (<60s) in the last 10 minutes, respawn is skipped to avoid infinite loops.

## Troubleshooting

### No logs appearing

```bash
# Check lock file
ls -la /tmp/metronome.lock

# Remove stale lock
rm /tmp/metronome.lock

# Run manually
./scripts/metronome/tick.sh
```

### "ImportError: cannot import name..."

Database connection issue. Verify:
```bash
ls -la dci_swarm.db
python3 -c "from backend.database import create_db_engine; print('OK')"
```

### Tick takes >5 minutes

Increase cron interval or investigate slow corps. Check per-corps tick durations in JSON reports.

### Lock file always stale

System clock issue or process killing. Check:
```bash
date -u  # Should be UTC
ps aux | grep metronome  # Should show no orphans
```

## Future Enhancements

1. **Messaging Integration**: Replace log-only ten-hut/resume-hut with actual backend messages
2. **Dashboard**: Real-time web UI parsing JSON reports
3. **Alerting**: Email/Slack notifications for RED FLAGS
4. **Metrics**: Prometheus exporter for Grafana dashboards
5. **Distributed Locking**: Redis/etcd for multi-server deployments

## Testing

### Manual Test Suite

```bash
# 1. Single execution
./scripts/metronome/tick.sh

# 2. Concurrent execution (lock test)
./scripts/metronome/tick.sh & sleep 0.1 && ./scripts/metronome/tick.sh & wait

# 3. Verify lock prevents overlap
grep -r "Another metronome instance" logs/metronome/

# 4. Check JSON output
ls -lh logs/metronome/*.json
cat logs/metronome/*.json | jq .

# 5. Verify alerts
cat logs/metronome/alerts.log
```

### Expected Behavior

- ✅ Lock file prevents concurrent execution
- ✅ Stale locks (>300s) are removed automatically
- ✅ Ten-hut sent to all active corps
- ✅ Resume-hut sent only to corps with stalled work
- ✅ JSON reports written with structured data
- ✅ Alerts logged for unresponsive corps
- ✅ Per-corps errors don't block other corps

## Related Files

- `backend/tools/metronome.py` — Per-corps tick logic (liveness, GUPP, watchdog)
- `backend/tools/metronome_orchestrator.py` — System-level orchestrator
- `scripts/metronome/tick.sh` — Bash entry point
- `logs/metronome/` — All outputs
- `shows/metronome-system-agent/` — Show specification and design notes
