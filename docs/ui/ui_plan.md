# DCI Swarm UI Plan

## Inventory Summary

### Frontend Stack
- **Framework:** React 19 + TypeScript, Vite 7, React Router DOM 7
- **State:** React Context (CorpsTheme, Mode, Show) + local component state
- **Styling:** Vanilla CSS with custom properties, 15+ DCI corps color themes
- **API client:** `frontend/src/services/api.ts` — 50+ fetch wrappers against `/api/*`
- **Layout:** Top NavBar + left sidebar + main content area (implemented in MVP)
- **Existing routes:** `/` (CommandCenter), `/shows` (SwarmOverview), `/corps` (CorpsList), `/corps/:id/:tab` (CorpsDeepDive with 12 tabs incl. history), `/runs` (RunsList), `/runs/:runId` (RunDetail), `/admin`, `/templates`, `/performers`, `/seance`

### Backend Surfaces
| Surface | Count | Notes |
|---------|-------|-------|
| REST endpoints | ~70 | FastAPI, all under `/api/` |
| WebSocket | 1 | `/ws/{corps_id}` |
| DB models | 19 | SQLite via SQLAlchemy |
| CLI commands | 32 | Mix of filesystem-only and client-based |
| Filesystem artifact trees | 4 | `seasons/`, `shows/`, `corps/`, `talent_pool/` |

### Sources of Truth

| Domain Concept | Primary Source | Secondary/Export |
|----------------|---------------|-----------------|
| **Seasons** | Filesystem (`seasons/<id>/season.yaml`) | — |
| **Standings** | Filesystem (`seasons/<id>/standings.yaml`) | — |
| **Shows (design)** | Filesystem (`shows/<slug>/status.yaml`, `design_notes.md`) | DB `Show` table (for active runs) |
| **Shows (runtime)** | DB `Show` table | — |
| **Corps (identity)** | Filesystem (`corps/<id>/corps.yaml`, `roster.yaml`) | DB `Corps` table (for runtime state) |
| **Corps (runtime)** | DB `Corps` table | — |
| **Runs / Rehearsals** | DB `Rep`, `Segment`, `AgentSession` tables | Filesystem `performances/<cid>/<run_id>/manifest.yaml` |
| **Segments / Reps** | DB `Segment`, `Rep` tables | — |
| **Judge Scores / Critique** | DB `Score`, `Penalty` tables | Filesystem `scores.yaml` (per-corps export) |
| **Talent Pool / Evolution** | Filesystem (`talent_pool/ledger.yaml`, `agents/*.yaml`) | DB `Performer` table |
| **Work Logs / Audit** | DB `WorkLog` table | — |
| **Agent Memory** | DB `AgentMemory`, `TaskMemory` tables | — |
| **Messages** | DB `Message` table | — |

---

## Information Architecture

### Left-Nav Layout

Transition from current top-nav to a collapsible left sidebar. The top NavBar collapses to a thin bar with logo, health badge, and theme picker.

```
┌─────────────────────────────────────────┐
│ DCI Swarm  [health badge]  [theme] [◑]  │  ← collapsed top bar
├────────┬────────────────────────────────┤
│ ◉ CMD  │                                │
│        │   (page content)               │
│ 🎨 DSN │                                │
│        │                                │
│ 📅 SEA │                                │
│        │                                │
│ 🎪 SHW │                                │
│        │                                │
│ 🎺 CRP │                                │
│        │                                │
│ ⚖ JDG  │                                │
│        │                                │
│ 🏃 RUN │                                │
│        │                                │
│ 🧬 EVO │                                │
│        │                                │
│ ⚙ SYS  │                                │
└────────┴────────────────────────────────┘
```

---

### 1. Command Center (`/`)

**User questions:**
- What is the overall state of the system right now?
- Which corps are active, what modes are they in?
- Are there failed reps, stale work, or problems needing attention?
- What happened recently?

**Widgets (MVP):**

