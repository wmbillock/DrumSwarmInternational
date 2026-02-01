#!/usr/bin/env bash
#
# Metronome Tick Script
# Runs every 5 minutes via cron to keep the DCI swarm marching
#
# Usage: */5 * * * * /path/to/scripts/metronome/tick.sh
#

set -euo pipefail

# Configuration
LOCK_FILE="/tmp/metronome.lock"
LOCK_TIMEOUT=300  # 5 minutes - same as cron interval
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs/metronome"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_FILE="${LOG_DIR}/${TIMESTAMP}.log"
ALERT_LOG="${LOG_DIR}/alerts.log"
FAILURE_TRACKER="${LOG_DIR}/.failure_counts.json"
BACKEND_URL="${METRONOME_BACKEND_URL:-http://localhost:8000}"
ALERT_THRESHOLD="${METRONOME_ALERT_THRESHOLD:-3}"
CORPS_TIMEOUT="${METRONOME_CORPS_TIMEOUT:-30}"

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Logging helper
log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*" | tee -a "${LOG_FILE}"
}

# Error handler
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Lock file acquisition (portable - works on macOS and Linux)
acquire_lock() {
    # Check if lock file exists and is recent
    if [ -f "${LOCK_FILE}" ]; then
        # Check if the process is still running
        LOCK_PID=$(cat "${LOCK_FILE}" 2>/dev/null || echo "")
        if [ -n "${LOCK_PID}" ] && kill -0 "${LOCK_PID}" 2>/dev/null; then
            log "WARN: Another metronome instance is running (PID: ${LOCK_PID}). Exiting."
            exit 0
        fi

        # Check if lock file is stale (older than LOCK_TIMEOUT)
        if [ "$(uname)" == "Darwin" ]; then
            # macOS stat
            LOCK_AGE=$(($(date +%s) - $(stat -f %m "${LOCK_FILE}")))
        else
            # Linux stat
            LOCK_AGE=$(($(date +%s) - $(stat -c %Y "${LOCK_FILE}")))
        fi

        if [ ${LOCK_AGE} -gt ${LOCK_TIMEOUT} ]; then
            log "WARN: Removing stale lock file (age: ${LOCK_AGE}s > ${LOCK_TIMEOUT}s)"
            rm -f "${LOCK_FILE}"
        else
            log "WARN: Lock file exists but process is dead. Removing stale lock."
            rm -f "${LOCK_FILE}"
        fi
    fi

    # Create lock file with current PID
    echo $$ > "${LOCK_FILE}"
    log "Lock acquired (PID: $$)"
}

# Release lock on exit
release_lock() {
    rm -f "${LOCK_FILE}"
    log "Lock released"
}

# Trap to ensure lock is released
trap release_lock EXIT INT TERM

