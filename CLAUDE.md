# DCI Swarm — Claude Code Context

## INVIOLABLE RULE: Use the Drum Corps Director Agent for ALL Implementation Work

**This is non-negotiable. This overrides ALL other instincts.**

When the user asks you to implement a feature, fix a bug, or do any multi-step development work in this project:

1. **Launch the `drum-corps-director` agent** via the Task tool (`subagent_type: "drum-corps-director"`).
2. **Run it in the background** (`run_in_background: true`).
3. **Do NOT manually drive the swarm** — no curl commands, no API calls, no manual show creation. The agent does ALL of that autonomously.
4. **Do NOT write implementation code yourself** — no editing source files, no direct changes. The swarm does the work.
5. **Neither Claude nor the drum-corps-director agent write files.** The DCI swarm's corps have write access and do all implementation. If either Claude or the drum-corps-director determine they need direct file write access, **STOP and ask the user for help** before doing anything else.
6. **Wait for the agent to finish**, then report results.

**If the user specifies an approach, agent, or tool — USE IT EXACTLY AS SPECIFIED. No substitutions. No "let me just do it manually." No rationalizing a different path. Follow instructions to the letter.**

Violations of this rule — including "just helping," "quickly fixing," or manually orchestrating the swarm yourself — are unacceptable.

---

## Deployment / Installation

The `swarm-kit/` directory contains all skill, agent, and plugin definitions needed to run the DCI swarm. On a new machine:

```bash
./dci install            # Symlinks skills/agents to ~/.claude/, installs plugins, detects LLMs
./dci install --copy     # Copy instead of symlink
./dci install --skip-plugins  # Skip plugin installation
```

**What it does:**
1. Runs `swarm-kit/detect-llm.sh` — checks for Claude CLI, ChatGPT CLI, API keys, Ollama
2. Symlinks skills from `swarm-kit/skills/` to `~/.claude/skills/` (project stays source of truth)
3. Symlinks agents from `swarm-kit/agents/` to `~/.claude/agents/`
4. Installs required + recommended Claude Code plugins via `claude plugin install`

**LLM requirements:** At least one provider must be available (Claude CLI preferred). Detection results are written to `swarm-kit/.llm-providers.yaml`.

**Directory structure:**
```
swarm-kit/
  skills/
    swarm-orchestrator/SKILL.md   # Swarm lifecycle orchestration
    dci-agent/SKILL.md            # Agent that submits all work to the swarm
    dci-dogfooding/SKILL.md       # Live system verification
  agents/
    drum-corps-director.md        # Drum Corps Director agent definition
  plugins.yaml                    # Required/recommended plugin manifest
  detect-llm.sh                   # LLM provider detection script
  install.sh                      # Installer script
```

---

## Tooling Inventory

Everything `./dci install` provisions, plus what's available when you open the project in Claude Code.

### Skills (7)
| Skill | Purpose |
|-------|---------|
| `swarm-orchestrator` | Drives the swarm through its full lifecycle (prompt → verified completion) |
| `dci-agent` | Submits all implementation work to the swarm — never writes code directly |
| `dci-dogfooding` | Exercises new features/endpoints against the live running swarm |
| `dci-api-corps` | API actions for corps management (list, create, identity, lifecycle commands) |
| `dci-api-shows` | API actions for shows and Design Room (create, design, lint, approve, publish) |
| `dci-api-seasons` | API actions for seasons and competitions (create, register, run, score, recap) |
| `dci-api-system` | API actions for system monitoring (health, LLM usage, agents overview, work log) |

### Agents (1)
| Agent | Purpose |
|-------|---------|
| `drum-corps-director` | Autonomous orchestrator — creates shows, runs seasons, evaluates results through the DCI swarm |

### Plugins (7)
| Plugin | Type | Purpose |
|--------|------|---------|
| `ralph-loop` | Required | Self-sustaining orchestration loops |
| `playwright` | Required | E2E browser testing and verification |
| `frontend-design` | Recommended | UI generation for design room |
| `context7` | Recommended | Up-to-date library documentation |
| `code-review` | Recommended | Parallel code review with confidence scoring |
| `feature-dev` | Recommended | Structured feature development workflow |
| `superpowers` | Recommended | Skill system for disciplined agent workflows |

### CLI Commands (15 via `./dci`)
| Command | Purpose |
|---------|---------|
| `ten-hut` | Full stack: backend + frontend + TMUX dashboard |
| `parade-rest` | Shut everything down |
| `mark-time` | TMUX dashboard session management |
| `forward-march` | Backend only |
| `company-front` | Frontend only |
| `run-through` | Run pytest test suite |
| `check-step` | Quick health/status check |
| `set-the-field` | Initialize workspace (DB, dirs) |
| `resume-hut` / `dress-center` | Resume stopped services |
| `drill` | Run a calibration drill (agent swarm on a task) |
| `pool` | Talent pool management |
| `doctor` | Diagnose system issues |
| `install` | Install skills, agents, plugins, detect LLMs |
| `swarm` | DCI Swarm CLI (season, corps, show, mode, status) |
| `horns-up` / `help` | Show help |

