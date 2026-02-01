# System Health Dashboard

## Overview

Build a system health monitoring dashboard showing swarm-wide metrics, agent status, metronome heartbeat status, and operational alerts.

## Acceptance Criteria

1. **Swarm overview**: Total active corps, running agents, pending reps, and system uptime.
2. **Metronome status**: Last heartbeat timestamp, ten-hut/resume-hut counts, stalled corps alerts.
3. **Per-corps health cards**: Agent liveness, rep throughput, failure rates, and RED FLAG indicators.
4. **Alert feed**: Real-time display of system alerts and metronome RED FLAG events.
5. **Refresh**: Auto-refresh on interval or manual refresh button.

## Constraints

- Use existing /api/system-health endpoint (or create v1 equivalent)
- Lightweight polling (not WebSocket) for health data
- Dashboard should load fast even with many corps

## Deliverables

- SystemHealthDashboard.tsx page
- CorpsHealthCard.tsx component
- MetronomeStatus.tsx component
- AlertFeed.tsx component