| Widget | Data Fields | Backend Adapter |
|--------|-------------|-----------------|
| System Vitals | `active_corps`, `total_agents`, `active_agents`, `failed_agents`, `total_reps`, `completed_reps`, `failed_reps`, `stale_reps`, `failure_rate` | Existing `GET /api/system-health` |
| Corps Cards | per-corps: `id`, `name`, `status`, `mode`, `agents_active`, `agents_total`, `reps_completed`, `reps_total`, `failures` | Existing `GET /api/system-health` → `corps_summaries[]` |
| Active Shows | `id`, `title`, `status`, `corps_name`, `reps_total`, `reps_completed`, `final_score` | Existing `GET /api/shows-overview` |
| Recent Activity Feed | `role`, `nickname`, `event_type`, `phase`, `details`, `timestamp` | Existing `GET /api/work-log?limit=30` |
| Alerts / Problems | `title`, `severity`, `status`, `corps_id`, `segment_id` | **New:** `GET /api/problems?status=open` |

**Adapter needed:** One new endpoint for open problems (or filter existing work-log by event_type).

---

### 2. Design Room (`/design-room`)

**User questions:**
- What shows are in design? What's their status?
- What are the design notes so far?
- Can I approve a show for the field?

**Widgets (MVP):**

| Widget | Data Fields | Backend Adapter |
|--------|-------------|-----------------|
| Show Pipeline | `slug`, `status` (draft/needs_review/approved/rejected), `design_notes` (preview) | **New:** `GET /api/shows-workspace` — reads filesystem `shows/` |
| Design Notes Viewer | full `design_notes.md` content | **New:** `GET /api/shows-workspace/{slug}/notes` |
| Show Prompt Viewer | full `show_prompt.md` content | **New:** `GET /api/shows-workspace/{slug}/prompt` |
| Approve / Reject | action buttons | **New:** `POST /api/shows-workspace/{slug}/approve` |

**Adapter needed:** Thin API layer that reads from `shows/` filesystem directory. 4 new endpoints.

---

### 3. Seasons (`/seasons`, `/seasons/:seasonId`)

**User questions:**
- What seasons exist? Which is current?
- What are the standings for a season?
- Which corps competed, what were their scores per caption?

**Widgets (MVP):**

| Widget | Data Fields | Backend Adapter |
|--------|-------------|-----------------|
| Season List | `season_id`, `metadata`, registered corps count | **New:** `GET /api/seasons-workspace` — reads `seasons/` dirs |
| Standings Table | `corps_id`, `rank`, `final_score`, `raw_score`, `caption_scores{brass,percussion,guard,visual,general_effect}` | **New:** `GET /api/seasons-workspace/{id}/standings` |
| Season Corps | list of registered `corps_id` in `performances/` | Included in season detail |

**Adapter needed:** 2 new filesystem-reading endpoints.

---

### 4. Shows (`/shows`, `/shows/:showId`)

**User questions:**
- What shows exist (DB active shows vs. filesystem design artifacts)?
- What's the segment tree for an active show?
- What's the completion progress?

**Widgets (MVP):**

| Widget | Data Fields | Backend Adapter |
|--------|-------------|-----------------|
| Active Shows List | `id`, `title`, `status`, `corps_name`, `reps_total`, `reps_completed` | Existing `GET /api/shows-overview` |
| Show Detail | `id`, `title`, `status`, `description`, `corps_id`, `segment_root_id` | Existing `GET /api/shows/{id}` |
| Segment Tree | recursive `SegmentNode{id, type, title, status, caption, reps[], children[]}` | Existing `GET /api/segments/{id}/tree` |

**Adapter needed:** None — existing endpoints cover this.

---

### 5. Corps (`/corps`, `/corps/:corpsId`, `/corps/:corpsId/:tab`)

**User questions:**
- What corps exist, what are their states?
- Who is on the roster?
- What's the corps' competition history?
- What mode is this corps in?

**Widgets (MVP):**

