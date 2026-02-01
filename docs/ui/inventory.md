# Repository Inventory — UI + HTTP API Readiness

> Generated 2026-01-31. Sources: file-system grep, AST-level reads of every route/model/service file.

---

## 1. Frontend Structure Overview

### Stack

| Layer | Choice | Version | Evidence |
|-------|--------|---------|----------|
| Framework | React | 19.2.0 | `frontend/package.json` line 13 |
| Bundler | Vite | 7.2.4 | `frontend/package.json` line 29, `vite.config.ts` |
| Language | TypeScript | 5.9.3 | `frontend/package.json` line 28 |
| Routing | react-router-dom | 7.13.0 | `frontend/package.json` line 14, `frontend/src/router.tsx` |
| State | Local state + Context API | — | No Redux/Zustand/MobX; two Contexts (CorpsTheme, Mode) |
| CSS | Plain CSS + CSS custom properties | — | `App.css` (754 lines), `index.css`, `dci-colors.css` |
| Real-time | WebSocket + polling | — | `frontend/src/hooks/useWebSocket.ts`, `usePolling.ts` |

Vite config (`frontend/vite.config.ts`) is minimal — one plugin (`@vitejs/plugin-react`), no path aliases, no proxy.

### Entry Point

`frontend/src/main.tsx` wraps the app in:

```
StrictMode → CorpsThemeProvider → ModeProvider → RouterProvider
```

Imports both `index.css` and `App.css`.

### Layout

`frontend/src/layouts/AppLayout.tsx` renders:

```
NavBar (top) + SideNav (left sidebar) + <Outlet> (main content)
```

Dark/light theme toggle persisted to localStorage.

### Routes (20 total)

Source: `frontend/src/router.tsx`

| Path | Component | Purpose |
|------|-----------|---------|
| `/` | CommandCenter | System vitals, corps status, shows table, activity feed |
| `/shows` | SwarmOverview | Show CRUD, show cards, agent overview |
| `/corps` | CorpsList | Corps workspaces with state/philosophy/history |
| `/corps/:corpsId` | CorpsDeepDive | 12-tab deep dive (command, roster, sheets, field, reps, tape, banquet, stand, chart, books, season, history) |
| `/corps/:corpsId/:tab` | CorpsDeepDive | Direct tab link |
| `/runs` | RunsList | Run manifest table |
| `/runs/:runId` | RunDetail | Run manifest + output log |
| `/admin` | AdminChat | Admin/ED chat interface |
| `/templates` | Templates | Show template browser + instantiation |
| `/performers` | Performers | Performer roster + trust scores + ledger |
| `/seance` | Seance | Legacy memory-bank query (labeled "Legacy") |
| `/design` | DesignRoom | Show creation / design room entry |
| `/design/:showSlug` | DesignRoom | Two-pane design: chat + spec viewer |
| `/judging` | JudgingCritique | Judge tapes, critique viewer |
| `/judging/:corpsId` | JudgingCritique | Judge tapes for specific corps |
| `/evolution` | EvolutionTalentPool | Performer genomes, selection events, mutations |
| `/history` | CorpsHistory | Corps selection for history index |
| `/history/:corpsId` | CorpsHistory | History entries + "Start Seance" button |
| `/seance-session/:seanceId` | SeanceSession | ED retrospective chat with binder |

### Components (26 files)

Source: `frontend/src/components/`

**Navigation:** NavBar, SideNav
**Corps tabs:** TheRoster, TheSheets, TheField, TheReps, TheTape, TheBanquet, TheStand, TheChart, TheBooks, TheSeason, TheHistory, TheLot, TheMet
**Design Room:** DesignChat, SpecViewer
**Shared:** ModeIndicator, SystemHealth, CorpsThemePicker, ChatRoom, Critique, ShowSelector, ProjectState, CorpsDetail, Basics

### SideNav Entries

Source: `frontend/src/components/SideNav.tsx`

```
CMD  Command Center    /
SHW  Shows             /shows
CRP  Corps             /corps
RUN  Runs & Rehearsals /runs
EVO  Evolution & Talent /evolution
JDG  Judging & Critique /judging
TPL  Templates         /templates
DSN  Design Room       /design
HST  Corps History     /history
QRY  Seance (Legacy)   /seance
```

### API Client

Source: `frontend/src/services/api.ts` (290 lines)

Base URL: `VITE_API_URL || http://localhost:8000`

