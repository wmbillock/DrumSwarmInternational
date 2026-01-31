# DCI Swarm — Architecture

## System Layers

### DCI Layer (persistent, cross-corps)
The product. Web UI + API. Manages shows (projects), spawns corps, hosts judges and rehearsal tools. Focused on: "make the swarm perform effectively, correctly, and efficiently."

### Corps Layer (per-show, lives as long as the show)
Full hierarchy: ED → PC → Design Staff → Caption Heads → Techs → Performers. Focused on: "deliver this show following good practices and procedures."

### Performer Layer (ephemeral)
Individual agent sessions. Performers spawn per rep, die when done. Staff agents are longer-lived but session-based with context snapshots for continuity.

## Terminology

| Domain Term | Meaning in Engine |
|---|---|
| **Show** | A project — the complete deliverable |
| **Movement** | A major feature or milestone within a show |
| **Set** | A group of related segments that form a coherent unit (e.g., a module, a component) |
| **Segment** | A specific task or feature to be implemented |
| **Rep** | A single work attempt against a segment or set. The atomic work unit. Multiple reps may be needed to "learn" (complete) a segment. |
| **Corps** | The agent swarm instantiated for a show |
| **Winter Camps** | Planning phase — user talks to ED, clarifies requirements, agents prepare |
| **On Tour** | Execution phase — agents work autonomously, deliver results continuously |
| **Rehearsal Mode** | Graduated integration level: basics → sectionals → full_ensemble → run_through. Auto-progresses as milestones are met. |
| **Score** | Multi-dimensional quality evaluation of a rep or show |
| **Penalty** | Deduction for rule violation |

## Tech Stack
- **Backend**: Python, FastAPI
- **Frontend**: React, TypeScript
- **Database**: SQLite initially, migrate to PostgreSQL when concurrency demands it
- **Testing**: pytest with TDD

## Data Model

### Core Entities
- **Show** — user-created project. Owns one corps.
- **Corps** — the swarm for a show. Owns all agents, reps, and messages.
- **AgentDefinition** — role template. Mutable by techs (tiered: prompt tweaks free, tool permission or model tier changes require caption head approval). Versioned.
- **AgentSession** — a running instance of a definition. Parent/child spawn tree. Context snapshot on completion for warm-up of successors.
- **Segment** — a specific task/feature to be completed. Tree structure: show → movement → set → segment. Status rolls up from children.
- **Rep** — a work attempt against a segment. State machine: pending → assigned → in_progress → review → completed/failed. A segment may require multiple reps.
- **Message** — priority-queued, hierarchy-enforced communication. Types: handoff, escalation, flag, status, directive, feedback. Delivery: direct, role-addressed, or broadcast.
- **Score** — evaluation of a rep or segment. Judge type, 0-100, box 1-5, feedback.
- **Penalty** — rule violation deduction against a corps.

### Key Design Decisions
- Reps and segments are persistent and survive agent death
- Messages are hierarchy-enforced — a performer cannot send a directive, a designer cannot message a performer directly
- AgentDefinitions are versioned with tiered modification permissions
- Performers get context via segment description + parent snapshot, not full conversation replay

## Corps Lifecycle

### Status Flow
`INITIALIZING` → `WINTER_CAMPS` → `ON_TOUR` → `COMPLETED` / `DISBANDED`

- **Winter Camps** (planning): User talks to ED, clarifies requirements. ED designs work tree. Rehearsal modes auto-progress through BASICS → SECTIONALS → FULL_ENSEMBLE → RUN_THROUGH as agents hit milestones.
- **On Tour** (execution): Autonomous execution. Agents work independently, deliver results continuously. Rehearsal mode locked to RUN_THROUGH.

### Rehearsal Mode Auto-Progression
Each mode injects guidance into every agent's system prompt. Advancement criteria:
- **BASICS → SECTIONALS**: ED has created ≥1 movement. Work tree exists.
- **SECTIONALS → FULL_ENSEMBLE**: ≥1 rep created per active caption.
- **FULL_ENSEMBLE → RUN_THROUGH**: Cross-section messages exist, no blocked segments.

Mode-aware dispatch restricts handoffs: BASICS only dispatches ED+PC; SECTIONALS dispatches within sections; FULL_ENSEMBLE+ enables cross-section coordination.

### Activation Flow
Show activate → corps initialized (WINTER_CAMPS/BASICS) → ED designs structure → auto-progression through modes → manual `go_on_tour` when ready.

## Communication
- Priority queue per corps (polling-based with SQLite for v1)
- Strict handoff chain enforced at the messaging layer
- Escalation: Section Leader → Tech → Caption Head → PC → ED → User

### Asynchronous Coordination
Performers are ephemeral — they can't wait for a response from another agent. Three mechanisms handle this:

