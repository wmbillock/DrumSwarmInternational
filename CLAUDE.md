# DCI Swarm — Claude Code Context

A multi-agent orchestration system using DCI (drum corps international) as its organizing metaphor. Corps of AI agents collaborate through seasons of shows, scored performances, and reputation-driven drafting. **This is a full agent swarm, not a simple web app.**

## INVIOLABLE RULES

Determine your session type before doing anything else.

- **User session**: Interactive terminal with a human. No DCI role in system prompt. When in doubt, you are this.
- **Agent session**: Spawned by the swarm (`agent_runtime.py`, `ClaudeCLIClient`, or Task tool). Has role/corps/task in system prompt.

### User Sessions

1. **Launch `drum-corps-director`** via Task tool (`subagent_type: "drum-corps-director"`, `run_in_background: true`).
2. **Do NOT write code or drive the swarm manually.** The agent orchestrates; the corps implement.
3. If Claude or the director need file write access, **STOP and ask the user**.
4. If the user specifies an approach — follow it exactly. If they say "do it yourself" — do it directly.

### Agent Sessions

**Tier 1 — Orchestrators (drum-corps-director):** API-only orchestration via `curl`. No file writes. Never launch another director. Never create recursive swarm loops. If blocked, ask the user.

**Tier 2 — Admin/Instructional staff (ED, PC, caption heads):** Coordinate within your corps only. No Task tool. No external agents. May write files within your corps workspace.

**Tier 3 — Creative staff, techs, performers:** Execute your assigned task only. Write code as directed. Stay in your corps workspace. No delegation.

**All agents:** Never launch drum-corps-director. Never create new LLM clients. Never modify CLAUDE.md.

---

## Directory Guide

```
DrumSwarmInternational/
├── dci                         # CLI entrypoint (bash). Run ./dci horns-up for help
├── pyproject.toml              # Python package config, pytest settings
├── alembic.ini                 # Database migration config
├── dci_swarm.db                # SQLite database (created at runtime)
├── CLAUDE.md                   # This file
│
├── backend/                    # FastAPI application
│   ├── api/
│   │   ├── app.py              # App factory, lifespan, WebSocket, router mounts
│   │   └── v1/                 # 25 domain routers + schemas + helpers
│   ├── cli/                    # `./dci swarm` subcommands
│   │   ├── main.py             # Argument parser & dispatch
│   │   └── commands/           # 19 command modules (corps, season, show, run, etc.)
│   ├── config/                 # YAML configs (budget, themes, show templates, awards)
│   ├── models/                 # 22 SQLAlchemy ORM models
│   ├── prompts/                # Agent system prompts + 16 role manifests (YAML)
│   ├── services/               # 78 service modules (core business logic)
│   ├── tests/                  # 80+ pytest files + conftest.py
│   ├── tools/                  # Agent tools (metronome, tuner, cleaning, etc.)
│   └── database.py             # Engine factory, init_db, schema patches
│
├── frontend/                   # Vite + React 19 + TypeScript
│   ├── src/
│   │   ├── pages/              # 36 route pages
│   │   ├── components/         # 38 UI components
│   │   ├── contexts/           # 4 React contexts (theme, mode, show, corps)
│   │   ├── hooks/              # usePolling, useWebSocket, useCorpsContext
│   │   ├── services/v1.ts      # Typed API client (use this, NOT api.ts)
│   │   ├── ui/                 # Shared primitives (Card, Badge, Tabs, Panel, DataTable)
│   │   └── __tests__/          # 11 vitest files
│   ├── vitest.config.ts        # Vitest config (jsdom environment)
│   └── package.json
│
├── shows/                      # 28 show workspaces (status.yaml, spec.md, etc.)
├── seasons/                    # 12 season workspaces (season.yaml, performances/)
├── data/founding_corps/        # 12 seed corps YAML files
├── talent_pool/                # 10 agent definitions + ledger.yaml
├── prompts/                    # Top-level prompt templates (design, judging, rehearsal, etc.)
├── docs/                       # 40+ doc files (architecture, glossary, schemas, UI plans)
├── scripts/                    # Deployment, monitoring, metronome scripts
├── swarm-kit/                  # Claude Code agent definitions + 7 skills + installer
└── alembic/versions/           # DB migration scripts
```

