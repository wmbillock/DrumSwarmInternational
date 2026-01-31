# Deterministic Corps Drafting Rules

## Overview

Given a corps' instrumentation requirements (role slots) and optional philosophy tags, select agents from the talent pool deterministically. No LLM calls, no database writes — pure YAML in, YAML out.

## Algorithm

### 1. Input

- **Requirements**: ordered list of `{role, count, preferred_specialties?}`
- **Pool directory**: path to talent pool YAML files (ledger + per-agent)

### 2. Candidate Filtering

For each role slot, find agents where:
- `primary_instrument == role`
- `availability == "active"`

Agents already selected for a previous role in the same draft are excluded.

### 3. Deterministic Ranking

Candidates are sorted using these tie-breakers in order:

| Priority | Criterion | Direction |
|----------|-----------|-----------|
| 1 | Specialty match bonus | Matching agents first |
| 2 | `trust_score` | Higher first |
| 3 | `experience_seasons` | Higher first |
| 4 | `agent_id` | Lexicographic ascending (stable tie-breaker) |

**Specialty matching** is soft: agents without a matching specialty are still eligible, just ranked lower. An agent matches if any of their `specialties` appear in the role's `preferred_specialties`.

### 4. Selection

Pick top N candidates per role. Requirements are processed in list order — earlier roles get first pick.

### 5. Availability Marking

After selection, `execute_draft` writes:
- Each selected agent's YAML with `availability: "assigned"`
- Updated `ledger.yaml` reflecting the new availability
- `roster.yaml` via `assign_roster`

### 6. Insufficient Pool

If any role cannot be fully filled, raise `DraftError` with an `unfilled` dict mapping role names to the number of missing agents. No partial writes occur.

## Example

Requirements:
```yaml
- role: brass
  count: 2
  preferred_specialties: [jazz, classical]
- role: percussion
  count: 1
```

Pool contains 3 brass agents (A, B, C) and 1 percussion agent (D), all active. Agent A has specialty "jazz", B has "classical", C has none. A and B have equal trust and experience.

Result: A and B selected for brass (specialty match, then lexicographic), D selected for percussion.

## Extensibility

- Additional tie-breaker criteria can be inserted into `rank_candidates`.
- Philosophy-based filtering can wrap `draft_roster` without modifying internals.
- Phase gating (e.g., only draft during offseason) belongs in the lifecycle module.
