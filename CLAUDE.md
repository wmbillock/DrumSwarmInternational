# DCI Swarm — Claude Code Context

## Session Initialization

**On every new session in this project, you MUST:**

1. **Read the `docs/` directory** for current architecture, schemas, and plans:
   - `docs/architecture.md` — system layers, data model, lifecycle, communication, scoring
   - `docs/domain-glossary.md` — DCI terminology mapped to engineering concepts
   - `docs/quality/quality_contract.md` — 45+ observable behaviors and test matrix
   - `docs/ui/` — UI plans for each page (design_room.md, competitions.md, corps_history_plan.md, etc.)
   - `docs/shows/routing_rules.md` — how design notes route to creative staff roles
   - `docs/shows/prompt_lint_rules.md` — prompt validation rules
   - `docs/seasons/season_schema.md` — season workspace structure
   - `docs/corps/corps_schema.md` — corps workspace structure
   - `docs/scoring/reputation_system.md` — reputation and trust scoring
   - `docs/pool/talent_pool_schema.md` and `drafting_rules.md` — performer lifecycle
   - `docs/api/openapi.md` — API reference
2. **Scan `shows/` directory** for active shows (each is a feature/task being tracked by the swarm)
3. **Check git status** to understand what's in flight
4. **Read this file fully** before making any changes

## Stewardship

**Keep this file and project docs up to date.** When you make significant changes:
- Update the "Current State" section at the bottom of this file
- If you add new endpoints, update `docs/api/openapi.md`
- If you change UI pages, update the relevant file in `docs/ui/`
- If you modify the data model, update `docs/architecture.md`
- If you create a new show for tracking work, document it in the show's `spec.md`
- Do NOT leave stale report files, investigation artifacts, or temporary docs in the project root — clean up after yourself
- Do NOT create new LLM clients, agent systems, or AI integrations — the system already has one (see below)

## What This Project Is

A multi-agent orchestration system using drum corps international (DCI) as its organizing metaphor. Corps of AI agents collaborate through seasons of shows, scored performances, and reputation-driven drafting.

**This is NOT a simple web app.** It is a full agent swarm with its own lifecycle, communication hierarchy, and execution engine.

## Critical Architecture Facts

### LLM Client — Already Configured

The backend initializes ONE shared LLM client at startup in `backend/api/app.py` lifespan():

```
Priority: Claude CLI > ChatGPT CLI > Anthropic API > OpenAI API > Mock
```

The Claude CLI (`claude` command) is the **primary agent runner**. It is already installed and is the same tool you are running in right now. Do NOT create new LLM clients or add new AI integrations — use `_task_manager.llm_client` from `backend.api.app.get_task_manager()`.

### Agent Execution System

Agents run through `backend/services/agent_runtime.py` `run_agent()`:
- Loads agent definition + session from DB
- Builds system prompt with role, phase guidance, corps context
- Runs iterative LLM loop with tool execution
- Persists memories, work logs, context snapshots

The `TaskManager` (`backend/services/task_manager.py`) manages async agent execution and the metronome background task.

### Dual Persistence

- **Filesystem** (`corps/`, `shows/`, `seasons/`, `seances/`): workspace artifacts, specs, design notes, YAML configs
- **SQLite DB**: runtime state (corps, agents, sessions, reps, scores, messages)
- The V1 API merges both sources when listing entities
- Corps files in `corps/` have been deleted from git — corps are now DB-only. The filesystem path still works for corps that have workspace dirs.

### Corps Lifecycle

```
INITIALIZING → WINTER_CAMPS → ON_TOUR → COMPLETED / DISBANDED
```

- **Winter Camps**: Planning. User talks to ED. Design Room active.
- **On Tour**: Autonomous execution. Agents work independently.
- Lifecycle commands (go_on_tour, return_to_camps, etc.) at `POST /api/corps/{id}/command` in app.py

### Rehearsal Mode Progression

```
BASICS → SECTIONALS → FULL_ENSEMBLE → RUN_THROUGH
```

Auto-progresses based on milestones. Mode-aware dispatch restricts which agents can communicate.

### Communication Hierarchy

ED → PC → Design Staff → Caption Heads → Techs → Performers. Messages are hierarchy-enforced. A performer cannot send a directive.

## Key File Map

