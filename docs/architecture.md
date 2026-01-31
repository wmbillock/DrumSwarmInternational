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

## Scoring / Adjudication
- Judges live at the DCI layer, external to any corps
- Evaluate reps on technique + GE per caption
- Composite score: weighted caption scores minus penalties
- Tiered response: minor issues → automatic rework (another rep); major issues → escalate to ED/user
- Timing official: mechanical enforcement of deadlines and budgets
