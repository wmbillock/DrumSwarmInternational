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
