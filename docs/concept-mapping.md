# Concept Mapping: DCI, Gas Town, and Ensemble

A comparative analysis for building the DCI Swarm orchestration engine.

---

## 1. Role Mappings: DCI → Gas Town

| DCI Role | Gas Town Role | Fit | Notes |
|---|---|---|---|
| DCI (governing org) | Town (~/.gt/) | Strong | Both are the top-level container that sets rules and coordinates multiple independent units. |
| Named Corps | Rig | Strong | Each is an independent orchestration with its own identity and work. |
| Executive Director | Mayor | Moderate | Both are the top coordinator who escalates to the human. Key difference: Mayor is infrastructure; ED is a decision-maker with creative authority. |
| Program Coordinator | *No analog* | — | Gas Town has no role between Mayor and workers that owns creative delivery. This is the most important role DCI adds. |
| Design Staff | *No analog* | — | Gas Town has no agents that create plans/artifacts but never touch execution. The design/execution separation is entirely absent. |
| Caption Heads | Witness + Refinery (partial) | Weak | Caption heads are domain-expert leaders who translate design into execution. Witnesses monitor health; Refineries handle merge conflicts. Neither teaches or leads a functional domain. The mapping is structural (mid-tier persistent agents), not functional. |
| Techs | Crew (long-lived) | Moderate | Both handle persistent, detail-oriented work under a supervisor, scoped per specialty. |
| Drum Major | *No analog* | — | No Gas Town agent provides a cross-cutting synchronization signal. |
| Caption Leads | *No analog* | — | Leadership-performers (simultaneously supervisors and workers) do not exist in Gas Town. |
| Section Leaders | *No analog* | — | First-line peer correction does not exist. Gas Town relies on Witnesses, not peers. |
| Section Performers | Polecats | Strong | Ephemeral workers. Spawn, do one task, die. No idle state. Cleanest mapping. |
| Crews (operational) | Dogs | Strong | Both handle maintenance/operational duties. |
| *(no analog)* | Deacon | — | Continuous patrol/health monitoring. DCI's correction escalation chain serves a similar function but is not a dedicated role. |
| *(no analog)* | Boot | — | Triage watchdog (checking the checker). No DCI equivalent — DCI trusts its hierarchy. |
| *(no analog)* | Daemon | — | Heartbeat-level liveness. Infrastructure, not a domain role. |

**Key takeaway**: Gas Town is infrastructure-heavy and worker-focused. DCI has a rich middle management layer (PC, Design Staff, Caption Heads) that translates intent into execution. Gas Town skips this layer.

---

## 2. Concept Mappings: DCI → Gas Town

| DCI Concept | Gas Town Concept | Fit | Notes |
|---|---|---|---|
| Show | Convoy | Moderate | Both represent the complete deliverable. But a Show has artistic coherence; a Convoy is a batch tracker. |
| Movement | Molecule | Moderate | Both are durable multi-step units that survive interruptions. |
| Set/Form/Coordinate | Bead | Strong | Both are atomic, persistent work units. A coordinate tells a performer exactly where to be; a bead is an atomic work item. Both survive agent/performer death. |
| Drill (all sets) | Beads (collection) | Moderate | The complete set of beads for a rig is structurally equivalent. |
| Hook | Coordinate (inverted) | Moderate | Both bind a unit of work to a specific agent/performer. |
| Tour (80-day refinement) | *No analog* | — | Gas Town has no bounded refinement cycle. Work is complete-and-move-on. Worth importing. |
| GUPP | Rehearsal discipline | Strong | "If work is on your hook, YOU RUN IT" = performer discipline after material handoff. Cultural alignment. |
| MEOW | Sets/Coordinates | Strong | Both decompose goals into trackable atomic units. |
| NDI | Correction Escalation | Moderate | Both ensure completion despite unreliability, but different failure modes. |
| Mail/Nudge | Communication patterns | Moderate | Gas Town's is asynchronous and prioritized; DCI's is hierarchical and direct. |
| Escalation (severity) | Correction Escalation | Strong | Both are graduated routing. Gas Town escalates by channel; DCI escalates by authority. Merge both. |
| Handoff | Design Handoff | Strong | Both preserve state across boundaries. DCI's is a one-way chain; Gas Town's is session continuation. |
| ZFC | Lane discipline | Strong | "Don't reason about other agents" = "flag problems outside your caption rather than fix them." |
| Swarm | Full Ensemble | Moderate | Both are the ephemeral grouping of all workers on a shared goal. |
| Basics/Sectionals/Ensemble/Run-Through | *No analog* | — | Gas Town has no graduated integration levels. Major DCI contribution. |
| Adjudication/Scoring | *No analog* | — | Gas Town has no external evaluation. Work is done or not. |
| Dual Tempo Sources | *No analog* | — | No redundant synchronization mechanism. |
| Competition | Convoy across rigs | Weak | Competition ranks independent orchestrations. Convoy tracks but doesn't rank. |

---

## 3. Where DCI Improves on Gas Town

