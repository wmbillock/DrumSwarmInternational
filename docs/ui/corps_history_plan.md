# Corps History & Executive Director Seance — Extension Plan

## Step 1: Current Seance Implementation Summary

### Where it lives

| Layer | File | Purpose |
|-------|------|---------|
| Service | `backend/services/seance.py` | `query_previous_sessions()` — semantic search over ChromaDB memory bank; `query_for_agent_context()` — builds agent prompt context from memories + capability ledger stats |
| Storage | `backend/services/memory_bank.py` | `MemoryBank` class wrapping ChromaDB. Collections keyed by agent identity. Stores/recalls `Memory(text, metadata, distance)` objects. Methods: `store()`, `recall()`, `store_session_summary()`, `store_failure_lesson()`, `get_context_for_task()` |
| Models | `backend/models/agent_memory.py` | `AgentMemory` (versioned episodic memories: DECISION, PROFILE, SUMMARY, PREFERENCE, LESSON) and `TaskMemory` (session checkpoints, tool calls, outcomes) — SQLAlchemy |
| API | `backend/api/app.py:1738-1744` | `POST /api/seance` — takes `{query, role?, k?}`, returns `SeanceResult` (query, memories[], sessions_found) |
| Frontend | `frontend/src/pages/Seance.tsx` | Single input field, POSTs query, displays JSON result in a code block |
| API client | `frontend/src/services/api.ts:169-170` | `querySeance(query, corpsId?)` |
| Tests | `backend/tests/test_batch5.py:221-232` | `test_seance_empty_result`, `test_query_for_agent_context` |
| Nav | `frontend/src/components/SideNav.tsx` | Entry: `{ to: "/seance", label: "Seance", icon: "QRY" }` |

### What artifacts it writes

The seance service itself writes **nothing** to disk. It is read-only against two stores:

1. **ChromaDB** (`.chromadb/`): Semantic embeddings stored by other services via `memory_bank.store_session_summary()` and `memory_bank.store_failure_lesson()`. Metadata fields: `type`, `session_id`, `role`, `corps_id`, `show_title`.
2. **SQLAlchemy tables**: `agent_memories` and `task_memories` — written by `MemoryManager` during agent sessions.

### How context is selected

`query_previous_sessions()` does a single ChromaDB similarity search scoped to one collection (keyed by `role` or `performer_name` or `"system"`). There is **no artifact-path awareness** — it cannot look up a specific show's design notes, standings, or scores. It only finds whatever was previously pushed into the memory bank by agent sessions.

`query_for_agent_context()` augments memory bank recall with recent session success/failure counts from the capability ledger (SQL query).

### How transcripts/summaries are stored

- Session summaries: `memory_bank.store_session_summary(identity, session_id, role, summary, corps_id, show_title)` — idempotent by `memory_id = f"session_{session_id}"`
- Failure lessons: `memory_bank.store_failure_lesson(identity, session_id, what_failed, lesson)` — stored with `type=failure_lesson` metadata
- Task checkpoints: `TaskMemory` rows in SQLAlchemy with `tool_calls` (JSON), `outcomes`, `result_summary`

### What the seance *cannot* do today

- Select a specific past show or season to discuss
- Read canonical filesystem artifacts (standings, scores, design notes, show prompts, run output)
- Anchor a conversation to a corps' competition history entry
- Produce a transcript or reusable session artifact from the seance itself

---

## Step 2: Extension Plan

### Goal

Evolve the seance from a generic memory-bank search into a **corps history browser** with an **"Ask the ED about a past show"** workflow anchored to real artifacts.

### A) Corps History Index

A per-corps derived index that enumerates all canonical artifacts from previous shows and seasons, making them addressable for seance sessions.

**Path**: `corps/<corps_id>/history/index.yaml`

**Schema**:

```yaml
corps_id: cavaliers
generated_at: "2026-01-31T12:00:00Z"
entries:
  - entry_id: "cavaliers-tour-s1"
    season_id: tour-s1
    show_slug: tour-show-s1         # extracted from placement notes ("show:tour-show-s1")
    placement: 1
    final_score: 78.4
    artifacts:
      standings: seasons/tour-s1/standings.yaml
      corps_scores: seasons/tour-s1/performances/cavaliers/scores.yaml
      show_status: shows/tour-show-s1/status.yaml
      design_notes: shows/tour-show-s1/design_notes.md
      show_prompt: shows/tour-show-s1/show_prompt.md
    runs: []                        # list of run_id strings found under performances/cavaliers/
```