### Backend
| File | Purpose |
|------|---------|
| `backend/api/app.py` (~250 lines) | FastAPI app, WebSocket, lifespan init, router inclusions |
| `backend/api/legacy/` (9 routers) | Extracted legacy routes: shows, corps, segments, scoring, communication, system, performers, improvement, memory |
| `backend/api/v1/router.py` (~1200 lines) | V1 API — corps, runs, design room, competitions, seasons, seances |
| `backend/services/agent_runtime.py` | Agent execution loop with LLM + tools |
| `backend/services/task_manager.py` | Async agent orchestration, metronome |
| `backend/services/llm_client.py` | LLM abstraction: ClaudeCLIClient, ChatGPTCLIClient, AnthropicLLMClient, Mock |
| `backend/services/corps_service.py` | Corps init, lifecycle transitions, go_on_tour, return_to_camps |
| `backend/services/show_persistence.py` | Show workspace disk I/O |
| `backend/services/season_persistence.py` | Season workspace management |
| `backend/services/nickname_generator.py` | Corps name + mascot + agent nickname generation |
| `backend/services/ed_chat.py` | ED retrospective chat (seance-based, grounded in artifacts) |
| `backend/services/note_router.py` | Tag-based routing of design notes to roles |
| `backend/models/corps.py` | Corps model with status, mode, theme, mascot fields |
| `backend/database.py` | SQLAlchemy setup, Alembic migrations |

### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/services/v1.ts` | Typed V1 API client (use this, not api.ts) |
| `frontend/src/services/api.ts` | Legacy API client (being phased out) |
| `frontend/src/pages/DesignRoom.tsx` | Design room page orchestrator |
| `frontend/src/components/DesignChat.tsx` | Design chat with LLM-powered responses |
| `frontend/src/pages/CorpsList.tsx` | Corps list with creation modal |
| `frontend/src/pages/CorpsDetailV2.tsx` | Corps detail with lifecycle controls |
| `frontend/src/pages/CompetitionsList.tsx` | Competition management |
| `frontend/src/components/CorpsCreateModal.tsx` | Corps identity generation modal |

### CLI
| Command | Purpose |
|---------|---------|
| `./dci ten-hut` | Full stack: backend + frontend + TMUX dashboard |
| `./dci forward-march` | Backend only |
| `./dci company-front` | Frontend only |
| `./dci parade-rest` | Shut everything down |
| `./dci run-through` | Run pytest |

## Design Room

The Design Room (`/design/:showSlug`) is a two-pane collaboration interface:
- **Left**: Chat with creative staff (messages route to music_writer, drill_writer, choreographer, program_coordinator based on content tags)
- **Right**: Artifact panel (Brief/Prompt/Versions tabs)

Messages go through `POST /api/v1/design/threads/{slug}/messages` which:
1. Routes via `note_router` to determine tags and role
2. Persists user message to `design_notes.md`
3. Calls the shared LLM client (Claude CLI) with role-specific system prompt + spec context
4. Persists agent response to `design_notes.md`
5. Returns response to frontend

Show lifecycle: `draft → needs_review → approved → published`

## Shows, Seasons, Competitions

- **Shows** live in `shows/<slug>/` with status.yaml, design_notes.md, spec.md, show_prompt.md
- **Seasons** live in `seasons/<season_id>/` with season.yaml, performances/, standings.yaml
- **Competitions** are virtual (season + show pairs) — no separate DB entity
- Competition IDs are `{season_id}-{show_slug}` — use `_parse_competition_id()` in router.py to handle hyphenated season IDs

## Common Pitfalls

1. **React hooks**: All hooks must be called before any early returns in components
2. **Corps validation**: Corps may be DB-only (no filesystem `corps.yaml`). Always check DB as fallback.
3. **SQLAlchemy 2.0**: Use `select().where().correlate()` not `db.query().filter().correlate()` inside `exists()`
4. **Frontend API client**: Use `v1.ts` for all new code, not the legacy `api.ts`
5. **Season ID parsing**: Season IDs can contain hyphens (e.g. `tour-s1`), so competition_id splitting must match against actual season directories

## Testing

```bash
python -m pytest backend/tests/ -v          # All tests
python -m pytest backend/tests/test_v1_api.py  # V1 API tests
cd frontend && npx tsc --noEmit             # TypeScript check
```

## Current State (as of 2026-02-01)

### ✅ Recently Completed (This Session + Previous Sessions)
- **Ready-for-Contest Lifecycle**: ✅ COMPLETE
  - Backend: ready_for_contest() and complete_corps() with validation gates
  - V1 API: /ready-for-contest, /return-to-tour, /complete endpoints
  - Legacy routes: Command handlers for all three transitions
  - Frontend: Lifecycle buttons on CorpsDetailV2 for ON_TOUR → READY_FOR_CONTEST → COMPLETED flow
  - Allows rework: Can return from READY_FOR_CONTEST → ON_TOUR
