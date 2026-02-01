# Swarm Prompt: System Health Dashboard

## Show Concept
Create a new React page displaying real-time DCI swarm operational health. The System Health Dashboard is a single-scroll page at /system-health showing status banner, LLM usage, swarm stats, and work log feed.

## Musical Design
Data orchestration: four API endpoints polled on a 30-second interval, each feeding a distinct visual section. The rhythm is poll-render-refresh. Loading skeletons provide visual continuity between data fetches.

- GET /api/v1/system/health -> Status Banner (ok/warning/error)
- GET /api/v1/system/llm-usage -> LLM Provider Panel
- GET /api/v1/system/agents -> Swarm Stats Grid
- GET /api/v1/system/work-log -> Work Log Feed (last 20 entries)

## Visual Design
Field Commander Brutalism aesthetic:
- JetBrains Mono (--font-mono) for all numbers, data values, timestamps
- IBM Plex Sans (--font-body) for labels, headings, descriptions
- Dark background: var(--color-field-dark) or var(--bg-primary)
- No rounded corners — sharp edges only
- Border: 1px solid var(--border-color)
- Status colors: green (#00C853) ok, amber (#FFD600) warning, red (#FF1744) error
- Use existing CSS variables from App.css

## Guard Design
Error handling and resilience:
- Each section handles its own fetch errors independently (inline error message, not full page crash)
- Loading skeleton states while fetching
- Cleanup all setInterval on component unmount
- Manual refresh button in status banner
- Graceful degradation if an endpoint is unavailable

## General Effect
The page gives operators immediate situational awareness of the swarm. At a glance: is the system healthy, are agents working, what happened recently. No clicks required to see critical info.

## Constraints
- Use v1.ts API client exclusively (no legacy api.ts)
- No new npm dependencies
- No WebSocket connections — polling only
- No backend modifications
- Responsive at 1024px+ width
- All React hooks called before any early returns

## Deliverables

### CREATE: frontend/src/pages/SystemHealthDashboard.tsx
Single page with four stacked sections:
1. Status Banner — large color-coded health indicator with status text, uptime, timestamp, refresh button
2. LLM Provider Panel — provider name, model, request count, avg latency, errors (grid layout)
3. Swarm Stats Grid — stat cards with large numbers: active corps, total agents, active sessions
4. Work Log Feed — scrollable list of recent entries with timestamp, corps name, action, details

### MODIFY: frontend/src/App.tsx
- Import SystemHealthDashboard
- Add route: <Route path="/system-health" element={<SystemHealthDashboard />} />

### MODIFY: frontend/src/components/SideNav.tsx
- Add "System Health" nav item linking to /system-health

### MODIFY: frontend/src/services/v1.ts
- Add typed functions if not present: getSystemHealth(), getLLMUsage(), getAgentsOverview(), getWorkLog()