**79 exported functions** covering: shows (7), admin (1), corps (5), segments (3), work log (2), chat (4), messages (1), sessions (1), scoring (1), commands (2), metronome (1), templates (3), performers (5), health (1), mode (1), seasons (1), metrics (1), seance (1), evaluation (1), lifecycle (6), memory (4), banquet (1), runs (2), workspace (2), design room (6), judging (4), evolution (4), corps history + seance sessions (7).

All functions are typed with return types referencing interfaces from `types/index.ts`.

### TypeScript Types

Source: `frontend/src/types/index.ts` (465 lines)

**37 interfaces/types** organized into: Core (Show, Corps, SystemHealth, AgentSession, SegmentNode, RepInfo, WorkLogEntry), Communication (ChatMessage, WebSocketEvent), Scoring (CaptionScore, Scoresheet), Domain (Segment, Rep, Message, MetronomeResult, BanquetReport), Workspace (RunManifest, RunDetail, CorpsWorkspace, CorpsPlacement), Design Room (ShowSpec, DesignMessage, SpecVersion), Judging (JudgeTape, CritiqueFeedback, CritiqueDetail, CritiqueAction, CritiqueActionsResponse), Evolution (PerformerGenome, SelectionEvent, MutationLog, MutationSimulationResult), History/Seance (HistoryIndexEntry, HistoryIndex, ContextBinderItem, SeanceSession, SeanceMessageResponse, ArtifactPreview).

### Custom Hooks

- `useWebSocket` — WebSocket connection with auto-reconnect, heartbeat (25s), event buffer (200)
- `usePolling` — Generic polling with configurable interval

### Contexts

- `CorpsThemeContext` — 16 DCI corps color themes, applied via CSS custom properties
- `ModeContext` — Corps operational mode (design_room, show_mode, rehearsal_mode, judging, offseason_review) with suggested prompts and quick actions

---

## 2. Backend API Status

### Framework

**FastAPI** — confirmed at `backend/api/app.py` line 115:

```python
app = FastAPI(title="DCI Swarm", version="0.1.0", lifespan=lifespan)
```

### Database

- **ORM:** SQLAlchemy 2.0+ (declarative base, `Mapped[]` syntax)
- **Engine:** SQLite (`sqlite:///dci_swarm.db`)
- **Migrations:** Alembic (with `create_all()` fallback)
- **Session:** `get_db()` dependency injection per request

Source: `backend/database.py`

### Route Modules (6 files)

Routes registered in `backend/api/app.py` lines 118–135:

| Module | Prefix | Endpoints | Source |
|--------|--------|-----------|--------|
| `app.py` (main) | `/api/` | 63 endpoints + 1 WebSocket | `backend/api/app.py` |
| `workspace_routes.py` | `/api/` | 4 endpoints | `backend/api/workspace_routes.py` |
| `design_room_routes.py` | `/api/design/` | 6 endpoints | `backend/api/design_room_routes.py` |
| `judging_routes.py` | `/api/judging/` | 4 endpoints | `backend/api/judging_routes.py` |
| `evolution_routes.py` | `/api/evolution/` | 4 endpoints | `backend/api/evolution_routes.py` |
| `seance_routes.py` | `/api/` | 7 endpoints | `backend/api/seance_routes.py` |

**Total: ~88 REST endpoints + 1 WebSocket**

### All Endpoints by Resource

#### Shows (10)
```
POST   /api/shows                          Create show
GET    /api/shows                          List shows
GET    /api/shows/{show_id}                Get show
POST   /api/shows/{show_id}/activate       Activate show (spawns corps + agents)
POST   /api/shows/{show_id}/complete       Complete show
POST   /api/shows/{show_id}/tour           Toggle tour mode
DELETE /api/shows/{show_id}                Delete show
GET    /api/shows-overview                 Dashboard overview (with stats)
GET    /api/show-templates                 List templates
GET    /api/show-templates/{name}          Get template
POST   /api/show-templates/instantiate     Instantiate template
```

#### Corps (15)
```
GET    /api/admin-corps                    Get/create admin corps
GET    /api/corps/{corps_id}               Get corps
GET    /api/corps/{corps_id}/theme         Get theme
PUT    /api/corps/{corps_id}/theme         Update theme
GET    /api/corps/{corps_id}/progression   Rehearsal progression
POST   /api/corps/{corps_id}/rehearsal-mode  Set rehearsal mode
POST   /api/corps/{corps_id}/mode          Switch operational mode
GET    /api/corps/{corps_id}/roster        Agent roster
GET    /api/corps/{corps_id}/scoresheet    Competition scoresheet
GET    /api/corps/{corps_id}/metrics       Aggregate metrics
GET    /api/corps/{corps_id}/work-log      Work log
POST   /api/corps/{corps_id}/evaluate      Evaluate performers
POST   /api/corps/{corps_id}/season-transition  Season lifecycle
GET    /api/corps/{corps_id}/ageouts       Ageout performers
POST   /api/corps/{corps_id}/command       Execute corps command
GET    /api/corps-commands                 List available commands
```