## Local Development Setup

### Prerequisites

- Python >= 3.11
- Node.js >= 18 (22 recommended)
- npm

### Install from scratch

```bash
# 1. Clone the repo
git clone <repo-url> && cd DrumSwarmInternational

# 2. Python backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# 3. Frontend
cd frontend && npm install && cd ..

# 4. Initialize the database (runs Alembic migrations + create_all)
./dci set-the-field

# 5. (Optional) Install Claude Code skills/agents/plugins
./dci install                    # --symlink (default) or --copy
./dci install --skip-plugins     # skip Claude CLI plugin install
./dci install --skip-llm-check   # skip LLM provider detection
```

### Start everything

```bash
./dci ten-hut              # Backend + frontend + TMUX monitoring dashboard
```

Or start services individually:

```bash
./dci forward-march        # Backend only (uvicorn --reload on port 4224)
./dci company-front        # Frontend only (Vite dev server on port 5173)
./dci mark-time            # TMUX monitoring dashboard only
```

### Verify it's working

```bash
./dci check-step                                    # Status of all services
curl http://localhost:4224/api/v1/system/health      # Backend health JSON
curl http://localhost:5173                            # Frontend HTML
open http://localhost:4224/docs                       # Swagger UI
```

### Shutdown

```bash
./dci parade-rest          # Graceful shutdown (backend, frontend, TMUX, orphan agents)
./dci stand-down           # Nuclear cleanup — kill ALL DCI processes
```

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DCI_PORT` | `4224` | Backend port |
| `DCI_SESSION` | `dci-swarm` | TMUX session name |

---

## CLI Reference (`./dci <command>`)

### Stack Management

| Command | What it does |
|---------|-------------|
| `ten-hut` | Start backend + frontend + TMUX dashboard |
| `parade-rest` | Graceful shutdown of all services |
| `stand-down` | Nuclear cleanup — kill ALL DCI processes |
| `resume-hut` / `dress-center` | Restart backend + frontend, keep TMUX alive |
| `forward-march` | Backend only (uvicorn with --reload) |
| `company-front` | Frontend only (Vite dev server) |
| `mark-time` | TMUX monitoring dashboard only |
| `check-step` | Show status of all services |
| `set-the-field` | Initialize / migrate the database |
| `install` | Install skills, agents, plugins + detect LLMs |
| `horns-up` | Show help |

### Swarm CLI (`./dci swarm <command>`)

The swarm CLI auto-detects whether the API server is running (API mode) or falls back to direct DB access (direct mode). Force a mode with `--direct` or `--api-url <url>`.

| Command | Example | Purpose |
|---------|---------|---------|
| `corps list` | `./dci swarm corps list` | List all corps |
| `corps status <id>` | `./dci swarm corps status abc123` | Corps detail |
| `corps init <id>` | `./dci swarm corps init abc123 --yes` | Create corps workspace on disk |
| `corps history build <id>` | `./dci swarm corps history build abc123 --yes` | Build history index |
| `corps history list <id>` | `./dci swarm corps history list abc123` | List history entries |
| `show create <title>` | `./dci swarm show create "My Show" --yes` | Create show + workspace |
| `show list` | `./dci swarm show list` | List all shows |
| `show status <slug>` | `./dci swarm show status my-show` | Show workspace status |
| `show activate <id>` | `./dci swarm show activate abc123` | Activate a show |
| `show approve <slug>` | `./dci swarm show approve my-show --yes` | Approve a show |
| `season create <name>` | `./dci swarm season create s1 --yes` | Create season workspace |
| `season register-corps <sid> <cid>` | `./dci swarm season register-corps s1 abc123 --yes` | Register corps |
| `season run-contest <sid>` | `./dci swarm season run-contest s1 --show my-show --corps abc --yes` | Run contest |
| `draft run <corps_id>` | `./dci swarm draft run abc123` | Run agent draft |
| `mode switch <cid> <mode>` | `./dci swarm mode switch abc123 design_room` | Switch corps mode |
| `mode design-room <cid>` | `./dci swarm mode design-room abc123` | Shortcut: design room |
| `mode rehearsal <cid>` | `./dci swarm mode rehearsal abc123` | Shortcut: rehearsal |
| `score submit <cid>` | `./dci swarm score submit abc123 --caption brass --value 85.5` | Submit score |
| `status` | `./dci swarm status --json` | Swarm-wide status |
| `logs <cid>` | `./dci swarm logs abc123 --tail 50` | View work logs |
| `watch <cid>` | `./dci swarm watch abc123 --interval 5` | Live tail of activity |
| `source <desc>` | `./dci swarm source "fix the bug" --poll` | Accept external work |
| `run show <slug>` | `./dci swarm run show my-show --corps abc --season s1 --yes` | Full show run |
| `demo tour` | `./dci swarm demo tour --seed 1 --seasons 2 --corps-count 3 --yes` | Demo lifecycle |
| `seance start` | `./dci swarm seance start --corps abc --entry xyz --yes` | Start seance |
| `pool list` | `./dci swarm pool list --instrument brass` | List talent pool |
| `pool init` | `./dci swarm pool init --yes` | Initialize talent pool |
| `batch <yaml>` | `./dci swarm batch workflow.yaml --dry-run` | Scripted workflow |
| `export <cid>` | `./dci swarm export abc123 --format summary -o out.json` | Export corps data |
| `doctor` | `./dci swarm doctor --json` | Validate repo + environment |

### Drill (calibration)

```bash
./dci drill -p 1               # Run Euler problem #1
./dci drill -l 1,2,3           # Calibration loop on problems 1-3
```

### TMUX Hotkeys (inside `mark-time` session)

| Key | Action |
|-----|--------|
| `prefix+s` | Swarm menu (popup with all actions) |
| `prefix+1..6` | Switch dashboard view |
| `prefix+0` | Focus Claude Code pane |
| `prefix+d` | Focus Dashboard pane |
| `prefix+l` | Focus Backend log pane |
| `prefix+;` | Focus Frontend log pane |

---

## Testing

### Configuration

Backend tests use **pytest** configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["backend/tests"]
pythonpath = ["."]
```