| Widget | Data Fields | Backend Adapter |
|--------|-------------|-----------------|
| Corps List | `corps_id`, `display_name`, `state`, `philosophy` (filesystem) + `mode`, `rehearsal_mode` (DB) | **New:** `GET /api/corps-workspace` — merges filesystem + DB |
| Corps Detail Header | `corps_id`, `display_name`, `state`, `philosophy`, `mode`, `rehearsal_mode` | Existing `GET /api/corps/{id}` + **new** filesystem read |
| Roster Table | `agent_id`, `role`, `trust_score`, `availability` | Existing `GET /api/corps/{id}/roster` (DB sessions) + filesystem `roster.yaml` |
| Competition History | `season_id`, `placement`, `final_score`, `notes` | **New:** `GET /api/corps-workspace/{id}/history` — reads `corps.yaml` history[] |
| Scoresheet | full `Scoresheet` type (caption_scores, composite, penalties, execution, roster, activity) | Existing `GET /api/corps/{id}/scoresheet` |
| Command Room (chat) | existing chat interface | Existing chat/WebSocket endpoints |

**Adapter needed:** 2 new endpoints (corps list from filesystem, corps history from filesystem).

---

### 6. Judging & Critique (`/judging`, `/judging/:corpsId`)

**User questions:**
- What scores has a corps received, per caption?
- What penalties have been issued?
- What feedback/critique came back from judges?
- Does anything need rework or escalation?

**Widgets (MVP):**

| Widget | Data Fields | Backend Adapter |
|--------|-------------|-----------------|
| Scoresheet View | reuse `Scoresheet` type — `caption_scores`, `composite`, `penalties` | Existing `GET /api/corps/{id}/scoresheet` |
| Rep Critique | `rep_id`, `overall_assessment`, `needs_rework`, `feedbacks[]` | Existing `GET /api/reps/{id}/critique` |
| Penalty Log | `type`, `amount`, `reason`, `issued_by`, `created_at` | **New:** `GET /api/corps/{id}/penalties` |
| Standings Comparison | multi-corps caption scores side-by-side | **New:** `GET /api/seasons-workspace/{id}/standings` (reuse from Seasons) |

**Adapter needed:** 1 new endpoint (penalties list — simple DB query).

---

### 7. Runs & Rehearsals (`/runs`, `/runs/:runId`)

**User questions:**
- What runs have been executed?
- What was the outcome of a specific run?
- Which reps succeeded/failed in a run?
- What did agents actually do during a run?

**Widgets (MVP):**

| Widget | Data Fields | Backend Adapter |
|--------|-------------|-----------------|
| Runs List | `run_id`, `show_slug`, `corps_id`, `season_id`, `started_at`, `completed_at`, `status` | **New:** `GET /api/runs` — scans `seasons/*/performances/*/` for `manifest.yaml` files |
| Run Detail | full `manifest.yaml` fields + `output.txt` content | **New:** `GET /api/runs/{runId}` |
| Rep Progress Table | `rep_id`, `status`, `assigned_to`, `segment_title`, `result` (summary), `error` | Existing `GET /api/segments/{id}/tree` (reps embedded) |
| Agent Activity Log | `session_id`, `tool_calls[]`, `messages[]`, `final_response` | Existing `GET /api/sessions/{id}/activity` |
| Work Log | `role`, `event_type`, `details`, `timestamp` | Existing `GET /api/corps/{id}/work-log` |

**Adapter needed:** 2 new endpoints (runs list, run detail — both read from filesystem manifests).

---

### 8. Evolution & Talent Pool (`/evolution`, `/evolution/:agentId`)

**User questions:**
- Who are the agents in the pool?
- What are their trust scores and track records?
- How have trust scores changed over time?
- Are there pending self-improvement proposals?

**Widgets (MVP):**

| Widget | Data Fields | Backend Adapter |
|--------|-------------|-----------------|
| Agent Roster Table | `agent_id`, `display_name`, `primary_instrument`, `availability`, `trust_score`, `total_sessions`, `successful_sessions`, `failed_sessions`, `experience_seasons` | Existing `GET /api/performers` (DB) + **new** `GET /api/talent-pool` (filesystem) |
| Agent Detail | full agent YAML fields + `specialties[]`, `seen_sessions[]` | **New:** `GET /api/talent-pool/{agentId}` |
| Capability Ledger | `entry_type`, `score`, `trust_before`, `trust_after`, `details`, `created_at` | Existing `GET /api/performers/{id}/ledger` |
| Self-Improvement Queue | `definition_id`, `changes`, `reason`, `status` | Existing `GET /api/self-improvement/pending` |

