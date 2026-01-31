# DrumSwarmInternational — Architecture Analysis

## SYSTEM MAP

### Directory Structure
```
backend/
  api/app.py              — FastAPI + WebSocket endpoints
  models/                 — SQLAlchemy ORM (16 models)
  services/               — Core orchestration logic (25+ modules)
  tools/                  — Rehearsal tools (metronome, tuner, cleaning, dressing, gock_block)
  prompts/                — Markdown components + YAML manifests per role
  config/                 — Themes, MCP instruments, show templates
  cli/                    — judge.py, drill.py
  tests/                  — 37 test files, pytest + async
frontend/
  src/components/         — 20+ React/TS components (DCI-themed names)
  src/services/api.ts     — REST + WebSocket client
scripts/
  monitoring/             — Tmux dashboard, unified_dashboard.py, swarm_actions.sh
  deployment/             — start_backend.sh, start_frontend.sh
alembic/                  — DB migrations
dci                       — CLI entry point (bash, drill-command verbs)
```

### Role Hierarchy (top → bottom)
```
Executive Director  (Opus)   — decomposes task → MOVEMENTs
Program Coordinator (Sonnet) — MOVEMENTs → SETs → SEGMENTs → REPs
Drum Major          (Sonnet) — monitors progress, escalates blocks

Design Staff        (Sonnet) — Drill Writer, Music Writer, Choreographer
Caption Heads       (Sonnet) — Brass, Percussion, Guard, Visual (cross-cutting)
Techs               (Haiku)  — Brass, Percussion, Front Ensemble, Guard, Visual

Timing Judge        (Haiku)  — health/budget/deadline enforcement
Performers          (ephemeral) — spawn per rep, accumulate trust, age out at 22
```

### Work Decomposition
```
Show → Movement → Set → Segment → Rep
```
Each level has its own status machine. Reps are the atomic work unit:
`PENDING → ASSIGNED → IN_PROGRESS → REVIEW → COMPLETED | FAILED`

### Orchestration Flow
1. User → ED (chat) — clarifies requirements
2. ED creates MOVEMENTs under show root
3. PC decomposes into SETs/SEGMENTs/REPs
4. Handoff chain: ED → PC → Design → Caption Heads → Techs → Performers
5. Escalation chain: reverse direction
6. Merge Monitor: rolls completed children up to parents
7. Metronome: reclaims stale reps (GUPP), respawns dead critical roles

### Corps Lifecycle
```
INITIALIZING → WINTER_CAMPS → ON_TOUR → COMPLETED | DISBANDED
```
Rehearsal modes (auto-advance during WINTER_CAMPS):
```
BASICS → SECTIONALS → FULL_ENSEMBLE → RUN_THROUGH
```

### Key Subsystems
| Subsystem | Files | Purpose |
|---|---|---|
| Agent Runtime | `agent_runtime.py`, `agent_phases.py` | 9-phase agent loop, LLM calls, tool execution |
| Tool System | `tool_executor.py`, `tool_registry_setup.py` | Permission-gated tool registry |
| Messaging | `message_service.py`, `message_bus.py` | Hierarchy-enforced priority queue + pub/sub |
| Memory | `memory_manager.py`, `memory_bank.py`, `file_memory.py` | 3-layer: short-term / ChromaDB semantic / SQL+files |
| Scoring | `scoring_service.py`, `models/score.py`, `models/penalty.py` | Weighted caption scores minus penalties |
| Performers | `performer_service.py`, `lifecycle_manager.py` | Trust scoring, auditions, ageout |
| Prompts | `prompt_arranger.py`, `prompts/` | Component-based prompt assembly with Jinja2 substitution |
| Verification | `verification.py` | Extensible gate chain before rep completion |
| Themes | `config/theme.py`, `config/themes/*.yaml` | Pluggable domain vocabulary (DCI, Ensemble, Gastown) |

---

## INVARIANTS

These must be preserved by any extension:

### Metaphor Invariants
1. Work hierarchy is Show → Movement → Set → Segment → Rep. No new levels, no skipping.
2. Roles map 1:1 to DCI organizational positions. No generic "agent" role.
3. Performers are ephemeral, identity-bearing workers with age (12-22), trust, and experience.
4. Corps is the organizational unit. One corps = one full agent hierarchy for one show.