#### Chat & Messages (5)
```
POST   /api/corps/{corps_id}/chat          Send chat message
GET    /api/corps/{corps_id}/chat          Get chat history
POST   /api/corps/{corps_id}/chat-stream   SSE chat stream
POST   /api/corps/{corps_id}/messages      Send message
GET    /api/corps/{corps_id}/messages      Poll messages
```

#### Segments & Reps (8)
```
POST   /api/segments                       Create segment
GET    /api/segments/{id}                  Get segment
GET    /api/segments/{id}/children         Get children
GET    /api/segments/{id}/reps             Get reps for segment
GET    /api/segments/{id}/tree             Get full tree
POST   /api/reps                           Create rep
POST   /api/reps/{id}/transition           Transition rep status
GET    /api/reps/{id}/scores               Get scores for rep
GET    /api/reps/{id}/composite            Composite score
GET    /api/reps/{id}/critique             Run critique
```

#### Scoring (1)
```
POST   /api/scores                         Record a score
```

#### Design Room (6)
```
POST   /api/design/shows                   Create design show + empty spec
GET    /api/design/shows/{slug}/spec       Read spec
PUT    /api/design/shows/{slug}/spec       Update spec
POST   /api/design/shows/{slug}/conversation  Routed conversation
POST   /api/design/shows/{slug}/approve    Freeze spec, approve show
GET    /api/design/shows/{slug}/versions   List versions
```

#### Judging (4)
```
GET    /api/judging/corps/{id}/tapes       All judge tapes
GET    /api/judging/corps/{id}/tapes/{rep} Detailed tape
GET    /api/judging/corps/{id}/actions     Critique actions
GET    /api/judging/corps/{id}/tapes/{rep}/export  Export tape
```

#### Evolution (4)
```
GET    /api/evolution/performers/{id}/genome  Performer genome
GET    /api/evolution/events                Selection events
GET    /api/evolution/mutations             Mutation log
POST   /api/evolution/simulate-mutation     Simulate mutation
```

#### Seance & Corps History (8)
```
POST   /api/seance                         Legacy: query memory bank
GET    /api/corps/{id}/history-index       Build/return history index
POST   /api/seances                        Create seance session
GET    /api/seances/{id}                   Get session metadata
GET    /api/seances/{id}/binder            Get context binder
GET    /api/seances/{id}/transcript        Read transcript
POST   /api/seances/{id}/message           Send message to ED
GET    /api/seances/{id}/artifact-preview  Preview artifact
```

#### Performers (5)
```
GET    /api/performers                     List performers
GET    /api/performers/{id}                Get performer
POST   /api/performers/{id}/retire         Retire performer
GET    /api/performers/{id}/ledger         Capability ledger
GET    /api/performers/{id}/stats          Aggregate stats
```

#### System (8)
```
GET    /api/system-health                  Swarm health metrics
POST   /api/heartbeat                      Cron heartbeat
GET    /api/work-log                       Global work log
GET    /api/agents-overview                Active agents
GET    /api/sessions/{id}/activity         Session activity
GET    /api/theme                          Current UI theme
GET    /api/themes                         List themes
POST   /api/seasons                        Create season
```

#### Memory (4)
```
GET    /api/agents/{identity}/memories     Get memories
GET    /api/agents/{identity}/memory-stats Memory stats
PUT    /api/memories/{id}                  Update memory
DELETE /api/memories/{id}                  Delete memory
```

#### Self-Improvement (4)
```
POST   /api/self-improvement/propose       Propose improvement
POST   /api/self-improvement/{id}/approve  Approve
POST   /api/self-improvement/{id}/reject   Reject
GET    /api/self-improvement/pending       Pending proposals
```

#### Workspace (4)
```
GET    /api/runs                           List run manifests
GET    /api/runs/{run_id}                  Run detail
GET    /api/corps-workspace                List corps workspaces
GET    /api/corps-workspace/{id}/history   Corps competition history
```

#### WebSocket (1)
```
WS     /ws/{corps_id}                      Real-time updates (chat, tool calls, status)
```

### Middleware