- **Problem Queue** — when a performer hits an issue it can't resolve, it posts to a persistent queue linked to the segment, then dies. The problem survives the agent. The tech or caption head monitoring that caption reads the queue and acts on it.
- **Subscriptions** — agents subscribe to events on segments or sets they care about. Notifications fire on rep completion, rep failure, problem queue posts, or set completion. No polling required.
- **Merge Monitor** — a persistent corps-level process that manages the queue of completed reps waiting to be integrated. Orders changes correctly, manages branches, handles merge conflicts.

## Rehearsal Tools
**Continuous (background):**
- Metronome — liveness monitor. Polls in-progress reps, checks agent liveness, reclaims stale reps.
- Cleaning — linting/style checks on completed artifacts, flags issues to caption heads.

**On-demand (callable by agents):**
- Tuner — validation (types, tests, schema)
- Gock Block — isolated timing/performance check
- Dressing — alignment with adjacent/related work

Permission-gated per agent definition.

## Agent Classification

Every agent definition has a `classification` from one of five categories:

| Classification | Description | Example Roles |
|---|---|---|
| `performing_member` | Ephemeral workers (performers) | performer |
| `instructional_staff` | Domain experts who translate design to execution | drill_writer, music_writer, choreographer, caption heads |
| `administrative_staff` | Management and coordination | executive_director, program_coordinator, drum_major |
| `logistics` | Operational and infrastructure support | brass_tech, percussion_tech, guard_tech, visual_tech |
| `dci_assigned` | External evaluation (judges) | timing_judge |

Classifications are assigned automatically from the `ROLE_CLASSIFICATIONS` mapping when agents are initialized.

## Corps Identity

Each corps has a visual identity:

- **theme_id** — One of 17 predefined color themes (e.g. "phantom-regiment", "blue-devils", "kilties")
- **mascot** — Auto-generated unique mascot name (e.g. "The Crimson Hawks")
- **uniform_concept** — Optional text description of the corps' visual concept

Themes are assigned randomly at corps creation (avoiding duplicates across active corps) and can be updated via the API.

## Performer Lifecycle

Performers have a simulated age system inspired by DCI eligibility rules:

- **Age range**: 12–22 (DCI performing member age limits)
- **Ageouts**: When a performer's age exceeds 22, they are automatically retired
- **Experience seasons**: Incremented each season transition, tracks total experience
- **Auditions**: New performers selected by trust score for available roles
- **Season transitions**: End-of-season process that ages all performers, records experience, and retires ageouts

Staff lifecycle is managed separately via hire/fire operations on agent definitions.

## Self-Improvement

Agents can propose changes to their own definitions, subject to approval:

1. **Propose**: Agent creates a `SelfImprovementLog` entry with proposed changes (e.g. updated system prompt, new tool permissions)
2. **Review**: Entry sits in `PENDING` status until a supervisor reviews it
3. **Approve/Reject**: Supervisor approves (applying changes and bumping version) or rejects

All self-improvement operations are audit-logged with the old/new version, changes, reason, and approver.

## Memory System

Three-layer architecture for agent memory:

### Layer 1: Short-term (in-process)
Handled by `agent_runtime` — conversation context within a single session. Dies with the session.

### Layer 2: Semantic (ChromaDB)
Similarity-based retrieval via `memory_bank`. Stores task+result summaries for fuzzy matching against future tasks. Optional — degrades gracefully if ChromaDB is unavailable.

### Layer 3: Episodic/Structured (SQL + Files)
Two complementary stores:

- **AgentMemory** (SQL): Explicit, typed memories (decisions, profiles, summaries, preferences, lessons). Versioned with superseding. Confidence-scored. Queryable by type.
- **TaskMemory** (SQL): Episodic records of task executions — tool calls, outcomes, success/failure. Indexed by task hash for exact-match retrieval.
- **FileMemory** (filesystem): Human-inspectable state in `memory_store/agents/{identity}/` — JSON profiles, markdown session summaries, JSON decision records. Version-controllable via git.

### Key Principles
- Store summaries, not raw transcripts
- Memory is explicit, inspectable, and editable (by humans and agents)
- The system decides what memory structures exist, not the agent
- Separate long-term knowledge from scratchpad/working memory

## Scoring / Adjudication
- Judges live at the DCI layer, external to any corps
- Evaluate reps on technique + GE per caption
- Composite score: weighted caption scores minus penalties
- Tiered response: minor issues → automatic rework (another rep); major issues → escalate to ED/user
- Timing official: mechanical enforcement of deadlines and budgets

### Judge Monitoring CLI

The judge monitoring system provides real-time health observation via `backend/cli/judge.py`:

- `health` — Analyze corps health (segment status, agent activity, stale reps)
- `list-issues` — List active issues and problems across segments
- `escalate` — Trigger escalation for a specific segment or problem
- `segment` — Inspect segment tree and rep status

Supporting services:
- **`health_monitor.py`** — `analyze_corps_health()`, `get_segment_health()` for programmatic health checks
- **`judge_dashboard.py`** — Real-time ASCII dashboard visualization for judge monitoring
- **`examples/judge_monitoring_example.py`** — Complete workflow examples