**Builder function**: `build_history_index(project_root, corps_id) -> dict`

1. Read `corps/<corps_id>/corps.yaml`, extract `history[]` entries.
2. For each placement entry, derive `entry_id = f"{corps_id}-{season_id}"` (deduplicate by taking the last entry per season).
3. Parse `notes` field to extract `show_slug` (convention: `"show:<slug>"`).
4. Probe each canonical artifact path. Include only paths that exist on disk.
5. Scan `seasons/<season_id>/performances/<corps_id>/*/manifest.yaml` for run entries.
6. Write `corps/<corps_id>/history/index.yaml`.
7. Return the dict.

**The index is a cache**, not a source of truth. It can always be rebuilt from `corps.yaml` + filesystem probing. The builder is idempotent.

### B) Seance Sessions Anchored to History Entries

A seance session is a structured conversation with a simulated Executive Director about a specific past show, grounded in the artifacts from that history entry.

**Session directory**: `seances/<seance_id>/`

**Files**:

```
seances/<seance_id>/
├── session.yaml          # session metadata + context binder
└── transcript.md         # append-only conversation log
```

**`session.yaml` schema**:

```yaml
seance_id: "abc123"
corps_id: cavaliers
entry_id: "cavaliers-tour-s1"
season_id: tour-s1
show_slug: tour-show-s1
created_at: "2026-01-31T12:00:00Z"
status: active                     # active | closed
context_binder:
  - path: seasons/tour-s1/standings.yaml
    type: standings
    loaded: true
  - path: seasons/tour-s1/performances/cavaliers/scores.yaml
    type: corps_scores
    loaded: true
  - path: shows/tour-show-s1/design_notes.md
    type: design_notes
    loaded: true
  - path: shows/tour-show-s1/show_prompt.md
    type: show_prompt
    loaded: false                  # file existed but was empty
```

The **context binder** is the manifest of artifact paths assembled from the history index entry's `artifacts` dict. When a session starts, each path is probed; `loaded: true` means the file existed and was non-empty at session creation time. This is the contract for what the ED "remembers."

**`transcript.md` format**:

```markdown
<!-- seance: abc123 | corps: cavaliers | season: tour-s1 -->

**[user]** What worked well in the brass section this season?

**[executive_director]** Looking at the scores, brass came in at 75 — solid but
below our percussion line at 80. The design notes mention...

**[user]** How should we adjust for next season?

**[executive_director]** Based on the placement (#1) and the caption breakdown...
```

Appended to by each conversation turn.

