---
show_slug: metronome-system-agent
version: 1
created_at: "2026-01-31"
approved_at: "2026-01-31"
approved_by: executive_director
roles_consulted: [executive_director, program_coordinator]
model: null
run_id: null
status: approved
---

# Metronome System Agent

## Summary

A standalone, system-level agent that runs on a 5-minute cron and keeps the entire DCI swarm marching. It is the swarm's heartbeat.

## Movements

### 1. Metronome Script & Cron Setup

**Caption**: percussion (timing/rhythm — fitting)

- Create `scripts/metronome/tick.sh` — the entry point invoked by cron
- Register a crontab entry: `*/5 * * * * /path/to/tick.sh`
- Script should be idempotent and safe to run concurrently (lock file or similar)

### 2. Ten-Hut / Resume-Hut Command Mechanism

**Caption**: brass (command & signal)

- Define how `ten-hut` wakes instructional staff, admin, and logistics agents for each corps
- Define how `resume-hut` detects stalled work and resumes it
- Target agents: executive_director, program_coordinator, caption_heads, logistics — NOT performers
- Performers are woken by their respective staff as needed

### 3. Status Gathering & Reporting

**Caption**: visual (observation & display)

- After issuing commands, the metronome gathers status from all corps
- Collects: active/completed/failed sessions, pending/in-progress/completed/failed reps
- Outputs a swarm-wide summary (same format as current METRONOME STATUS PING)
- Log output to `logs/metronome/` with timestamped entries

### 4. Error Handling & Resilience

**Caption**: guard (protection)

- Handle unreachable corps gracefully (log warning, continue to next)
- Lock file to prevent overlapping ticks
- Timeout per corps wake attempt
- Alert mechanism if a corps fails to respond on N consecutive ticks

## Constraints

- Must not wake performers directly
- Must be idempotent — safe if two ticks overlap
- Must run at the DCI system level, not inside any single corps
- 5-minute interval is the target cadence

## Resolved Questions

- **Agent wake mechanism**: Use `send_message` to corps `executive_director` agents with ten-hut/resume-hut commands. The existing `backend/tools/metronome.py` already implements liveness monitoring, GUPP enforcement, and watchdog chain respawn — the cron script orchestrates these.
- **Dashboard integration**: Deferred to a follow-up show. For now, log to `logs/metronome/` with timestamped entries.
- **Persistent vs stateless**: Stateless per tick. Each cron invocation runs the tick, gathers status, and exits. The lock file prevents overlapping ticks.
