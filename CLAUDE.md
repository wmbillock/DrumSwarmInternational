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

## Quick Reference

### CLI (`./dci <command>`)

`ten-hut` (full stack) · `parade-rest` (shutdown) · `forward-march` (backend) · `company-front` (frontend) · `run-through` (pytest) · `check-step` (health) · `set-the-field` (init) · `drill` (calibration) · `pool` (talent) · `doctor` (diagnose) · `install` (setup) · `swarm` (CLI) · `horns-up` (help)

### Testing

```bash
python -m pytest backend/tests/ -v
python -m pytest backend/tests/test_v1_api.py
cd frontend && npx tsc --noEmit
```

### Installation

```bash
./dci install    # Symlinks skills/agents to ~/.claude/, installs plugins, detects LLMs
```

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

## Known Issues

- 8 pre-existing test failures (competition_scoring, coverage_boost, judging_routes, show_persistence, v1_api)
- `backend.models.scoresheet` does not exist; scoresheet endpoint returns empty data

## Docs

Architecture and schemas live in `docs/`. Key files: `architecture.md`, `domain-glossary.md`, `quality/quality_contract.md`, `api/openapi.md`, `ui/`, `shows/`, `seasons/`, `corps/`, `scoring/`, `pool/`.