### The Middle Management Layer
Gas Town jumps from Mayor to Polecats. DCI inserts Program Coordinator, Design Staff, and Caption Heads. This translation layer is essential for complex tasks where executive intent cannot be directly executed by workers.

### Design/Execution Separation
DCI's rule that designers never interact with performers forces clean handoffs. In agent terms: the planning agent should never directly modify code — it hands plans to a translation layer that converts them into executable tasks.

### Rehearsal Modes as Execution Phases

| Mode | DCI Purpose | Agent Engine Equivalent |
|---|---|---|
| Basics | Validate fundamental technique in isolation | Validate each agent/tool works independently |
| Sectionals | Each caption works its own material | Each functional domain runs independently |
| Full Ensemble | All captions integrate | All domains integrate |
| Run-Through | Complete uninterrupted performance | Full dry run before delivery |

### Cross-Cutting Concerns via the Visual Caption Head
The Visual CH has authority over how all on-field performers march but owns no performers. This is the correct model for cross-cutting quality concerns (code style, security, performance) — authority without ownership.

### Dual Tempo Sources
Two coordination signals (visual/authoritative + auditory/derived) provide redundancy. Agent equivalent: one authoritative state store + one derived event stream.

### Adjudication as Quality Framework
Scoring technique + GE per caption on a 0–100 composite provides quality evaluation along multiple dimensions rather than binary pass/fail.

---

## 4. Where Gas Town Improves on a Naive DCI Mapping

### Ephemeral Workers (Polecats)
A naive DCI mapping would keep all performers alive for the "tour." Gas Town's spawn-work-die pattern is superior for cost control. **Keep the Polecat lifecycle for all leaf-node workers.**

### Git-Backed Persistence (Beads)
All work units must survive agent death. **All work units must be beads.**

### NDI (Nondeterministic Idempotence)
DCI assumes performers show up reliably. Agents can't. **NDI must be first-class.**

### The Refinery
DCI has no merge conflicts (drill writer is single source of truth). Software does. **The Refinery is essential.**

### Health Monitoring Patterns (Daemon → Boot → Deacon)
Gas Town's multi-tier watchdog pattern is robust, but these roles map better to **judges** (DCI-level evaluation, external to the corps) than to internal corps infrastructure. **Reframe as adjudication, not internal monitoring.** See Section 9.

### Priority-Based Mail
DCI communication is synchronous and hierarchical. Gas Town's async mail with priorities better suits agents operating at different speeds. **Use as communication backbone.**

### GUPP as Explicit Policy
DCI's "own your part" is cultural. Gas Town makes it architectural. **Make it enforced, not assumed.**

---

## 5. Where Metaphors Break Down

| Mapping | Why It Breaks | Resolution |
|---|---|---|
| Tour = project lifecycle | A tour refines ONE show. Software evolves requirements. | Use "tour" for a bounded iteration, not the whole project. |
| Performers = agents | Performers are persistent humans who learn. Agents are ephemeral and stateless. | Use Polecat lifecycle; preserve state in beads. |
| Drill writer = planner | Drill writer produces one authoritative plan. Software planning is iterative. | Allow multiple design iterations with PC approval gates. |
| Field = execution environment | A football field is fixed. Execution environments vary. | Don't over-map the physical metaphor. |
| Physical transport (convoy) | Agents don't travel. | Rename or repurpose as deployment/delivery pipeline. |
| Warm-up | Performers need physical prep. | Map to "context warm-up" — loading relevant state before execution. Surprisingly useful. |
| Age restrictions, housing | No agent equivalent. | Drop entirely. |

---

## 6. Ensemble Learnings

### Carry Forward

| Pattern | Why |
|---|---|
| Permission enforcement at tool level | Proven — `can_write_code: false` enforced by tool, not trust |
| Markdown-based agent definitions | Easy to author, version, and modify |
| Budget tiers per role | Design Staff/Caption Heads get Sonnet/Opus; Performers get Haiku |
| Hierarchical spawning with explicit trees | Prevents complexity explosion |
| Activity tracking and observability | Essential for debugging orchestration |

### Discard

| Pattern | Why |
|---|---|
| 23+ agent count | Roles should exist because work requires them, not because the metaphor has them |
| Surface-level metaphor | The metaphor must drive architecture, not just naming |
| Rigid TDD as the only workflow | Process should serve orchestration, not replace it |
| Achievement system | Replace with adjudication that drives behavior |
| No rehearsal/integration concept | Graduated integration was missing entirely |

---

## 7. Orchestration of Orchestrations

| DCI Concept | Engine Concept | Description |
|---|---|---|
| Named Corps | **Corps Instance** | Independent orchestration with its own ED, PC, staff, and performers |
| Competition | **Competition** | Multiple Corps Instances work the same problem independently, scored and ranked |
| DCI | **League** | Top-level system that spawns Corps Instances, sets rules, runs Competitions |
| Judges | **Adjudication** | External evaluation agents scoring technique + GE per caption |
| Composite Score | **Score** | Weighted aggregate of caption scores minus penalties |
| Penalties | **Penalties** | Deductions for rule violations (over-budget, time exceeded, disallowed tools) |
| Finals Week | **Tournament** | Progressive elimination — quarterfinals → semifinals → finals |