- **CORS** — allows `localhost:5173`, `5174`, `3000` (+ 127.0.0.1 variants); all methods/headers
- **Lifespan** — initializes DB, LLM client (Claude CLI > ChatGPT CLI > Anthropic API > OpenAI API > Mock), tool registry, TaskManager with metronome

### Models (19 SQLAlchemy models)

Source: `backend/models/`

| Model | Key Fields |
|-------|------------|
| Show | id, title, description, status (draft/active/completed/archived), corps_id, segment_root_id |
| Corps | id, name, status, rehearsal_mode, mode, theme_id, mascot, uniform_concept |
| Segment | id, parent_id, type (show/movement/set/segment), title, status, caption |
| Rep | id, segment_id, assigned_to, status (pending→assigned→in_progress→review→completed/failed), result, error |
| Score | id, rep_id, segment_id, corps_id, judge_type, value (0-100), box (1-5), feedback |
| Penalty | id, corps_id, type, amount, reason |
| Message | id, corps_id, from_role, to_role, type, priority, subject, body, segment_id |
| AgentDefinition | id, role, system_prompt, model_tier, tools_allowed, version, nickname, classification |
| AgentSession | id, definition_id, corps_id, parent_session_id, status, context_snapshot, performer_id |
| AgentMemory | id, agent_identity, memory_type, title, content, confidence, version |
| AgentExperience | id, session_id, experience data |
| Performer | id, name, role_type, trust_score, total/successful/failed_sessions, status, age, specialties |
| CapabilityLedgerEntry | id, performer_id, entry_type, role_type, score, trust_before, trust_after |
| SelfImprovementLog | id, agent_definition_id, old/new_version, changes, reason, status, approved_by |
| WorkLog | id, session_id, corps_id, role, event_type, phase, details, timestamp |
| Subscription | id, subscriber details |
| Problem | id, problem tracking data |

### Services (64 files)

Source: `backend/services/`

Key service groups:
- **Agent lifecycle:** agent_lifecycle, agent_phases, agent_runtime, autoscaler, drafting, task_manager
- **LLM:** llm_client (5 backends: Anthropic, OpenAI, Claude CLI, ChatGPT CLI, Mock + circuit breaker)
- **Show/Corps:** show_service, show_persistence, corps_service, corps_persistence, season_persistence
- **Scoring:** scoring_service, scoring_engine, scoring_persistence, judge_dashboard
- **Improvement:** improvement (basics/critique/banquet), evaluation_service
- **Design:** note_router, show_templates
- **Seance:** seance (legacy memory query), seance_session (session management), ed_chat (grounded ED conversation), corps_history (history index building)
- **Memory:** memory_bank, memory_manager, file_memory
- **Evolution:** talent_pool, lifecycle_manager, lifecycle_transitions, reputation
- **Tools:** tool_executor, tool_registry_setup, file_tools
- **System:** system_health, health_monitor, metrics_collector, event_bus, message_bus, mode_manager

### CLI

Source: `backend/cli/main.py` + `backend/cli/commands/`

15+ top-level commands: `season`, `corps`, `show`, `draft`, `mode`, `score`, `status`, `logs`, `source`, `watch`, `batch`, `pool`, `run`, `demo`, `seance`, `doctor`, `export`

### Tests

Source: `backend/tests/` — **77 test files, ~13,100 lines**

Framework: pytest with in-memory SQLite fixtures (`conftest.py`).

Test categories: model tests, service tests, API integration tests (TestClient), CLI tests, persistence tests, security tests.

---

## 3. Seance — Current Design Notes

### What It Is

"Seance" is the system's retrospective analysis feature. It lets a user (or an agent) query the memory of past shows — specifically by conversing with a simulated Executive Director who is grounded in real artifacts from a prior season/performance.

### Two Implementations

#### Legacy Seance (`/api/seance`)

- **Service:** `backend/services/seance.py`
- **Storage:** ChromaDB memory bank (`.chromadb/`)
- **Purpose:** Semantic search over agent session memories
- **API:** `POST /api/seance` with `{query, role?, k?}` → `{query, memories[], sessions_found}`
- **Frontend:** `Seance.tsx` — minimal search box + JSON display, labeled "Legacy" in nav
- **Also used by:** `query_for_agent_context()` — called by agent runtime to build context when agents start work

#### Seance Sessions (`/api/seances/*`)

