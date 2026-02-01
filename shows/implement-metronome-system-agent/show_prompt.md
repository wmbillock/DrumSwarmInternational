## Show Concept

Implement a Metronome system-level agent that runs on a cron schedule (every 5 minutes) to keep the DCI swarm continuously active. The metronome acts as the heartbeat of the swarm — on each tick it wakes corps agents, issues ten-hut and resume-hut commands as needed, and gathers swarm-wide status. This ensures no corps sits idle or gets stuck without intervention.

## Musical Design

Not applicable to this system-level feature. The metronome is an infrastructure agent, not a musical design element. However, the naming is thematically aligned — the metronome keeps time and keeps the ensemble in motion.

## Visual Design

Not applicable to this system-level feature. Future integration with the dashboard could display metronome tick history, last-ping timestamps, and corps responsiveness metrics.

## Guard Design

Not applicable to this system-level feature. No guard-related changes required.

## General Effect

The metronome ensures continuous forward progress across the entire swarm. Without it, corps agents may sit idle between user interactions. The metronome provides autonomous continuity — the swarm keeps rehearsing and performing even when the DCI executive director is not actively issuing commands.

## Constraints

- The metronome must run as a standalone script invocable by cron every 5 minutes
- The metronome must only directly wake instructional staff, admin, and logistics agents — never performers directly
- Woken staff/admin/logistics agents are responsible for waking their own performers as needed
- The metronome must issue ten-hut to every corps on each tick
- The metronome must issue resume-hut to any corps that appears stuck or has pending/failed work
- After issuing commands, the metronome must gather and report swarm-wide corps status
- The metronome must be idempotent — repeated ticks on an already-active swarm should cause no harm

## Deliverables

- A standalone metronome script (e.g. `scripts/metronome.sh` or `scripts/metronome.py`) that can be invoked by cron
- A crontab entry or documentation for setting up the 5-minute cron schedule
- Integration with existing corps discovery to enumerate all active corps
- ten-hut and resume-hut command dispatch to each corps
- Swarm status collection and summary output (similar to the METRONOME STATUS PING format already in use)
- The metronome should target instructional staff, admin, and logistics roles only — not performers

## Evaluation Rubric

- Does the metronome successfully wake all corps on each tick?
- Does it correctly limit direct wake-ups to staff/admin/logistics (not performers)?
- Does it issue ten-hut and conditionally issue resume-hut based on corps state?
- Does it produce a clear swarm-wide status summary after each tick?
- Is it safe to run repeatedly (idempotent)?
- Can it be installed as a cron job with minimal configuration?
