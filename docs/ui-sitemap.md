# DCI Swarm — UI Site Map

Generated: 2026-02-14 via Playwright accessibility snapshots against `http://localhost:5173`.

---

## Global Observations

| Property | Value |
|----------|-------|
| **Page title** | `frontend` (all routes — no per-page `<title>`) |
| **Active theme** | Dark (toggle button reads "☀ Light", meaning light is the alternative) |
| **Errors on load** | None. "Loading Command Center..." shown briefly on `/` before data arrives |
| **WebSocket warning** | `SwarmHealthPage.tsx` and `useWebSocket.ts` log reconnect warnings (non-blocking) |
| **Formatter warning** | `[formatters] Unknown status: ok` on `/system` page (cosmetic) |

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ TOP NAV (banner)                                                │
│  Logo ─ Corps ─ Shows ─ Design Room ─ DCI Office ─             │
│  Performance Stats ─ System ─ Messages ─ Command Center         │
│                                    [Theme picker] [☀ Light]     │
├──────────┬──────────────────────────────────┬───────────────────┤
│ SIDE NAV │         MAIN CONTENT             │ RIGHT SIDEBAR     │
│          │                                  │ (complementary)   │
│ DSI Logo │                                  │                   │
│ ──────── │                                  │ System Health     │
│ LIFECYCLE│                                  │ Corps count       │
│ 1 Design │                                  │ Recent Rounds     │
│ 2 Shows  │                                  │ Latest Scores     │
│ 3 Season │                                  │                   │
│ 4 Tour   │                                  │                   │
│ 5 Finals │                                  │                   │
│ 6 Health │                                  │                   │
│ ──────── │                                  │                   │
│ ACTIONS  │                                  │                   │
│ New Show │                                  │                   │
│ New Seasn│                                  │                   │
│ New Corps│                                  │                   │
│ Cmd Centr│                                  │                   │
│ ──────── │                                  │                   │
│ CORPS    │                                  │                   │
│ [picker] │                                  │                   │
└──────────┴──────────────────────────────────┴───────────────────┘
```

**Top nav** — 8 links + theme selector dropdown (17 corps color schemes) + dark/light toggle.

**Side nav** — Numbered lifecycle steps (1–6), quick-action buttons, corps combobox picker.

**Right sidebar** — Persistent `<aside>` with System Health, Corps count, Recent Rounds, Latest Scores. Visible on most routes but data loads asynchronously.

---

## Route Map

### Primary Routes (Side Nav — Lifecycle)

| # | Route | Heading | Content Type | Description |
|---|-------|---------|-------------|-------------|
| 1 | `/design` | "Design Room" | **Table** (Thread, Summary, Status, Spec) + New Thread input | Lists all design threads (shows in design). 29 rows with status badges. |
| 2 | `/shows` | "SHOW LIBRARY" | **Cards** (show cards with status, spec indicator, action buttons) + stats bar + search/filter | Shows with status counts (Active/Published/Approved/In Review/Draft/Completed). Cards have Delete, Add to Season, Publish actions. |
| 3 | `/seasons` | "Season Workshop" | **Table** (Season, Status, Corps) + New Season button | Lists 12 seasons, all "Planning" status. Clickable rows navigate to detail. |
| 4 | `/tour` | "On Tour" | **Cards + Tables** (tour cards with schedule tables) + competition sections | 5 active tours. Each has round schedule table, Advance Round button, auto-advance toggle. Sections: Tours in Progress, Active Competitions, Completed. |
| 5 | `/finals` | "Finals" | **Cards** (season cards with status badges) | 12 season cards showing Finals status (Completed/Touring/Finals/Planning). Stats: Total Seasons, Awaiting Review. |
| 6 | `/swarm-health` | "Swarm Health" | **Dashboard** (stat cards + tabs + leaderboard) | Tabs: Overview, Providers, Agents, Resources, Trophies. Time range selector (1h/6h/24h/7d). Corps Leaderboard ranked list. Status/Active Corps/Agents/Failure Rate metrics. |

### Primary Routes (Top Nav Only)

| Route | Heading | Content Type | Description |
|-------|---------|-------------|-------------|
| `/` | "Command Center" | **Dashboard** (stat cards + corps grid + provider table + activity feed) | Quick Start guide (7 steps), system metrics (Corps/Agents/Reps/Failures), Corps on the Field grid, Agent Usage provider table, Recent Activity timeline. |
| `/corps` | "Corps" | **Cards** (corps cards with name, staff count, status, philosophy) | 14 corps + 1 system corps (collapsible). Each card clickable to detail. Create Corps button. |
| `/scoreboards` | "Scoreboards" | **Table** (Rank, Corps, Status, Completion, Efficiency, Sessions, Reps, Score) | Sortable scoreboard with time range filter (7/14/30 days). Tabs: Corps / Agents. |
| `/system` | "System Health" | **Dashboard** (vitals cards + corps health table) | System Vitals (Status, Corps, Agents, Failures, Sessions, Reps), Corps Health table (per-corps agent/session/rep/failure counts). Auto-refresh 15s. |
| `/messages/inbox` | "Message Inbox" | **Split pane** (thread list + detail) | Thread list with status filter (Pending/Completed/All). Sub-nav: Archive, Admin. |

### Sub-Routes (Messages)

| Route | Heading | Content Type | Description |
|-------|---------|-------------|-------------|
| `/messages/inbox` | "Message Inbox" | **Split pane** | Thread list + thread detail viewer. Status filter dropdown. |
| `/messages/archive` | "Message Archive" | **Split pane** + search | Keyword search + role filter (ED/PC/Caption Head/Tech/Music Writer). |
| `/messages/admin` | "Message Admin" | **List** + bulk actions | Bulk archive completed threads. Select-all checkbox, Archive Selected button. |

### Detail Routes (Parameterized)

| Route | Heading | Content Type | Description |
|-------|---------|-------------|-------------|
| `/corps/:id` | Corps name (e.g. "Cavaliers") | **Tabbed detail** (Overview, Roster, Runs, Shows, History, Strategy) | Overview: Corps Info table, Lifecycle stepper, Operational Commands (Resume/Attention/Metronome/Rehearsal modes), Achievements, Feedback textarea, Philosophy. Back button. |
| `/design/:slug` | Thread title (e.g. "Finals System") | **Split pane** (chat + artifacts) | Left: chat messages + send input. Right: tabbed artifacts (Brief, Prompt, Versions) with show spec markdown. Approve Show button. Status badge. Back button. |
| `/seasons/:id` | Season name | **Detail page** | Season detail with back button. (Note: some seasons return "Season not found" if data incomplete.) |

---

## Navigation Cross-Reference

Some top nav links overlap with side nav but use different labels:

| Top Nav Label | Top Nav Route | Side Nav Label | Side Nav Route |
|---------------|---------------|----------------|----------------|
| Design Room | `/design` | DSN Design Room | `/design` |
| Shows | `/shows` | LIB Show Library | `/shows` |
| DCI Office | `/seasons` | SZN Season Workshop | `/seasons` |
| Command Center | `/` | CMD Command Center (button) | `/` |
| Corps | `/corps` | — (combobox only) | — |
| Performance Stats | `/scoreboards` | — | — |
| System | `/system` | SYS Swarm Health | `/swarm-health` |
| Messages | `/messages/inbox` | — | — |

Note: `/system` (top nav) and `/swarm-health` (side nav) are **different pages** — System Health is a simpler vitals + table view, while Swarm Health is a full tabbed dashboard with leaderboard and trophies.

---

## Quick Actions (Side Nav Buttons)

| Button | Action |
|--------|--------|
| NEW — New Show | Opens new show creation flow |
| SZN — New Season | Opens new season creation flow |
| CRP — New Corps | Opens corps creation flow |
| CMD — Command Center | Navigates to `/` |

---

## Complete Route List

```
/                           Command Center (dashboard)
/corps                      Corps list (cards)
/corps/:id                  Corps detail (tabbed: Overview/Roster/Runs/Shows/History/Strategy)
/design                     Design Room thread list (table)
/design/:slug               Design Room thread detail (split: chat + artifacts)
/shows                      Show Library (cards + search/filter)
/seasons                    Season Workshop (table)
/seasons/:id                Season detail
/tour                       On Tour dashboard (tour cards + schedule tables)
/finals                     Finals overview (season cards)
/swarm-health               Swarm Health dashboard (tabs: Overview/Providers/Agents/Resources/Trophies)
/system                     System Health (vitals + corps health table)
/scoreboards                Performance Stats scoreboard (sortable table)
/messages/inbox             Message Inbox (split pane)
/messages/archive           Message Archive (search + split pane)
/messages/admin             Message Admin (bulk actions)
```

**Total: 16 route patterns (10 static + 3 parameterized + 3 message sub-routes)**