### LLM Providers (5 detected)
| Provider | Type | Priority |
|----------|------|----------|
| `claude-cli` | CLI | 1 (primary) |
| `codex-cli` | CLI | 2 |
| `anthropic-api` | API | 3 |
| `ollama` | Local | 5 |
| `cursor` | IDE | 6 (interactive only) |

### What Happens When You Open the Project
1. Claude Code reads `CLAUDE.md` and `docs/` for full context
2. Skills from `~/.claude/skills/` are available via the Skill tool
3. The `drum-corps-director` agent is available via the Task tool
4. Plugins provide Playwright browser control, Context7 docs, code review, and feature dev workflows
5. The `superpowers` plugin enforces skill discipline — skills are checked before every action

---

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
| `backend/api/v1/` (25 domain routers) | V1 API split by domain: corps, design, competitions, messaging, seasons, runs, seances, shows, performers, system, segments, reps, metrics, critique, evolution, admin, judging, self_improvement, agents, staff, templates, ci, awards, misc, scoreboards |
| `backend/api/v1/helpers.py` | Shared utilities: `_get_root`, `_validate_id`, `_get_db_session`, `_get_llm_client`, etc. |
| `backend/api/v1/schemas.py` | 27 Pydantic request models for all V1 endpoints |
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
4. **Frontend API client**: Use `v1.ts` for all code. Legacy `api.ts` is fully deprecated — zero files import it.
5. **Season ID parsing**: Season IDs can contain hyphens (e.g. `tour-s1`), so competition_id splitting must match against actual season directories

## Testing

```bash
python -m pytest backend/tests/ -v          # All tests
python -m pytest backend/tests/test_v1_api.py  # V1 API tests
cd frontend && npx tsc --noEmit             # TypeScript check
```

## Current State (as of 2026-02-01)

### ✅ Post-Zero-State Cleanup (Completed This Session)

- **Phase A: Git Tag** — Tagged `v0.0.0-zero-state` at commit `588b04e`
- **Phase B: V1 Router Split** — Split monolithic `router.py` (6,080 lines) into 25 domain routers:
  - `backend/api/v1/helpers.py` — shared utilities (`_get_root`, `_validate_id`, `_get_db_session`, etc.)
  - `backend/api/v1/schemas.py` — 27 Pydantic request models
  - 25 domain routers: corps, design, competitions, messaging, seasons, runs, seances, shows, performers, system, segments, reps, metrics, critique, evolution, admin, judging, self_improvement, agents, staff, templates, ci, awards, misc, scoreboards
  - `backend/api/v1/router.py` is now a backward-compat shim re-exporting from helpers
- **Phase C: Legacy Router Removal** — Deleted all 9 legacy routers (`backend/api/legacy/` removed entirely)
  - Migrated 5 test files from legacy endpoints to V1 paths and response shapes
  - Patched `SessionFactory` in test fixtures for proper DB isolation
  - Fixed `_build_chat_agent_context` imports → `backend.services.chat_service`
  - Fixed `_shows_base_dir()` to respect `DCI_PROJECT_ROOT` env var
- **Phase D: Segment Tree Filtering** — Bug was in deleted legacy code; V1 endpoints use proper parent_id filtering
- **Phase E: Show Prompt Synthesis** — Synthesized `show_prompt.md` for 2 shows with spec+design_notes content
- **Phase F: Run Execution Wiring** — `POST /api/v1/runs` now attempts `task_manager.start_agent()` with stub fallback

### ✅ Previously Completed
- Design Room prompt rewrite, Legacy→V1 API consolidation, Ready-for-Contest lifecycle
- Asynchronous messaging system, Scoreboards & Metrics, Metronome system
- Frontend v1.ts migration, LLM multi-provider connector, UI redesign (Field Commander Brutalism)
- synthesize_prompt(), app.py extraction, Alembic migrations, Evolution & Talent Pool

### Architecture
- **V1 API**: 25 domain routers in `backend/api/v1/`, ~165 routes total
- **Non-legacy routers**: workspace_routes, design_room_routes, judging_routes, evolution_routes, seance_routes (still in `backend/api/`)
- **app.py**: ~180 lines — lifespan, WebSocket, CORS, router inclusions only
- **No legacy routes remain** — all test and production code uses V1 endpoints

### Known Issues
- **8 pre-existing test failures**: test_competition_scoring (4, missing corps table in judge_service), test_coverage_boost (1, autoscaler assertion), test_judging_routes (1), test_show_persistence (1), test_v1_api competitions (1)
- **Scoresheet model missing**: `backend.models.scoresheet` does not exist; V1 scoresheet endpoint returns empty data with debug log