# Main execution
main() {
    log "=== Metronome Tick Started ==="
    log "Project root: ${PROJECT_ROOT}"
    log "Log file: ${LOG_FILE}"

    # Acquire lock first
    acquire_lock

    # Health check: verify backend is reachable
    if ! curl -sf --max-time 5 "${BACKEND_URL}/api/system-health" > /dev/null 2>&1; then
        error_exit "Backend unreachable at ${BACKEND_URL}. Aborting tick."
    fi
    log "Backend reachable at ${BACKEND_URL}"

    # Execute system-wide tick
    log "Calling POST ${BACKEND_URL}/api/metronome/tick ..."
    TICK_RESPONSE=$(curl -sf --max-time 120 \
        -X POST \
        -H "Content-Type: application/json" \
        "${BACKEND_URL}/api/metronome/tick" 2>&1) || {
        error_exit "System tick API call failed: ${TICK_RESPONSE}"
    }

    # Write raw JSON response
    echo "${TICK_RESPONSE}" > "${LOG_FILE%.log}.json"
    log "Raw JSON written to ${LOG_FILE%.log}.json"

    # Find Python
    PYTHON="${PROJECT_ROOT}/.venv/bin/python"
    if [ ! -x "${PYTHON}" ]; then
        PYTHON="python3"
    fi

    # Process results: log summary, issue resume-hut to stalled corps, track failures
    "${PYTHON}" << 'PYEOF' "${TICK_RESPONSE}" "${LOG_FILE}" "${ALERT_LOG}" "${FAILURE_TRACKER}" "${ALERT_THRESHOLD}" "${BACKEND_URL}" "${CORPS_TIMEOUT}"
import json, sys, os
from datetime import datetime

response = json.loads(sys.argv[1])
log_file = sys.argv[2]
alert_log = sys.argv[3]
failure_file = sys.argv[4]
alert_threshold = int(sys.argv[5])
backend_url = sys.argv[6]
corps_timeout = int(sys.argv[7])

def log(level, msg):
    ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    line = f'[{ts}] [{level}] {msg}'
    print(line)
    with open(log_file, 'a') as f:
        f.write(line + '\n')

def alert(msg):
    ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    line = f'[{ts}] [RED FLAG] {msg}'
    print(line, file=sys.stderr)
    with open(log_file, 'a') as f:
        f.write(line + '\n')
    with open(alert_log, 'a') as f:
        f.write(line + '\n')

# Load failure tracker
failure_counts = {}
if os.path.exists(failure_file):
    try:
        with open(failure_file) as f:
            failure_counts = json.load(f)
    except (json.JSONDecodeError, IOError):
        failure_counts = {}

# Log summary
summary = response.get('summary', {})
log('INFO', f"Total corps: {response.get('total_corps', 0)}")
log('INFO', f"Active sessions: {summary.get('total_active_sessions', 0)}")
log('INFO', f"Stalled corps: {summary.get('total_stalled_corps', 0)}")
log('INFO', f"Reclaimed reps: {summary.get('total_reclaimed', 0)}")
log('INFO', f"GUPP kicked: {summary.get('total_idle_kicked', 0)}")

# Process each corps
import urllib.request
for corps in response.get('corps', []):
    cid = corps['corps_id']
    cname = corps.get('corps_name', cid[:8])
    log('INFO', f"--- Corps '{cname}' ({cid[:8]}...) [{corps.get('corps_status')}] ---")

    # Sessions
    s = corps.get('sessions', {})
    log('INFO', f"  Sessions: {s.get('active', 0)} active, {s.get('completed', 0)} completed, {s.get('failed', 0)} failed")

    # Reps
    r = corps.get('reps', {})
    log('INFO', f"  Reps: {r.get('pending', 0)} pending, {r.get('assigned', 0)} assigned, {r.get('in_progress', 0)} in-progress, {r.get('completed', 0)} completed, {r.get('failed', 0)} failed")

    # Liveness
    liveness = corps.get('liveness', {})
    live_roles = [role for role, alive in liveness.items() if alive]
    dead_roles = [role for role, alive in liveness.items() if not alive]
    log('INFO', f"  Liveness: {len(live_roles)} responding, {len(dead_roles)} inactive")
    if dead_roles:
        log('WARN', f"  Inactive roles: {', '.join(dead_roles)}")

    # Metronome results
    met = corps.get('metronome', {})
    if met.get('reclaimed', 0) > 0:
        log('WARN', f"  Reclaimed {met['reclaimed']} orphan reps")
    if met.get('idle_kicked', 0) > 0:
        log('WARN', f"  GUPP kicked {met['idle_kicked']} idle reps")
    if met.get('watchdog_respawned'):
        log('WARN', f"  Watchdog respawned: {', '.join(met['watchdog_respawned'])}")

    # Stalled work → issue resume-hut
    stalled = corps.get('stalled_reps', [])
    if stalled:
        log('WARN', f"  {len(stalled)} stalled reps detected — issuing resume-hut")
        try:
            req = urllib.request.Request(
                f'{backend_url}/api/corps/{cid}/command',
                data=json.dumps({'command': 'resume_hut'}).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            urllib.request.urlopen(req, timeout=corps_timeout)
            log('INFO', f"  resume-hut sent to corps {cid[:8]}")
            failure_counts[cid] = 0
        except Exception as e:
            log('ERROR', f"  Failed to send resume-hut to corps {cid[:8]}: {e}")
            failure_counts[cid] = failure_counts.get(cid, 0) + 1
    else:
        failure_counts[cid] = 0

    # Check consecutive failure threshold
    if failure_counts.get(cid, 0) >= alert_threshold:
        alert(f"Corps '{cname}' ({cid}) unresponsive for {failure_counts[cid]} consecutive ticks")

# Save failure tracker
with open(failure_file, 'w') as f:
    json.dump(failure_counts, f)

log('INFO', '--- Tick complete ---')
PYEOF

    if [ $? -ne 0 ]; then
        error_exit "Result processing failed"
    fi

    log "=== Metronome Tick Completed Successfully ==="
}

# Execute main
main