**Adapter needed:** 2 new endpoints (talent-pool list, talent-pool agent detail — read from filesystem YAML).

---

### 9. System (`/system`)

**User questions:**
- Is the system healthy?
- What's the database state?
- What environment checks pass/fail?

**Widgets (MVP):**

| Widget | Data Fields | Backend Adapter |
|--------|-------------|-----------------|
| Health Dashboard | full `SystemHealth` type | Existing `GET /api/system-health` |
| Doctor Report | checks: `project_root`, `backend`, `cli`, `models`, `services`, `tests`, `frontend`, `venv`, `database`, `alembic` — each pass/fail | **New:** `GET /api/doctor` — runs `dci doctor --json` equivalent |
| Corps Commands Reference | command definitions | Existing `GET /api/corps-commands` |

**Adapter needed:** 1 new endpoint (doctor — runs filesystem checks, returns JSON).

---

## Data Contracts (View Models)

### New TypeScript Types

```typescript
// -- Filesystem-sourced types --

interface SeasonWorkspace {
  season_id: string;
  metadata: Record<string, unknown>;
  registered_corps: string[];
}

interface SeasonStandings {
  season_id: string;
  generated_at: string;
  results: StandingsResult[];
}

interface StandingsResult {
  corps_id: string;
  rank: number;
  final_score: number;
  raw_score: number;
  caption_scores: Record<string, number>; // brass, percussion, guard, visual, general_effect
}

interface ShowWorkspace {
  slug: string;
  status: "draft" | "needs_review" | "approved" | "rejected";
  has_design_notes: boolean;
  has_prompt: boolean;
}

interface CorpsWorkspace {
  corps_id: string;
  display_name: string;
  philosophy: string;
  state: string; // commissioned, active, contending, stagnant, rebuilt, retired
  history: CorpsPlacement[];
  roster_size: number;
}

interface CorpsPlacement {
  season_id: string;
  placement: number;
  final_score: number;
  notes: string;
}

interface RunManifest {
  run_id: string;
  show_slug: string;
  corps_id: string;
  season_id: string;
  started_at: string;
  completed_at?: string;
  status: "running" | "completed" | "failed";
  config: { max_iterations: number; timeout: number };
}

interface TalentPoolAgent {
  agent_id: string;
  display_name: string;
  primary_instrument: string;
  availability: string;
  trust_score: number;
  total_sessions: number;
  successful_sessions: number;
  failed_sessions: number;
  experience_seasons: number;
  specialties: string[];
  seen_sessions: string[];
}

interface DoctorReport {
  checks: DoctorCheck[];
  all_passed: boolean;
}

interface DoctorCheck {
  name: string;
  passed: boolean;
  detail: string;
}

interface PenaltyEntry {
  id: string;
  corps_id: string;
  type: "timing" | "budget" | "rule";
  amount: number;
  reason: string;
  issued_by?: string;
  rep_id?: string;
  segment_id?: string;
  created_at: string;
}
```

---

## Proposed Backend Adapter Approach

### Principle: Thin filesystem readers, no new business logic

All new endpoints read YAML/markdown from disk and return JSON. They do NOT create new persistence layers or duplicate existing services. They call the same `*_persistence.py` modules the CLI uses.

### New Endpoint Summary