### API Surface

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/corps/{corps_id}/history-index` | Build (or return cached) history index |
| `POST` | `/api/seances` | Create a seance session from a history entry |
| `GET` | `/api/seances/{seance_id}` | Get session metadata + context binder |
| `POST` | `/api/seances/{seance_id}/message` | Send message, get ED response |
| `GET` | `/api/seances/{seance_id}/transcript` | Read transcript |

### Service Functions

**`backend/services/corps_history.py`** (new):

- `build_history_index(project_root: Path, corps_id: str) -> dict` — Scan corps.yaml + filesystem, write + return index
- `load_history_index(project_root: Path, corps_id: str) -> dict` — Read cached index or build if missing
- `get_history_entry(project_root: Path, corps_id: str, entry_id: str) -> dict` — Single entry from index

**`backend/services/seance_session.py`** (new):

- `create_session(project_root: Path, corps_id: str, entry_id: str) -> dict` — Validate artifacts exist, assemble context binder, write session.yaml + empty transcript.md, return session dict
- `load_session(project_root: Path, seance_id: str) -> dict` — Read session.yaml
- `append_transcript(project_root: Path, seance_id: str, role: str, message: str) -> None` — Append to transcript.md
- `read_transcript(project_root: Path, seance_id: str) -> str` — Read transcript.md
- `assemble_context(project_root: Path, session: dict) -> str` — Read all loaded artifacts from context binder, concatenate into a context string for the ED prompt
- `close_session(project_root: Path, seance_id: str) -> None` — Set status to closed

### Scope Boundary

This plan covers **only** the persistence layer, index building, session lifecycle, and context assembly. The actual LLM conversation (calling the ED with the assembled context) is a future step — the MVP conversation endpoint returns the assembled context binder and transcript but uses a stub response (similar to the Design Room MVP pattern where `note_router.route_note()` tags the message without an LLM call).

### What Does Not Change

- `seance.py` — The existing memory-bank seance remains untouched. It continues to serve `POST /api/seance` for generic memory queries.
- `memory_bank.py` — No changes. The new system reads filesystem artifacts, not ChromaDB.
- `corps.yaml` history format — No changes. The index builder reads the existing format.
- `TheHistory.tsx` — No changes. It continues to render placement history from `/api/corps-workspace/{corpsId}/history`.

---

## Step 3: Acceptance Tests (TDD)

### `backend/tests/test_corps_history.py`

All tests use `tmp_path` fixtures to create realistic directory structures.

#### History Index Building

```
test_build_index_from_single_season
```
Given a corps.yaml with one history entry (`season_id: s1, notes: "show:my-show"`) and the corresponding `seasons/s1/standings.yaml` and `seasons/s1/performances/<corps_id>/scores.yaml` on disk, `build_history_index()` produces an index with one entry whose `artifacts` dict contains the correct relative paths and all paths that exist on disk are present.

```
test_build_index_deduplicates_seasons
```
Given a corps.yaml with duplicate entries for the same season (as cavaliers currently has), the index contains only one entry per `(corps_id, season_id)` pair, using the last occurrence.

```
test_build_index_missing_show_artifacts
```
Given a history entry referencing `show:ghost-show` where the show directory does not exist, the entry's `artifacts` dict omits the missing paths (no `design_notes`, no `show_prompt`, no `show_status`) but still includes season-level artifacts that do exist (`standings`, `corps_scores`).

```
test_build_index_discovers_runs
```
Given a run manifest at `seasons/s1/performances/<corps_id>/run-001/manifest.yaml`, the entry's `runs` list contains `"run-001"`.

```
test_build_index_empty_history
```
Given a corps.yaml with `history: []`, `build_history_index()` returns an index with zero entries and does not raise.

```
test_build_index_no_notes_field
```
Given a history entry with `notes: ""` (no show slug), the entry has `show_slug: null` and omits show-level artifact paths.

```
test_load_index_returns_cached
```
After calling `build_history_index()`, calling `load_history_index()` reads from `corps/<id>/history/index.yaml` without re-scanning.

```
test_get_history_entry_found
```
`get_history_entry()` with a valid entry_id returns the matching entry dict.

```
test_get_history_entry_not_found
```
`get_history_entry()` with an unknown entry_id raises `ValueError`.

#### Seance Session Creation

```
test_create_session_from_history_entry
```
Given a valid history index entry with at least `standings` and `corps_scores` artifacts existing on disk, `create_session()` creates `seances/<id>/session.yaml` with a populated context binder where `loaded: true` for existing artifacts, and `seances/<id>/transcript.md` exists and is empty.

```
test_create_session_refuses_missing_required_artifacts
```
Given a history entry where `standings.yaml` does not exist on disk, `create_session()` raises `ValueError("Required artifact missing: standings")`. The standings artifact is the minimum required artifact for a seance — without it, there is no performance record to discuss.

```
test_create_session_allows_missing_optional_artifacts
```
Given a history entry where `design_notes.md` does not exist but `standings.yaml` and `corps_scores.yaml` do exist, `create_session()` succeeds. The context binder entry for `design_notes` has `loaded: false`.

```
test_create_session_writes_valid_yaml
```
After `create_session()`, the `session.yaml` file round-trips through `yaml.safe_load()` and contains all required fields: `seance_id`, `corps_id`, `entry_id`, `season_id`, `created_at`, `status`, `context_binder`.

#### Seance Session Operations

```
test_append_and_read_transcript
```
Call `append_transcript()` twice (once as user, once as executive_director), then `read_transcript()` returns a string containing both entries with role attribution.

```
test_assemble_context_reads_artifacts
```
Given a session with two `loaded: true` artifacts on disk, `assemble_context()` returns a string containing the content of both files, prefixed by their artifact type.

```
test_close_session_sets_status
```
After `close_session()`, `load_session()` returns a dict with `status: "closed"`.

```
test_create_session_nonexistent_entry_raises
```
Calling `create_session()` with an `entry_id` not in the history index raises `ValueError`.

#### Security

```
test_seance_id_no_path_traversal
```
A seance_id containing `..` is rejected by `load_session()` / `append_transcript()`.