The `conftest.py` fixture provides a `db` session backed by an **in-memory SQLite** database — each test gets a clean DB. No running server required for unit tests.

Frontend tests use **vitest** with jsdom, configured in `frontend/vitest.config.ts`.

### Running tests

```bash
# --- Backend (80+ test files, ~1169 tests) ---
./dci run-through                              # All backend tests (via CLI)
python -m pytest backend/tests/ -v             # Same thing, directly

# Filter by keyword
./dci run-through -k scoring                   # Only tests matching "scoring"
python -m pytest backend/tests/ -k "corps and not history"

# Single file
python -m pytest backend/tests/test_v1_api.py -v

# Stop on first failure
python -m pytest backend/tests/ -x

# --- Frontend (11 test files) ---
cd frontend && npx vitest run                  # All frontend tests (single run)
cd frontend && npx vitest                      # Watch mode
cd frontend && npx vitest run src/__tests__/CorpsList.test.tsx   # Single file

# --- TypeScript type check (no tests, just compilation) ---
cd frontend && npx tsc --noEmit
```

### Known test issues

- 2 test files fail to **collect** due to a syntax error in `backend/services/season_persistence.py` (escaped f-string quotes — fixed on this branch)
- 8 pre-existing test failures in: `test_competition_scoring`, `test_coverage_boost`, `test_judging_routes`, `test_show_persistence`, `test_v1_api`
- `backend.models.scoresheet` does not exist; scoresheet endpoint returns empty data