| Endpoint | Method | Source | Implementation |
|----------|--------|--------|----------------|
| `GET /api/seasons-workspace` | GET | `seasons/` dirs | Read `season.yaml` from each dir, list registered corps |
| `GET /api/seasons-workspace/{id}/standings` | GET | `seasons/{id}/standings.yaml` | YAML load → JSON |
| `GET /api/shows-workspace` | GET | `shows/` dirs | Read `status.yaml` from each dir |
| `GET /api/shows-workspace/{slug}/notes` | GET | `shows/{slug}/design_notes.md` | Read markdown → string |
| `GET /api/shows-workspace/{slug}/prompt` | GET | `shows/{slug}/show_prompt.md` | Read markdown → string |
| `POST /api/shows-workspace/{slug}/approve` | POST | `shows/{slug}/status.yaml` | Call `show_persistence.update_status()` |
| `GET /api/corps-workspace` | GET | `corps/` dirs | Read `corps.yaml` from each dir |
| `GET /api/corps-workspace/{id}/history` | GET | `corps/{id}/corps.yaml` | Extract `history[]` |
| `GET /api/runs` | GET | `seasons/*/performances/*/` | Scan for `manifest.yaml` files |
| `GET /api/runs/{runId}` | GET | manifest path | Read `manifest.yaml` + `output.txt` |
| `GET /api/talent-pool` | GET | `talent_pool/ledger.yaml` + agents | YAML load → JSON |
| `GET /api/talent-pool/{agentId}` | GET | `talent_pool/agents/{id}.yaml` | YAML load → JSON |
| `GET /api/corps/{id}/penalties` | GET | DB `Penalty` table | Simple SQLAlchemy query |
| `GET /api/doctor` | GET | filesystem checks | Run doctor checks, return JSON |

**14 new endpoints.** All are read-only except the show approve action.

### File Organization

```
backend/api/
  app.py             ← add routes to existing file (or split into router modules)

backend/api/workspace_routes.py   ← NEW: all filesystem-reading endpoints
backend/api/workspace_views.py    ← NEW: view-model serializers (YAML → dict)
```

### Project Root Resolution

All workspace endpoints use the same `DCI_PROJECT_ROOT` env var / `_find_project_root()` pattern established in CLI commands. A shared helper:

```python
# backend/api/workspace_routes.py
from backend.cli.commands.doctor import _find_project_root

def _get_root() -> Path:
    import os
    override = os.environ.get("DCI_PROJECT_ROOT", "")
    return Path(override).resolve() if override else Path(_find_project_root())
```

---

## MVP Slice

### Scope: 3 views

1. **Command Center dashboard** (read-only) — `/`
2. **Runs & Rehearsals list + detail** — `/runs`, `/runs/:runId`
3. **Corps detail with history tab** — `/corps/:corpsId` (enhance existing)

### Why this slice

- Command Center uses only existing endpoints (zero backend work, pure frontend).
- Runs list is the most operationally useful new view — "what happened?" is the first question after `dci demo tour --yes`.
- Corps history tab bridges filesystem artifacts into the existing CorpsDeepDive, proving the workspace adapter pattern.

### Pages / Routes / Components

```
Route                     Page Component         New?   Backend Deps
─────────────────────────────────────────────────────────────────────
/                         CommandCenter           YES    existing endpoints only
/runs                     RunsList                YES    NEW GET /api/runs
/runs/:runId              RunDetail               YES    NEW GET /api/runs/{runId}
/corps/:corpsId           CorpsDeepDive           NO     existing + NEW history endpoint
/corps/:corpsId/history   CorpsDeepDive (tab)     YES*   NEW GET /api/corps-workspace/{id}/history
```

*`history` is a new tab within the existing CorpsDeepDive tabbed interface.

### Component Breakdown

**CommandCenter** (new page, replaces SwarmOverview)
- `<SystemVitals />` — cards for active_corps, total_agents, failure_rate, stale_reps
- `<CorpsStatusGrid />` — cards per corps (name, mode badge, agent count, rep progress bar)
- `<ActiveShowsList />` — table of active shows with progress
- `<RecentActivityFeed />` — scrollable work-log entries

**RunsList** (new page)
- `<RunsTable />` — sortable table: run_id, show, corps, season, status, started_at, completed_at

**RunDetail** (new page)
- `<RunManifestCard />` — run metadata (config, inputs, timestamps)
- `<RunOutput />` — formatted output.txt content
- `<RunSegmentTree />` — reuse existing segment tree component if segment_root available

**CorpsHistory** (new tab component within CorpsDeepDive)
- `<PlacementTimeline />` — table/timeline of history[] entries: season, placement, score, show

### New Backend Endpoints (MVP only)