### Execution Invariants
5. Handoff chain is strict and validated (`HANDOFF_CHAIN` dict). Design never executes; techs never design.
6. Escalation chain is the reverse of handoff. Problems flow up, work flows down.
7. Rep state machine transitions are validated (`VALID_TRANSITIONS`). No shortcuts.
8. GUPP enforcement: stale assigned reps are reclaimed with trust penalty.
9. Merge monitor rolls child completion up to parents automatically.
10. Model tiers are load-bearing: Opus for strategy, Sonnet for coordination, Haiku for execution.

### Lifecycle Invariants
11. Corps status flow: INITIALIZING → WINTER_CAMPS → ON_TOUR → terminal. No backward jumps except ON_TOUR → WINTER_CAMPS.
12. Rehearsal modes auto-advance based on milestone criteria (not time).
13. Performer ageout at 22 is mandatory. Trust < 20 triggers retirement.
14. Self-improvement requires audit trail (SelfImprovementLog). Major changes need approval.

### Architecture Invariants
15. Agent sessions are stateless between runs; continuity via context snapshots + memory bank.
16. All domain operations go through service layer, never direct model mutation from agents.
17. Tool permissions are defined per AgentDefinition; agents cannot acquire tools at runtime.
18. Message hierarchy is enforced — agents can only message roles they're connected to in the chain.
19. Verification gates run before rep COMPLETED transition. Gate chain is extensible but never skippable.

---

## SAFE EXTENSION POINTS

### 1. Persistence & Storage
- **Alembic migrations**: Add columns/tables without touching existing models. Models in `backend/models/` follow established SQLAlchemy patterns.
- **Memory bank**: Add new memory types alongside `session_summary` and `failure_lesson` in `memory_bank.py`. ChromaDB collections are per-agent, isolated.
- **File memory**: Add new file-based state categories in `memory_store/agents/{identity}/`.

### 2. Talent Pool & Performer Mechanics
- **`performer_service.py`**: Extend `audition_for_role()` with new selection criteria (specialization, affinity scores).
- **`lifecycle_manager.py`**: Add new lifecycle events (mid-season evaluations, trades between corps).
- **Trust formula**: Adjustable in `performer_service.py` — current constants are hardcoded, could be config-driven.
- **Performer metadata**: Add columns to Performer model via migration for specialization tracking.

### 3. Scoring & Competition
- **`scoring_service.py`**: Add new JudgeTypes, adjust DEFAULT_WEIGHTS, add score-driven routing rules.
- **Multi-corps competition**: `Corps` model already supports multiple corps per show. Wire up comparative scoring and ranking.
- **Penalty types**: Extend PenaltyType enum and add new automated penalty triggers.
- **Score thresholds**: Currently hardcoded (60 = rework, 40 = escalate). Make configurable per corps or show.

### 4. Lifecycle & Rehearsal
- **Rehearsal mode criteria**: `_check_rehearsal_advancement()` in `corps_service.py` — add new advancement conditions.
- **New lifecycle hooks**: EventBus topics for corps state transitions. Subscribe without modifying core flow.
- **Season transitions**: `conduct_season_transition()` in lifecycle_manager — extend with awards, promotions, etc.

### 5. Design Room & Prompts
- **Prompt components**: Add new `.md` files to `backend/prompts/`, reference from role manifests in `prompts/manifests/`.
- **Manifest variables**: Add new context variables in `prompt_arranger.py` `_build_context()`.
- **Phase guidance**: Extend `agent_phases.py` with new phase-specific instructions without changing the phase enum.
- **Rehearsal mode guidance**: Add mode-specific prompt injections in `corps_service.py` `_get_rehearsal_guidance()`.

### 6. Tools & Verification
- **Tool registry**: Register new tools in `tool_registry_setup.py`. Agents gain access via `tools_allowed` on their definition.
- **Verification gates**: Add new gate functions in `verification.py`, register in `SEGMENT_TYPE_GATES` or per-segment config.
- **Rehearsal tools**: Add new tools in `backend/tools/` following metronome/tuner patterns.

### 7. Events & Monitoring
- **EventBus subscribers**: Add subscribers for any existing topic without touching publishers.
- **Subscription service**: Agents can subscribe to new event patterns.
- **Dashboard views**: Add new views to `unified_dashboard.py` (currently 6 views, numbered 1-6).
- **Metrics collector**: Extend `metrics_collector.py` with new metric types.

### 8. Themes
- **New theme YAML**: Add to `backend/config/themes/` following existing schema. No code changes needed.
- **Theme-specific UI**: `CorpsThemeContext` in frontend supports per-corps visual identity.
