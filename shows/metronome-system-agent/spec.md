# Metronome System Agent

## Goal
Build a standalone, cron-driven system-level heartbeat that keeps the entire DCI swarm marching autonomously every 5 minutes. The Metronome operates above the corps hierarchy and orchestrates staff-level wake signals, work resumption, and swarm-wide status reporting.

## Acceptance Criteria
1. `scripts/metronome/tick.sh` exists and is executable with lock file mechanism preventing overlapping executions
2. `ten-hut` message sent to every active corps ED on each tick via backend messaging system
3. `resume-hut` sent only to corps with stalled work (pending >5 min with no agent activity)
4. Performers are never directly messaged by the metronome
5. Swarm-wide status report generated after each tick (sessions, reps, agent liveness per corps)
6. Report written to `logs/metronome/{TIMESTAMP}.log` in structured format
7. Corps that fail to respond for 3 consecutive ticks trigger RED FLAG alert in `logs/metronome/alerts.log`
8. 30-second timeout per corps wake attempt; unreachable corps logged and skipped
9. Lock file prevents concurrent ticks (flock-based)
10. Backend unavailability causes graceful exit with error log

## Constraints
- System-level daemon (outside any corps)
- Stateless per tick with lock file concurrency
- Targets: ED, PC, caption heads, logistics staff only (NOT performers)
- Stalled detection: >5 min pending with no agent activity
- Cron interval: 5 minutes
- Lock timeout: 300 seconds
- N=3 consecutive tick failures before RED FLAG alert
- 30 sec per corps, 4 min total maximum tick duration