This enables competitive solution generation, A/B testing at scale, fault tolerance (if one corps fails, others continue), and progressive quality selection.

---

## 8. Summary: What to Take from Each

**From DCI:**
1. Middle management layer (PC, Design Staff, Caption Heads)
2. Design/execution separation as architectural law
3. Rehearsal modes (basics → sectionals → ensemble → run-through)
4. Cross-cutting Visual Caption Head pattern
5. Dual tempo sources for redundant synchronization
6. Adjudication and scoring framework
7. Orchestration of orchestrations (competition/tournament)
8. Strict material handoff chain
9. Lane discipline with escalation

**From Gas Town:**
1. Ephemeral worker lifecycle (Polecats/GUPP)
2. Git-backed persistent work units (beads)
3. NDI for agent unreliability
4. Refinery for merge conflicts
5. Priority-based mail system
6. Session management and handoff
7. ZFC principle
8. Multi-tier health monitoring → reframed as Judges (external evaluation) + Rehearsal Tools (on-demand and continuous infrastructure)

**From Ensemble:**
1. Permission enforcement at tool level
2. Markdown-based agent definitions
3. Budget tiers per role
4. Hierarchical spawning with explicit spawn trees
5. Activity tracking and observability

---

## 9. Refinement: Infrastructure as Judges and Rehearsal Tools

Gas Town creates agent roles (Deacon, Boot, Daemon, Witness) for infrastructure monitoring. In DCI, these concerns belong to two categories that are **external to the corps**: judges (DCI-level evaluation and enforcement) and rehearsal tools (equipment used by staff and performers).

### Infrastructure Monitors → Judges

Gas Town's health monitoring agents map more naturally to **judges** than to corps roles. Judges are external to any one corps — they work for DCI, they evaluate and enforce, they do not participate in the show.

| Gas Town Agent | DCI Mapping | Rationale |
|---|---|---|
| Deacon (continuous patrol) | Judge on the field | Continuously observing, scoring, providing feedback — not participating |
| Boot (triage watchdog) | Head Judge | Decides whether other judges need attention; meta-evaluation |
| Daemon (heartbeat) | DCI timing official | Mechanical enforcement (is the show running? is it over time?) — not reasoning, just measuring |
| Witness (per-rig stuck detection) | Caption-specific judge | Evaluates one domain (technique or GE) and flags issues within that domain |

Judges produce **scores and penalties** which serve as optimization and improvement targets:

- **Scores** are multi-dimensional (technique + GE per caption), not binary pass/fail
- **Penalties** enforce system-level rules (over-budget, time exceeded, disallowed tools)
- **Score-driven feedback loop** is tiered:
  - Minor score issues (below threshold in a single caption) → **automatic re-work** — triggers another sectional pass or basics block without human intervention
  - Major score issues (below threshold across multiple captions, or systemic) → **escalation to ED/human** for decision on where to focus

This reframes Gas Town's health monitoring from "infrastructure that keeps agents alive" to "evaluation that drives continuous improvement" — which is what DCI judging actually does.

### Infrastructure Tooling → Rehearsal Tools

Gas Town creates agent roles for capabilities that should be **tools, not agents**. In DCI, a metronome is not a person — it's equipment that staff and performers use. Similarly, infrastructure capabilities should be tools that agents invoke, not agents themselves.

| Rehearsal Tool | Nature | Agent Analog | How It Works |
|---|---|---|---|
| **Metronome** | Continuous (background) | Shared clock / coordination heartbeat | Always running during rehearsal. All agents can reference it for synchronization. The "dual tempo source" — authoritative state that keeps everyone aligned. |
| **Tuner** | On-demand (callable) | Validation / lint check | Agents invoke when they need to verify their output is "in tune" — correct, well-formed, meeting standards. |
| **Gock Block** | On-demand (callable) | Isolated timing check | Used to check timing/rhythm of a specific passage in isolation. Agents invoke to verify a specific unit of work meets timing/sequencing requirements. |
| **Dressing the Form** | On-demand (callable) | Alignment / formatting check | Verifying that the output is properly aligned with adjacent work — are the coordinates right relative to neighbors? Agents invoke to check integration with surrounding context. |
| **Cleaning the Drill** | Continuous (background) | Continuous integration / quality sweep | Ongoing process of identifying and correcting small errors across the whole drill. Runs in the background, surfaces issues to the appropriate caption head or tech. |

**Key distinction**: Some tools are continuous (metronome, cleaning) and some are on-demand (tuner, gock block, dressing). This maps to:
- **Background services**: Always running, monitoring, surfacing. Like a metronome click during rehearsal — you don't ask for it, it's always there.
- **Callable tools**: Invoked by agents when needed. Like pulling out a tuner to check a note — you use it, get a result, put it away.
