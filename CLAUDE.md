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

### ✅ Recently Completed (This Session)
- **Metronome system agent**: Published, orchestrator messaging integration complete
- **synthesize_prompt()**: Implemented — assembles show_prompt.md from spec + tagged design notes
- **app.py extraction**: Monolith split into 9 domain routers under backend/api/legacy/ (2217→249 lines)
- **Alembic migrations**: Schema fully synced, deprecated tables removed, workflow operational
- **Frontend v1 migration**: RunDetail, RunsList, CorpsDeepDive, ModeContext migrated to v1.ts
- **Show spec cleanup**: Removed duplicate directories, added specs to 4 pending shows
- **Metrics services**: metrics.py, metrics_aggregation.py, metronome_heartbeat.py committed

### Working
- 5+ active corps (DB-only, filesystem corps deleted)
- V1 API router with 47 routes (39 → 47 after messaging endpoints)
- **Asynchronous messaging system** (NEW): Full lifecycle — thread creation → multi-message conversation → manual completion → bulk archival with summaries → searchable archive
- Design room has LLM-powered responses via shared Claude CLI client
- Corps creation modal with auto-generated identity (name, mascot, colors)
- Season CRUD endpoints (create, list, get, update, register corps)
- Competition pipeline fixed for hyphenated season IDs and DB-only corps
- Corps detail page with lifecycle controls (go on tour, return to camps, rehearsal modes)
- Corps History page switched to v1 API
- Agent performer assignment and audition pipeline working for new corps
- System health monitoring and swarm health aggregation

### In Progress / Ready for Implementation
- **Caption-awards achievement system**: Spec drafted, design notes in progress
- **Ready-for-Contest Lifecycle**: Spec written, design notes extensive, needs implementation
- **Seasons & Standings UI**: Spec written, needs frontend implementation
- **Staff Marketplace & Career Evolution**: Spec written, needs frontend implementation
- **System Health Dashboard**: Spec written, needs frontend implementation

### Known Issues / Not Yet Working
- **Some frontend pages still use legacy `api.ts`** — ~25 files still need migration (most lack v1 equivalents, need new v1 endpoints first)
- **3 pre-existing test failures** in test_system_health and test_agents_overview (agent counting logic)