- **Asynchronous Messaging System**: ✅ COMPLETE
  - Database schema: message threads, messages, archive tables
  - Backend: MessagingService, MessagingPermissions, SummaryService
  - V1 API: Thread CRUD, message endpoints, bulk-archive, search
  - Frontend: MessageInbox, MessageArchive pages with full lifecycle
  - LLM Integration: Async summary generation for archived threads
- **Scoreboards & Metrics**: ✅ COMPLETE
  - Backend: Corps/Agent/Performer ranking endpoints with composite scoring
  - Frontend: ScoreboardsPage with tabs, sorting, detail drill-down
  - Integration: Full metrics aggregation with latency, throughput, reliability
- **Metronome System**: ✅ COMPLETE (Earlier)
  - Cron script (scripts/metronome/tick.sh) with lock file concurrency
  - Orchestrator with ten-hut/resume-hut messaging integration
  - Status gathering and RED FLAG alerting
- **Other Earlier Work**:
  - synthesize_prompt() — spec + design notes → show_prompt.md
  - app.py extraction (2217→249 lines, 9 domain routers)
  - Alembic migrations operational
  - Frontend v1 API migration (RunDetail, RunsList, CorpsDeepDive)
  - Evolution & Talent Pool fixed (786 sessions backfilled with performers)
  - System health status calculation (ok/warning/error)

### Working (Complete Feature List)
- 11+ active corps with full lifecycle management
- V1 API router with 60+ endpoints
- **Corps Lifecycle**: INITIALIZING → WINTER_CAMPS ⇄ ON_TOUR → READY_FOR_CONTEST ⇄ COMPLETED
- **Messaging**: Threaded inbox, bulk archive with LLM summaries, searchable archive, permission enforcement
- **Metrics & Scoring**: Composite scores, leaderboards, trend analysis, performance bottleneck detection
- **Metronome**: 5-minute heartbeat, corps liveness monitoring, stalled work recovery
- **Design Room**: LLM-powered collaboration with role-based routing and spec synthesis
- **Rehearsal Modes**: BASICS → SECTIONALS → FULL_ENSEMBLE → RUN_THROUGH with auto-progression
- **Agent System**: Full role hierarchy (ED → PC → Designers → Caption Heads → Techs), performer assignment, audition pipeline
- **Seasons & Competitions**: Season management, competition registration, standings calculation
- **System Health**: Real-time monitoring with status indicators (ok/warning/error)

### In Progress / Ready for Implementation
- **Caption-awards achievement system**: Spec drafted (12 categories, 360 achievements), TDD framework ready
- **Chat-test show**: ✅ PERCUSSION ASSIGNMENT COMPLETE
  - Rep 08741bf4-e594-4004-88bc-6bedbcdd268d assigned to Wayne Fortissimo (percussion_caption_head)
  - Status: IN_PROGRESS (pending → assigned → in_progress)
  - Task: Full percussion specification for fanfare opening (counts 1-32, geometric guard choreography)
- **Let's Build Metrics show**: Dashboard visualization movement in progress
- **Staff Marketplace**: Page exists, API endpoints defined (hiring, firing, career tracking)
- **System Health Dashboard**: Frontend page with real-time metrics
- **Seasons & Standings UI**: Spec written, needs frontend implementation

### Recently Fixed (This Session)
- **Test Failures Fixed**: ✅
  - test_system_health (5/5 tests passing)
  - test_agents_overview (15/15 tests passing)
  - Fixed: AgentDefinition.corps_id assignment in test setup
  - Fixed: Removed incorrect session deduplication in agents-overview endpoint
- **Scoreboards Router**: ✅ Included scoreboards.py router in app.py

### Metronome Status (2026-02-01)
- **Corps b8fb873a-77ff-41e0-865b-58b93c2065d6**:
  - Reps reclaimed: 1 (self-healed by metronome — indicates potential async rep calculation race)
  - Merges: 12/31 (39% rate, 0 conflicts) — normal backlog during ON_TOUR
  - System Status: 🟡 **WARNING** — continued monitoring recommended

### Known Issues / Not Yet Working
- **Frontend migration**: ~25 files still using legacy `api.ts` instead of v1 typed client
  - Pages affected: CommandCenter, AdminChat, Templates, Performers, Seance, JudgingCritique, EvolutionTalentPool, CorpsDeepDive, SystemHealth (9 main pages)
  - Requires endpoint analysis and careful refactoring per page
- **2 test failures in test_v1_api.py**: Unrelated to this session (test expects empty DB but finds existing corps)