| # | Endpoint | Returns |
|---|----------|---------|
| 1 | `GET /api/runs` | `RunManifest[]` |
| 2 | `GET /api/runs/{runId}` | `RunManifest & { output: string }` |
| 3 | `GET /api/corps-workspace` | `CorpsWorkspace[]` |
| 4 | `GET /api/corps-workspace/{id}/history` | `CorpsPlacement[]` |

**4 new endpoints for MVP.** (All implemented in `backend/api/workspace_routes.py`.)

---

## Test Plan

### Backend Tests (pytest)

**File: `backend/tests/test_workspace_routes.py`** (new)

| Test | What it verifies |
|------|-----------------|
| `test_get_runs_empty` | Returns `[]` when no runs exist |
| `test_get_runs_with_manifests` | Scans season performance dirs, returns `RunManifest[]` |
| `test_get_runs_sorted_by_date` | Most recent run first |
| `test_get_run_detail` | Returns manifest + output text |
| `test_get_run_detail_not_found` | Returns 404 |
| `test_get_corps_history` | Returns `CorpsPlacement[]` from `corps.yaml` history |
| `test_get_corps_history_no_history` | Returns `[]` for corps with no history |
| `test_get_corps_history_not_found` | Returns 404 for missing corps |

Tests create fixture dirs in `tmp_path`, set `DCI_PROJECT_ROOT`, and call endpoints via FastAPI `TestClient`.

### Frontend Tests (Vitest or manual)

For MVP, manual verification via the demo tour:
```bash
DCI_PROJECT_ROOT=. dci demo tour --seed 1 --seasons 2 --corps-count 3 --yes
# Start backend with DCI_PROJECT_ROOT=.
# Navigate to /, /runs, /corps/:id/history
```

Post-MVP: add Vitest component tests for data fetching and rendering.

---

## Implementation Checklist (Prompt 2)

### Backend (4 endpoints)

- [x] Create `backend/api/workspace_routes.py` with `_get_root()` helper
- [x] Implement `GET /api/runs` — scan `seasons/*/performances/*/*/manifest.yaml`
- [x] Implement `GET /api/runs/{runId}` — find manifest by run_id, read manifest + output
- [x] Implement `GET /api/corps-workspace` — list all corps from filesystem
- [x] Implement `GET /api/corps-workspace/{corpsId}/history` — read `corps/{id}/corps.yaml` → `history[]`
- [x] Register workspace routes in `backend/api/app.py`
- [x] Write `backend/tests/test_workspace_routes.py` (10 tests, all passing)

### Frontend — Layout

- [x] Add left-nav sidebar component (`SideNav.tsx`) with section links
- [x] Update `AppLayout.tsx` to use sidebar + main content flex layout
- [x] Add sidebar CSS (active state, section abbreviations)
- [x] Update `router.tsx` with new routes (+ `/corps` list route)

### Frontend — Command Center

- [x] Create `CommandCenter.tsx` page (replaces SwarmOverview as `/`)
- [x] System vitals grid from `getSystemHealth()`
- [x] Corps status cards with rep progress bars
- [x] Active shows table and recent activity feed
- [x] 15s auto-refresh

### Frontend — Runs & Rehearsals

- [x] Add new types to `types/index.ts` (`RunManifest`, `RunDetail`)
- [x] Add API functions to `services/api.ts` (`getRuns`, `getRunDetail`)
- [x] Create `RunsList.tsx` page with runs table
- [x] Create `RunDetail.tsx` page with manifest card + output viewer

### Frontend — Corps List & History Tab

- [x] Create `CorpsList.tsx` page with card grid
- [x] Add API functions `getCorpsWorkspaces()`, `getCorpsHistory()` to `services/api.ts`
- [x] Create `TheHistory.tsx` tab component
- [x] Register `history` tab in CorpsDeepDive tab list
- [x] Add `CorpsWorkspace`, `CorpsPlacement` types to `types/index.ts`

### Verification

- [x] `python -m pytest backend/tests/test_workspace_routes.py -v` — 10/10 pass
- [x] `python -m pytest -q` — 928 passed
- [x] TypeScript compiles clean, Vite build succeeds
- [ ] Run demo tour, start server, manually verify all views render data
- [ ] Verify left-nav links navigate correctly
- [ ] Verify corps theme colors still work with new layout
