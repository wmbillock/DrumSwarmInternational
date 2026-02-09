# DCI Swarm — System Upgrade Plan

**Date:** 2026-02-09
**Codename:** Willow
**Scope:** Three major initiatives + prerequisite stabilization

---

## Table of Contents

1. [Phase 0: Stabilization (prerequisites)](#phase-0-stabilization)
2. [Phase 1: Drill Books — Persistent Resumable Work Units](#phase-1-drill-books)
3. [Phase 2: Corps as Comparative Experiment Platforms](#phase-2-corps-experiments)
4. [Phase 3: Local Image Generation Pipeline](#phase-3-image-generation)
5. [State Machine Definitions](#state-machine-definitions)
6. [Action Vocabulary](#action-vocabulary)
7. [User Setup Instructions (Windows/Local)](#user-setup)

---

## Phase 0: Stabilization

Before building new systems, fix the foundation.

### 0.1 Fix Test Suite Hangs

**Problem:** Tests that create `TestClient(app)` trigger the FastAPI lifespan, which calls `build_llm_client()` (probes for CLI binaries) and `start_metronome()` (background async loop). These hang or never terminate in the test context.

**Files affected:**
- `test_competition_scoring.py` (hangs at ~18%)
- `test_v1_api.py`, `test_design_room.py`, `test_design_room_v2.py`
- `test_coverage_boost.py`, `test_scoresheet_and_context.py`
- `test_seance_routes.py`, `test_workspace_routes.py`
- `test_agents_overview.py`, `test_api.py`, `test_corps_history_v2.py`

**Fix:** Create a `conftest.py` fixture that patches the lifespan for test mode:
1. Add `DCI_TEST_MODE=1` env var check in `app.py` lifespan
2. When test mode: skip `build_llm_client()` (use `MockLLMClient`), skip `start_metronome()`, skip `seed_founding_corps()`
3. Alternatively: create a `create_test_app()` factory that returns an app with a no-op lifespan
4. Update all TestClient-using tests to use the test app fixture

**Acceptance:** `python -m pytest backend/tests/ -v` runs to completion (no hangs), all non-broken tests pass.

### 0.2 Fix Pre-existing Test Failures (8 tests)

**Files:** `test_competition_scoring`, `test_coverage_boost`, `test_judging_routes`, `test_show_persistence`, `test_v1_api`

**Approach:** Fix each individually after the hang issue is resolved — most are likely caused by the same lifespan/import issues or missing model attributes.

### 0.3 Fix season_persistence.py Syntax Error

**Status:** DONE on this branch. Escaped f-string `f\"{...}\"` → `f"{...}"` on line 192.

---

## Phase 1: Drill Books — Persistent Resumable Work Units

### 1.1 Concept

A **drill book** is a serializable, persistent object representing a unit of work from inception to verified completion. It is the single source of truth for "where are we" — not agent memory, not session context.

Key properties:
- **Persistent:** survives agent session death, context loss, system restarts
- **Resumable:** a new agent session picks up the book cold and continues
- **Hierarchical:** parent books spawn child books; child completion rolls up
- **Auditable:** every step links to evidence (diffs, output, evaluations)
- **Typed:** each step is a concrete action from the action vocabulary
- **Dual-scoped:** books exist per-task AND per-role (agent gets a book matching its role)

### 1.2 Data Model

#### DrillBook (SQLAlchemy model)

```python
class DrillBook(Base):
    __tablename__ = "drill_books"

    id = Column(String(36), primary_key=True, default=uuid4_str)
    parent_id = Column(String(36), ForeignKey("drill_books.id"), nullable=True)
    corps_id = Column(String(36), ForeignKey("corps.id"), nullable=True)
    assigned_performer_id = Column(String(36), ForeignKey("performers.id"), nullable=True)
    assigned_role = Column(String(50))  # e.g. "brass_tech", "percussion_caption_head"

    title = Column(String(255), nullable=False)
    description = Column(Text)
    book_type = Column(String(20))  # "linear", "branching", "dag"
    status = Column(String(20), default="pending")
    # pending → assigned → in_progress → blocked → completed → verified | failed | abandoned

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, onupdate=utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Context for cold pickup
    context_summary = Column(Text)  # Human-readable summary of current state
    context_snapshot = Column(JSON)  # Structured snapshot for agent consumption

    # Relationships
    steps = relationship("DrillStep", back_populates="book", order_by="DrillStep.sequence")
    children = relationship("DrillBook", backref=backref("parent", remote_side=[id]))
    evidence = relationship("DrillEvidence", back_populates="book")
```

#### DrillStep

```python
class DrillStep(Base):
    __tablename__ = "drill_steps"

    id = Column(String(36), primary_key=True, default=uuid4_str)
    book_id = Column(String(36), ForeignKey("drill_books.id"), nullable=False)
    sequence = Column(Integer)  # ordering within the book
    action_type = Column(String(50), nullable=False)  # from ActionType enum
    description = Column(String(500))
    status = Column(String(20), default="pending")
    # pending → in_progress → completed → verified | failed | skipped

    # DAG/branching support
    depends_on = Column(JSON)  # list of step IDs this depends on
    next_steps = Column(JSON)  # conditional next steps: {"on_success": [...], "on_failure": [...]}

    # Execution tracking
    assigned_session_id = Column(String(36), ForeignKey("agent_sessions.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON)  # structured output from the action
    error = Column(Text, nullable=True)

    # Relationships
    book = relationship("DrillBook", back_populates="steps")
    evidence_items = relationship("DrillEvidence", back_populates="step")
```

#### DrillEvidence

```python
class DrillEvidence(Base):
    __tablename__ = "drill_evidence"

    id = Column(String(36), primary_key=True, default=uuid4_str)
    book_id = Column(String(36), ForeignKey("drill_books.id"), nullable=False)
    step_id = Column(String(36), ForeignKey("drill_steps.id"), nullable=True)
    evidence_type = Column(String(30))
    # "file_diff", "command_output", "test_result", "evaluation", "screenshot", "generated_image"

    content = Column(Text)  # inline content or file path reference
    metadata = Column(JSON)  # file paths, line numbers, timestamps, etc.
    created_at = Column(DateTime, default=utcnow)

    book = relationship("DrillBook", back_populates="evidence")
    step = relationship("DrillStep", back_populates="evidence_items")
```

### 1.3 Vector Store / RAG Layer

**Architecture:**
- **ChromaDB** (already a dependency) for semantic memory
- Two collections:
  - `swarm_memory` — institutional knowledge, lessons learned, prior work patterns
  - `drill_book_context` — embeddings of drill book summaries, evidence, outcomes
- **RAG tool** available to agents as `RECALL_MEMORY` / `SEARCH_PRIOR_WORK` actions

**Implementation:**
1. `backend/services/vector_store.py` — ChromaDB client wrapper
   - `store_memory(collection, text, metadata)` — embed and store
   - `search_memory(collection, query, top_k)` — semantic search
   - `store_drill_context(book_id, summary, outcome)` — index completed books
2. `backend/tools/memory_tool.py` — agent-callable tool
   - `recall(query)` — search swarm memory for relevant prior work
   - `learn(insight)` — store a new lesson/pattern
3. On drill book completion: auto-index the book summary + evidence into `drill_book_context`
4. On agent session start: pre-load relevant memories via RAG query on the assigned drill book

### 1.4 Drill Book Service

`backend/services/drill_book_service.py`:

```
create_book(title, description, book_type, parent_id?, corps_id?, role?) → DrillBook
add_step(book_id, action_type, description, depends_on?) → DrillStep
assign_book(book_id, performer_id, session_id) → DrillBook
start_step(step_id, session_id) → DrillStep
complete_step(step_id, result, evidence?) → DrillStep
fail_step(step_id, error) → DrillStep
complete_book(book_id) → DrillBook  # only if all steps completed/verified
abandon_book(book_id, reason) → DrillBook
get_next_steps(book_id) → list[DrillStep]  # DAG-aware: returns steps with all deps met
get_resumption_context(book_id) → dict  # everything a new agent needs to pick up
spawn_child_book(parent_id, title, role, steps) → DrillBook
```

### 1.5 Agent Integration

When an agent session starts:
1. Check for pending/in-progress drill books matching the agent's role
2. If found: load the book's resumption context into the system prompt
3. If not found: the parent agent creates a child drill book for this agent
4. Agent executes steps, recording evidence for each
5. On session death: book remains in current state; next agent picks it up
6. On book completion: evidence chain verified, book marked complete, indexed in vector store

### 1.6 Files to Create/Modify

**New files:**
- `backend/models/drill_book.py` — DrillBook, DrillStep, DrillEvidence models
- `backend/services/drill_book_service.py` — CRUD + state machine logic
- `backend/services/vector_store.py` — ChromaDB wrapper
- `backend/tools/memory_tool.py` — agent RAG tool
- `backend/api/v1/drill_books.py` — REST endpoints
- `backend/tests/test_drill_books.py` — unit tests
- `alembic/versions/xxx_add_drill_books.py` — migration

**Modified files:**
- `backend/models/__init__.py` — register new models
- `backend/services/agent_runtime.py` — drill book context injection on session start
- `backend/services/task_manager.py` — drill book assignment on agent spawn
- `backend/tools/__init__.py` — register memory tool
- `backend/api/v1/router.py` — mount drill_books router

---

## Phase 2: Corps as Comparative Experiment Platforms

### 2.1 Concept

Each corps gets a locked-in configuration of LLM provider + development methodology + coding style. Running the same show across multiple corps produces comparative data. The competition scoring system naturally ranks outcomes.

### 2.2 Corps Configuration Model

Extend the existing `Corps` model:

```python
# New columns on corps table (or a new corps_config table)
class CorpsConfig(Base):
    __tablename__ = "corps_configs"

    corps_id = Column(String(36), ForeignKey("corps.id"), primary_key=True)

    # LLM Provider
    llm_provider = Column(String(30))
    # "claude", "openai", "ollama-local", "gemini", "mixed"
    llm_model_override = Column(String(100), nullable=True)
    # e.g. "gpt-4o", "claude-sonnet-4-5", "llama3.1:70b"

    # Development Methodology
    methodology = Column(String(30))
    # "tdd", "bdd", "xp", "scrum", "kanban", "waterfall", "mob", "pair"

    # Architecture Style
    architecture_style = Column(String(30))
    # "mvc", "mvvm", "clean", "hexagonal", "microservices", "monolith", "event_driven"

    # Coding Style
    naming_convention = Column(String(20))  # "snake_case", "camelCase", "PascalCase"
    comment_style = Column(String(20))  # "minimal", "moderate", "verbose", "docstring_heavy"
    test_philosophy = Column(String(20))  # "unit_first", "integration_first", "e2e_first", "no_tests"

    # Cosmetic / Identity
    color_primary = Column(String(7))  # hex color
    color_secondary = Column(String(7))
    personality_traits = Column(JSON)  # ["aggressive", "methodical", "creative", ...]

    # Training / Evolution
    training_score = Column(Float, default=50.0)  # evolves through feedback
    methodology_effectiveness = Column(JSON)  # per-task-type scores
    provider_reliability = Column(JSON)  # track failures/timeouts per provider
```

### 2.3 LLM Provider Routing

Modify `backend/services/llm_client.py`:

1. Add `CorpsAwareLLMRouter` that wraps the existing `SmartRouter`
2. When an agent session has a `corps_id`, look up that corps' `llm_provider` config
3. Route the request to the configured provider instead of the default priority chain
4. Fall back to the default chain if the configured provider is unavailable
5. Track success/failure/latency per-provider per-corps for comparative data

```python
class CorpsAwareLLMRouter(LLMClient):
    def __init__(self, default_router: SmartRouter, db_session_factory):
        self.default = default_router
        self.db_factory = db_session_factory

    def chat(self, messages, corps_id=None, **kwargs):
        if corps_id:
            config = self._get_corps_config(corps_id)
            if config and config.llm_provider:
                # Route to specific provider
                provider = self.default.get_provider(config.llm_provider)
                if provider:
                    return provider.chat(messages, **kwargs)
        return self.default.chat(messages, **kwargs)
```

### 2.4 Methodology Enforcement

Each methodology maps to constraints on the drill book step ordering:

| Methodology | Constraint |
|---|---|
| `tdd` | `WRITE_TEST` must precede `WRITE_FILE` for any implementation |
| `bdd` | `DESIGN_ACCEPTANCE_CRITERIA` before any implementation |
| `waterfall` | Strict phase gates: `DESIGN_*` → `WRITE_*` → `RUN_TEST` → `VERIFY` |
| `xp` | Pair steps: every `WRITE_FILE` accompanied by `REVIEW_CODE` |
| `scrum` | Sprint planning step required; work batched into sprint-sized chunks |
| `kanban` | WIP limits on in-progress steps (configurable) |

Enforcement lives in `drill_book_service.py` — when a step is started, validate it against the corps methodology constraints.

### 2.5 Comparative Data Collection

New model for experiment tracking:

```python
class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id = Column(String(36), primary_key=True, default=uuid4_str)
    competition_id = Column(String(100))
    corps_id = Column(String(36), ForeignKey("corps.id"))
    show_slug = Column(String(100))
    season_id = Column(String(100))

    # Corps config snapshot at time of competition
    llm_provider = Column(String(30))
    methodology = Column(String(30))
    architecture_style = Column(String(30))

    # Results
    final_score = Column(Float)
    caption_scores = Column(JSON)
    time_to_complete_seconds = Column(Integer)
    total_llm_calls = Column(Integer)
    total_tokens_used = Column(Integer)
    total_steps_completed = Column(Integer)
    total_steps_failed = Column(Integer)
    test_pass_rate = Column(Float, nullable=True)

    # Drill book reference
    drill_book_id = Column(String(36), ForeignKey("drill_books.id"), nullable=True)

    created_at = Column(DateTime, default=utcnow)
```

Query examples:
- "Average score by LLM provider across all shows"
- "TDD vs waterfall on code_review shows"
- "OpenAI failure rate vs Claude failure rate on complex tasks"
- "Which methodology + provider combo has the best test pass rate?"

### 2.6 Founding Corps Config Assignments

Update `data/founding_corps/` YAML files with config blocks. Example spread:

| Corps | LLM | Methodology | Architecture |
|---|---|---|---|
| The Quiet Trumpets | Claude | TDD | Clean Architecture |
| The Arrhythmic Drumline | OpenAI | Scrum | MVC |
| The Dropless Color Guard | Ollama (local) | XP | Hexagonal |
| Corps Is Stored In The Lips | Claude | Waterfall | Monolith |
| All Your Beats Are Belong To Us | OpenAI | Kanban | Microservices |
| The Backfield Flagboxes | Gemini | BDD | MVVM |
| We Only March Baris | Claude | Mob Programming | Event-Driven |
| Pit Happens | OpenAI | Pair Programming | Clean Architecture |
| Sabre Rattling | Ollama (local) | TDD | MVC |
| The Accidental Crescendo | Mixed | Scrum | Hexagonal |
| Several Loud Rimshots | Claude | XP | MVVM |
| Toss And Pray | OpenAI | Kanban | Monolith |

### 2.7 Files to Create/Modify

**New files:**
- `backend/models/corps_config.py`
- `backend/models/experiment_result.py`
- `backend/services/corps_config_service.py`
- `backend/services/experiment_tracker.py`
- `backend/api/v1/experiments.py`
- `backend/tests/test_corps_config.py`
- `backend/tests/test_experiment_tracker.py`
- `alembic/versions/xxx_add_corps_config.py`

**Modified files:**
- `backend/services/llm_client.py` — add CorpsAwareLLMRouter
- `backend/services/corps_seeder.py` — seed configs from YAML
- `backend/services/drill_book_service.py` — methodology enforcement
- `backend/services/scoring_persistence.py` — record experiment results after competition
- `data/founding_corps/*.yaml` — add config blocks
- Frontend: new comparative dashboard page

---

## Phase 3: Local Image Generation Pipeline

### 3.1 Architecture

```
Agent (GENERATE_IMAGE action)
  → backend/tools/image_generator.py
    → POST workflow JSON to ComfyUI API (http://localhost:8188/prompt)
    → Poll /history/{prompt_id} for completion
    → Download result from /view?filename=...
    → Return local image path + metadata
```

### 3.2 ComfyUI Connector

`backend/tools/image_generator.py`:

```python
class ComfyUIConnector:
    def __init__(self, base_url="http://localhost:8188"):
        self.base_url = base_url

    def generate(self, prompt, negative_prompt="", model="sd3.5_medium",
                 width=1024, height=1024, steps=20, cfg_scale=7.0,
                 seed=-1) -> ImageResult:
        """Submit a generation job and wait for result."""
        workflow = self._build_workflow(prompt, negative_prompt, model,
                                        width, height, steps, cfg_scale, seed)
        prompt_id = self._queue_prompt(workflow)
        result = self._poll_completion(prompt_id)
        image_path = self._download_image(result)
        return ImageResult(path=image_path, prompt_id=prompt_id, metadata=result)

    def _build_workflow(self, ...):
        """Build ComfyUI workflow JSON from parameters."""
        # Workflow is a node graph serialized as JSON
        # Template-based: load from backend/config/comfyui_workflows/
        ...

    def _queue_prompt(self, workflow):
        """POST to /prompt, return prompt_id."""
        r = httpx.post(f"{self.base_url}/prompt", json={"prompt": workflow})
        return r.json()["prompt_id"]

    def _poll_completion(self, prompt_id, timeout=120):
        """Poll /history/{prompt_id} until done."""
        ...

    def _download_image(self, history_entry):
        """GET /view?filename=... and save locally."""
        ...

    def health_check(self):
        """GET /system_stats — verify ComfyUI is reachable."""
        ...
```

### 3.3 Workflow Templates

Store in `backend/config/comfyui_workflows/`:

- `text2img_sd35.json` — SD 3.5 Medium, general purpose
- `text2img_sd35_turbo.json` — SD 3.5 Large Turbo, fast drafts
- `text2img_sdxl.json` — SDXL 1.0 Base
- `text2img_flux.json` — FLUX.1 Kontext (high quality, slower)
- `text2img_realistic.json` — Realistic Vision V5.1

Each template is a complete ComfyUI workflow JSON with placeholder values for prompt, seed, dimensions, steps.

### 3.4 Agent Tool Registration

```python
# In backend/tools/__init__.py
def create_tool_registry():
    registry = ToolRegistry()
    # ... existing tools ...
    registry.register("generate_image", image_generator_tool,
                      schema={...}, description="Generate an image from a text prompt")
    return registry
```

Agent action type: `GENERATE_IMAGE` in the drill book vocabulary.

### 3.5 Model Recommendations for RTX 5080 (16GB VRAM)

| Model | Use Case | VRAM | Speed | Quality |
|---|---|---|---|---|
| SD 3.5 Medium | **Default.** Best all-rounder | ~8GB | Fast | High |
| SD 3.5 Large Turbo | Fast iterations, drafts | ~10GB | Very fast (fewer steps) | Good |
| SDXL 1.0 Base | Proven, huge ecosystem | ~7GB | Fast | Good |
| FLUX.1 Kontext | Best quality, image editing | ~12GB fp16 | Slow | Excellent |
| Realistic Vision V5.1 | Photorealistic images | ~4GB | Fast | Good (photos) |
| Dreamshaper 8 | Creative/artistic | ~4GB | Fast | Good (art) |
| epicrealismXL | Photorealistic XL | ~7GB | Fast | Good (photos) |

All models are already installed in SwarmUI. No additional downloads needed.

### 3.6 Files to Create

**New files:**
- `backend/tools/image_generator.py` — ComfyUI connector + agent tool
- `backend/config/comfyui_workflows/` — workflow JSON templates (one per model)
- `backend/services/image_service.py` — higher-level image gen service
- `backend/api/v1/images.py` — REST endpoints for image generation/history
- `backend/tests/test_image_generator.py` — tests (mock ComfyUI API)

**Modified files:**
- `backend/tools/__init__.py` — register image tool
- `backend/config/` — add `comfyui.yaml` with connection settings
- `pyproject.toml` — add `httpx` to core deps if not already present (it is)

### 3.7 Environment Variable

```
COMFYUI_URL=http://localhost:8188  # default
```

---

## State Machine Definitions

### Corps Lifecycle

```
INITIALIZING
  → WINTER_CAMPS        [on: seed complete, staff hired]
WINTER_CAMPS
  → ON_TOUR             [on: season starts, performers drafted]
  → DISBANDED           [on: user/system dissolve]
ON_TOUR
  → COMPLETED           [on: season ends normally]
  → DISBANDED           [on: user/system dissolve]
COMPLETED
  → WINTER_CAMPS        [on: new season announced]
  → DISBANDED           [on: user/system dissolve]
```

### Rehearsal Mode

```
BASICS
  → SECTIONALS          [on: basics proficiency met]
SECTIONALS
  → FULL_ENSEMBLE       [on: all sections proficient]
FULL_ENSEMBLE
  → RUN_THROUGH         [on: ensemble ready]
RUN_THROUGH
  → BASICS              [on: reset / new show]
```

### Show Status

```
draft
  → needs_review        [on: spec written + linted]
needs_review
  → approved            [on: review passes]
  → draft               [on: review fails, needs revision]
approved
  → published           [on: assigned to season/competition]
  → draft               [on: retracted for revision]
published
  → (terminal)
```

### Drill Book Status

```
pending
  → assigned            [on: performer/agent assigned]
assigned
  → in_progress         [on: first step started]
in_progress
  → blocked             [on: step fails with blocking error OR dependency unmet]
  → completed           [on: all steps completed]
  → abandoned           [on: user/system cancels]
blocked
  → in_progress         [on: blocker resolved]
  → abandoned           [on: user/system cancels]
completed
  → verified            [on: evidence audit passes]
  → in_progress         [on: verification fails, rework needed]
verified
  → (terminal)
abandoned
  → (terminal)
failed
  → (terminal)
```

### Drill Step Status

```
pending
  → in_progress         [on: agent starts step]
in_progress
  → completed           [on: action succeeds, evidence recorded]
  → failed              [on: action fails]
  → skipped             [on: step no longer relevant]
completed
  → verified            [on: evidence reviewed]
failed
  → in_progress         [on: retry]
  → skipped             [on: abandoned]
skipped
  → (terminal)
verified
  → (terminal)
```

### Staff Lifecycle

```
HIRED
  → ACTIVE              [on: corps initialization complete]
ACTIVE
  → SUSPENDED           [on: poor performance / system automated]
  → FIRED               [on: replacement hired / system automated / user action]
SUSPENDED
  → ACTIVE              [on: reinstatement after review]
  → FIRED               [on: suspension review fails]
FIRED
  → (terminal, returns to pool if applicable)
```

### Performer Lifecycle

```
POOLED
  → DRAFTED             [on: corps selects from talent pool]
DRAFTED
  → ONBOARDED           [on: assigned to corps, receives drill book]
ONBOARDED
  → PERFORMING          [on: first drill book step started]
PERFORMING
  → SEASON_END          [on: season completes]
  → RELEASED            [on: cut by corps mid-season]
SEASON_END
  → REFLECTING          [on: mechanical score assigned]
RELEASED
  → REFLECTING          [on: mechanical score assigned]
REFLECTING
  → POOLED              [on: self-improvement LLM evaluation complete]
```

**Reflecting phase detail:**
1. Mechanical score assigned based on: drill book completion rate, evidence quality, competition scores, error rate
2. LLM evaluation call: agent reflects on its own drill book evidence chain — what worked, what didn't, what to change
3. Capability scores updated in talent pool ledger
4. Agent returns to pool with updated profile

### Performer Minting

When a corps needs a performer and the pool is insufficient:
1. Corps hierarchy (caption head or above) defines the need: instrument/role, skill requirements
2. System creates a new performer with base capability profile for that instrument
3. No history, no reputation, no prior drill books — raw recruit
4. Immediately enters the draft pool and competes with experienced performers
5. Corps' draft picks are based on reputation + capability scores, so experienced agents are preferred

### Corps Size Tiers

| Tier | Staff | Performers per Section | Total Performers |
|---|---|---|---|
| Small | ED + PC + 1 caption head | 1-2 | 4-8 |
| Medium | ED + PC + 3 caption heads + 2 techs | 2-3 | 10-18 |
| Large | ED + PC + 5 caption heads + 5 techs + drum major | 3-5 | 20-35 |

Staff is always present (roles exist even if agents rotate). Performer count per section scales with tier.

---

## Action Vocabulary

Typed actions that agents can perform. Each maps to a drill book step type.

### File Operations

| Action | Description | Roles |
|---|---|---|
| `READ_FILE` | Read a file for analysis | All |
| `WRITE_FILE` | Create or overwrite a file | Tier 2-3 |
| `EDIT_FILE` | Modify specific sections of a file | Tier 2-3 |
| `DELETE_FILE` | Remove a file | Tier 2 only |
| `MOVE_FILE` | Rename/move a file | Tier 2 only |

### Execution

| Action | Description | Roles |
|---|---|---|
| `RUN_COMMAND` | Execute a shell command | Tier 2-3 |
| `RUN_TEST` | Execute test suite | Tier 2-3 |
| `RUN_BUILD` | Build/compile the project | Tier 2-3 |
| `RUN_LINT` | Run linter/formatter | Tier 2-3 |

### Design & Architecture

| Action | Description | Roles |
|---|---|---|
| `DESIGN_APPROACH` | Decide high-level approach for a task | Tier 1-2 |
| `DESIGN_ARCHITECTURE` | Define system/component architecture | Tier 1-2 |
| `DESIGN_INTERFACE` | Define API/interface contracts | Tier 2 |
| `DESIGN_ACCEPTANCE_CRITERIA` | Define acceptance/done criteria | Tier 1-2 |
| `DESIGN_DATA_MODEL` | Define data structures/schemas | Tier 2 |
| `WRITE_SPEC` | Write a specification document | Tier 1-2 |

### Evaluation & Review

| Action | Description | Roles |
|---|---|---|
| `EVALUATE_PROMPT` | Analyze/critique a prompt or instruction | All |
| `REVIEW_CODE` | Review code for correctness/style | Tier 2-3 |
| `REVIEW_DESIGN` | Review architectural/design decisions | Tier 1-2 |
| `VERIFY_RESULT` | Verify a step's output meets criteria | Tier 2 |
| `JUDGE_SCORE` | Assign a score with rubric | Judges only |

### Communication

| Action | Description | Roles |
|---|---|---|
| `DELEGATE_TASK` | Assign work to a subordinate (creates child drill book) | Tier 1-2 |
| `REPORT_STATUS` | Report progress to superior | All |
| `REQUEST_CLARIFICATION` | Ask for clarification from superior or user | All |
| `ESCALATE_ISSUE` | Flag a problem to the next level up | All |

### Memory & Research

| Action | Description | Roles |
|---|---|---|
| `RECALL_MEMORY` | Search vector store for relevant prior work | All |
| `SEARCH_PRIOR_WORK` | Search drill book history for similar tasks | All |
| `LEARN` | Store a new insight in swarm memory | All |
| `SEARCH_CODEBASE` | Search code for patterns/references | All |

### Generation

| Action | Description | Roles |
|---|---|---|
| `GENERATE_IMAGE` | Generate an image via ComfyUI | Tier 2-3 (with image tool) |
| `GENERATE_DOCUMENT` | Generate a document from template | Tier 2-3 |

### Lifecycle

| Action | Description | Roles |
|---|---|---|
| `ASSIGN_PERFORMER` | Assign a performer to a drill book | Tier 2 |
| `RELEASE_PERFORMER` | Release a performer back to pool | Tier 2 |
| `MINT_PERFORMER` | Create a new performer when pool is insufficient | Tier 1-2 |

---

## User Setup Instructions (Windows/Local)

### ComfyUI Configuration

1. **Change ComfyUI port to 8188** (avoid conflict with DCI backend on 8000):
   - Open ComfyUI → Settings → Server-Config → Network
   - Set Port to `8188`
   - Restart ComfyUI

2. **Enable CORS** (so our backend can call ComfyUI):
   - In the same Server-Config → Network section
   - Set "Enable CORS header" to `*`

3. **Verify ComfyUI is reachable:**
   ```powershell
   curl http://127.0.0.1:8188/system_stats
   ```
   Should return JSON with CUDA device info and VRAM stats.

4. **SwarmUI** can stay on port 7801 for manual use. It won't conflict. Our swarm agents will talk to ComfyUI directly (port 8188), not through SwarmUI.

### Model Recommendations (already installed)

Your installed models are sufficient. Recommended defaults:
- **General purpose:** SD 3.5 Medium (`sd3.5_medium.safetensors`)
- **Fast drafts:** SD 3.5 Large Turbo (`sd35_large_turbo.safetensors`)
- **High quality:** FLUX.1 Kontext Dev (`flux1-kontext-dev.safetensors`)

No additional model downloads needed to start.

### If You Want to Add Models Later

```powershell
# Install HF CLI (if not already)
pip install huggingface-hub

# Example: download FLUX.1 Schnell (faster FLUX variant)
huggingface-cli download black-forest-labs/FLUX.1-schnell flux1-schnell.safetensors --local-dir C:\Users\evils\Downloads\SwarmUI\Models\OfficialStableDiffusion

# Example: download SD 3.5 Large (full, non-turbo)
huggingface-cli download stabilityai/stable-diffusion-3.5-large sd3.5_large.safetensors --local-dir C:\Users\evils\Downloads\SwarmUI\Models\OfficialStableDiffusion
```

### Running DCI Locally (instead of sandbox)

```powershell
# Clone and enter repo
git clone <repo-url>
cd DrumSwarmInternational
git checkout claude/setup-local-development-ClHf8

# Python setup
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install -e ".[dev]"

# Frontend
cd frontend && npm install && cd ..

# Init DB
python -c "from backend.database import create_db_engine, init_db, Base; import backend.models; engine = create_db_engine(); init_db(engine)"

# Start backend (different terminal)
uvicorn backend.api.app:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (different terminal)
cd frontend && npx vite

# Verify
curl http://localhost:8000/api/v1/system/health
curl http://localhost:8188/system_stats   # ComfyUI
```

---

## Implementation Order

### Sprint 1: Foundation (Phase 0 + Phase 1 core)
1. Fix test suite hangs (lifespan isolation)
2. Fix 8 pre-existing test failures
3. Drill book data model + migration
4. Drill book service (CRUD + state machine)
5. Drill book REST API
6. Tests for all of the above

### Sprint 2: Memory + Agent Integration (Phase 1 completion)
1. Vector store service (ChromaDB wrapper)
2. RAG tool for agents
3. Drill book context injection in agent_runtime
4. Drill book assignment in task_manager
5. Evidence recording on tool execution
6. Auto-indexing completed books

### Sprint 3: Corps Configuration (Phase 2)
1. CorpsConfig model + migration
2. Corps-aware LLM router
3. Methodology enforcement in drill book service
4. Update founding corps YAML with configs
5. ExperimentResult model + tracker
6. Comparative data endpoints

### Sprint 4: Image Generation (Phase 3)
1. ComfyUI connector tool
2. Workflow JSON templates
3. Image service
4. REST endpoints
5. Agent tool registration
6. Tests (mocked ComfyUI)

### Sprint 5: Performer Lifecycle (cross-cutting)
1. Performer state machine (POOLED → DRAFTED → ... → REFLECTING → POOLED)
2. Staff state machine (HIRED → ACTIVE → SUSPENDED/FIRED)
3. Minting service for new performers
4. Self-improvement loop (mechanical score + LLM reflection)
5. Corps size tier enforcement
6. Draft improvements (factor in corps config + performer capabilities)

### Sprint 6: UI + Polish
1. Drill book management pages (view, inspect evidence, resume)
2. Comparative experiment dashboard
3. Image generation UI (trigger + gallery)
4. Performer pool management UI
5. Corps config editor
6. End-to-end integration test: full show run with drill books, image gen, scoring
