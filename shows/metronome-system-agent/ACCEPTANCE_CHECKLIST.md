# Acceptance Checklist

- `scripts/metronome/tick.sh` exists, executable, and uses flock lock file.
- Ten-hut (attention) sent to each active corps ED per tick.
- Resume-hut only sent when corps work is stalled (>5 min inactivity).
- Performers are never directly messaged.
- Tick report written to `logs/metronome/{TIMESTAMP}.log`.
- Red flag logged after 3 consecutive failed ticks per corps.
- 30-second per-corps timeout and 4-minute overall tick limit enforced.
- Backend unavailability logs error and exits gracefully.
