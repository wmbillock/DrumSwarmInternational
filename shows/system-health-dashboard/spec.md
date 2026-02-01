# System Health Dashboard — Brief

## Goal
Build a new frontend page at /system-health that displays real-time operational health of the DCI swarm system.

## Key Sections
1. **Status Banner** — Overall system health (ok/warning/error) from GET /api/v1/system/health, color-coded.
2. **LLM Provider Panel** — Provider name, model, request counts, latency, error rate from GET /api/v1/system/llm-usage.
3. **Swarm Stats** — Active corps count, total agents, active sessions from GET /api/v1/system/agents.
4. **Work Log Feed** — Recent work log entries (last 20) from GET /api/v1/system/work-log, reverse chronological.
5. **Auto-Refresh** — Poll every 30 seconds with a manual refresh button.

## Design Constraints
- Field Commander Brutalism: JetBrains Mono for data, IBM Plex Sans for labels, stage color palette (--color-stage-*, --color-field-*).
- Dark background, high-contrast status indicators.
- Single-page layout, no tabs — all sections visible on scroll.
- Use v1.ts API client exclusively.
- Page component: SystemHealthDashboard.tsx in frontend/src/pages/.
- Add route to App.tsx and SideNav.tsx.

## Acceptance Criteria
- Page loads and displays health status within 2 seconds.
- Status banner changes color based on ok/warning/error.
- LLM usage stats render correctly.
- Work log entries display with timestamps.
- Auto-refresh works on 30s interval.
- Responsive layout (works at 1024px+ width).