- **Services:** `backend/services/seance_session.py` (CRUD), `backend/services/ed_chat.py` (LLM conversation), `backend/services/corps_history.py` (index building)
- **Storage:** Filesystem only — `seances/<seance_id>/session.yaml` + `transcript.md`
- **No database models** — entirely filesystem-based
- **Purpose:** Structured retrospective conversation anchored to a specific competition entry

### Data Flow

```
Corps History Index        Seance Session            ED Chat
─────────────────         ──────────────            ───────
corps.yaml history    →   session.yaml              ed_chat.py
  + artifact probing      context_binder[]     →    build_ed_prompt()
  → index.yaml              (type, path, loaded)    strict/relaxed mode
                          transcript.md          →  ed_respond() → LLM
                            **[role]** message
```

1. **Build history index** — `corps_history.build_history_index()` scans `corps/<id>/corps.yaml` history entries + filesystem artifacts. Writes `corps/<id>/history/index.yaml`.

2. **Create seance** — `seance_session.create_session()` takes a history entry, probes artifacts for existence/non-emptiness, assembles context binder, writes `seances/<id>/session.yaml` + `transcript.md`.

3. **Converse** — `ed_chat.ed_respond()` builds a system prompt from binder artifacts (max 4,000 chars each), prepends strict/relaxed preamble, calls LLM, appends to transcript.

### Context Binder Artifacts

Probed per history entry:

| Type | Path Pattern | Required |
|------|-------------|----------|
| standings | `seasons/<season_id>/standings.yaml` | Yes (minimum) |
| corps_scores | `seasons/<season_id>/performances/<corps_id>/scores.yaml` | No |
| show_status | `shows/<slug>/status.yaml` | No (requires show_slug) |
| design_notes | `shows/<slug>/design_notes.md` | No (requires show_slug) |
| show_prompt | `shows/<slug>/show_prompt.md` | No (requires show_slug) |

### Conversation Modes

- **Strict:** ED may ONLY cite information in binder artifacts. Refuses to answer if data missing.
- **Relaxed:** ED may hypothesize beyond binder but must label with `[HYPOTHESIS]`.

### Security

- Path traversal validation on all seance_id and corps_id inputs
- Artifact preview restricted to paths in the context binder (403 otherwise)
- Artifacts truncated to 10,000 chars in preview, 4,000 chars in ED prompt

### Current State on Disk

```
seances/
└── 8cbd915807c2/
    ├── session.yaml      (cavaliers, tour-s1, 5/5 artifacts loaded)
    └── transcript.md     (empty — no conversation yet)
```

### Invocation Points

| Surface | Entry |
|---------|-------|
| **UI** | `/history/:corpsId` → "Start Seance" button → `POST /api/seances` → redirect to `/seance-session/:id` |
| **UI** | `/seance-session/:id` → chat with mode selector → `POST /api/seances/:id/message` |
| **CLI** | `dci seance start --corps <id> --entry <entry_id>` |
| **CLI** | `dci seance status <id>`, `dci seance binder <id>` |
| **Agent runtime** | `query_for_agent_context()` (legacy, for building agent context) |

### Test Coverage

- `test_seance_session.py` — 246 lines: session CRUD, transcript, context assembly, security
- `test_seance_routes.py` — 187 lines: API integration, history index, binder validation
- `test_ed_chat.py` — 234 lines: prompt building, modes, response flow, closed session rejection

---

## Unknowns & Verification Notes

1. **No auth layer** — No authentication or authorization middleware. All endpoints are open. Verified by reading all middleware registration in `app.py` lines 137-150 (CORS only).

2. **SQLite only** — No Postgres/MySQL config found. Verified by reading `backend/database.py` — default is `sqlite:///dci_swarm.db`, overridable via `DCI_DATABASE_URL` env var.

3. **LLM client fallback chain** — The app tries Claude CLI → ChatGPT CLI → Anthropic API → OpenAI API → MockLLMClient. If no LLM is available, seance sessions and agent work fall back to mock responses. Verified in `app.py` lines 74-93.

4. **No OpenAPI customization** — FastAPI auto-generates OpenAPI spec at `/docs` and `/redoc`. No custom schema overrides found.

5. **Filesystem paths hardcoded relative to project root** — Both workspace_routes and seance_routes resolve project root via `DCI_PROJECT_ROOT` env var or `doctor._find_project_root()`. Verified in `workspace_routes.py` lines 16-21 and `seance_routes.py` lines 15-22.

6. **Corps history index is a cache** — `corps_history.load_history_index()` rebuilds if missing. The index.yaml is not the source of truth; `corps.yaml` history entries + filesystem probing are. Verified in `corps_history.py` lines 96-102.