---

## Architecture

### LLM Client — Already Configured

ONE shared client initialized in `backend/api/app.py` lifespan(). Priority: Claude CLI > ChatGPT CLI > Anthropic API > OpenAI API > Mock. Access via `_task_manager.llm_client` from `get_task_manager()`. **Do NOT create new LLM clients.**

### Agent Execution

`backend/services/agent_runtime.py` `run_agent()` → loads definition + session → builds system prompt → runs LLM loop with tools → persists memories/logs. `TaskManager` (`task_manager.py`) manages async execution + metronome.

### Persistence

- **Filesystem** (`shows/`, `seasons/`, `seances/`): workspace artifacts, specs, YAML configs
- **SQLite DB**: runtime state (corps, agents, sessions, reps, scores, messages)
- V1 API merges both. Corps are DB-only (no more `corps/` in git).

### Lifecycles

Corps: `INITIALIZING → WINTER_CAMPS → ON_TOUR → COMPLETED/DISBANDED`
Rehearsal: `BASICS → SECTIONALS → FULL_ENSEMBLE → RUN_THROUGH`
Shows: `draft → needs_review → approved → published`

Communication hierarchy: ED → PC → Design Staff → Caption Heads → Techs → Performers (enforced).

### Shows, Seasons, Competitions

- Shows: `shows/<slug>/` — status.yaml, design_notes.md, spec.md, show_prompt.md
- Seasons: `seasons/<id>/` — season.yaml, performances/, standings.yaml
- Competitions: virtual (season + show pairs), ID = `{season_id}-{show_slug}`

### Design Room

Two-pane UI at `/design/:showSlug`. Left: chat (routed to roles via `note_router`). Right: artifacts (Brief/Prompt/Versions). Messages flow through `POST /api/v1/design/threads/{slug}/messages`.

---

## Key Files

### Backend
| File | Purpose |
|------|---------|
| `backend/api/app.py` | FastAPI app, WebSocket, lifespan, router inclusions |
| `backend/api/v1/` | 25 domain routers (corps, design, shows, seasons, competitions, etc.) |
| `backend/api/v1/helpers.py` | Shared utilities (`_get_root`, `_validate_id`, `_get_db_session`) |
| `backend/api/v1/schemas.py` | 27 Pydantic request models |
| `backend/services/agent_runtime.py` | Agent execution loop |
| `backend/services/task_manager.py` | Async orchestration, metronome |
| `backend/services/llm_client.py` | LLM abstraction (Claude/ChatGPT/Anthropic/Mock) |
| `backend/services/corps_service.py` | Corps init, lifecycle transitions |
| `backend/services/show_persistence.py` | Show workspace disk I/O |
| `backend/database.py` | SQLAlchemy + Alembic |

### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/services/v1.ts` | Typed V1 API client (**use this, not api.ts**) |
| `frontend/src/pages/DesignRoom.tsx` | Design room orchestrator |
| `frontend/src/pages/CorpsList.tsx` | Corps list + creation |
| `frontend/src/pages/CorpsDetailV2.tsx` | Corps detail + lifecycle |
| `frontend/src/pages/CompetitionsList.tsx` | Competition management |

---

## Common Pitfalls

1. **React hooks** must be called before any early returns
2. **Corps** may be DB-only — always check DB as fallback
3. **SQLAlchemy 2.0**: use `select().where()` not `db.query().filter()` inside `exists()`
4. **API client**: use `v1.ts` only — `api.ts` is fully deprecated
5. **Season IDs** can contain hyphens — competition_id splitting must match against actual season dirs

## Docs

Architecture and schemas live in `docs/`. Key files: `architecture.md`, `domain-glossary.md`, `quality/quality_contract.md`, `api/openapi.md`, `ui/`, `shows/`, `seasons/`, `corps/`, `scoring/`, `pool/`.
