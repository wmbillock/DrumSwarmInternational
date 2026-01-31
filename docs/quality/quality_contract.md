# Quality Contract: DrumSwarmInternational Test Matrix

## Overview
Each test case has an identifier `QC-{domain}-{number}`, specifies observable behavior, acceptance criteria, test type, and asserted artifacts.

---

## A) Role Discipline ("Instrument Boundaries")

| ID | Observable Behavior | Acceptance Criteria | Test Type | Asserted Artifacts |
|----|--------------------|--------------------|-----------|-------------------|
| QC-A-01 | Performer cannot send directives | `send_message(type=DIRECTIVE, from_role="performer")` raises `InvalidMessageType` | Unit | Exception type + message |
| QC-A-02 | Brass tech cannot message guard caption head | `send_message(from_role="brass_tech", to_role="guard_caption_head")` raises `InvalidMessagePath` | Unit | Exception; `ROLE_HIERARCHY["brass_tech"]` does not contain `"guard_caption_head"` |
| QC-A-03 | Agent tool permissions enforced per role | Runtime refuses tool call not in `tools_allowed` for that `AgentDefinition` | Unit | `RunResult` contains tool-denied error; tool side-effect absent |
| QC-A-04 | Performer cannot create segments | Performer-classified agent calling `create_segment` is rejected | Integration | No new `Segment` row in DB; error returned to agent |
| QC-A-05 | Caption head stays within own caption | Brass caption head handoff to guard tech raises error or is rejected by routing | Unit | `InvalidMessagePath` or handoff refusal |

---

## B) Design-Room Routing

| ID | Observable Behavior | Acceptance Criteria | Test Type | Asserted Artifacts |
|----|--------------------|--------------------|-----------|-------------------|
| QC-B-01 | User task reaches Executive Director first | `initialize_corps` creates ED session; first segment owned by ED | Integration | `AgentSession` with role `executive_director` is first active session |
| QC-B-02 | ED hands off to PC with segment ID | After ED creates MOVEMENT segments, handoff message to PC includes segment references | Integration | `Message` row with `type=HANDOFF`, `to_role="program_coordinator"`, body containing segment ID |
| QC-B-03 | PC routes to correct caption head by segment type | PC creates brass-related segment → handoff to `brass_caption_head`, not percussion | Integration | Handoff `Message.to_role` matches expected caption for segment content |
| QC-B-04 | Messages respect priority ordering | Poll returns CRITICAL before NORMAL messages for same recipient | Unit | `poll_messages` result list ordered by priority then timestamp |
| QC-B-05 | Escalation follows chain upward | Tech flags problem → caption head receives it; caption head escalates → PC receives it | Integration | `Message` rows with `type=ESCALATION` at each hop; no skipped levels |

---

## C) Prompt Approval Gate

| ID | Observable Behavior | Acceptance Criteria | Test Type | Asserted Artifacts |
|----|--------------------|--------------------|-----------|-------------------|
| QC-C-01 | Major self-improvement requires approval | Agent proposing `model_tier` change creates `SelfImprovementLog` with `status=PENDING` | Unit | DB row: `status=PENDING`, `changes` JSON contains `model_tier` |
| QC-C-02 | Unapproved change is not applied | While `status=PENDING`, `AgentDefinition.model_tier` unchanged | Unit | `AgentDefinition.version` unchanged; field value unchanged |
| QC-C-03 | Approved change bumps version | `approve_self_improvement(log_id)` → definition version incremented, changes applied | Unit | `AgentDefinition.version == old + 1`; field matches proposed value |
| QC-C-04 | Rejected change leaves definition intact | `reject_self_improvement(log_id)` → `status=REJECTED`, definition unchanged | Unit | `SelfImprovementLog.status=REJECTED`; definition fields unchanged |
| QC-C-05 | Minor prompt tweak does not require approval | Agent changing only `system_prompt` text applies immediately (not in `MAJOR_CHANGE_FIELDS`) | Unit | No `SelfImprovementLog` with `status=PENDING`; prompt updated |

---

## D) Corps Persistence

| ID | Observable Behavior | Acceptance Criteria | Test Type | Asserted Artifacts |
|----|--------------------|--------------------|-----------|-------------------|
| QC-D-01 | Corps survives process restart | Create corps, stop process, restart, query corps by ID → same state | Integration | `Corps` row with same `id`, `status`, `rehearsal_mode` |
| QC-D-02 | Segments persist after agent death | Agent session fails → segment remains with original status | Integration | `Segment.status` unchanged; `AgentSession.status=FAILED` |
| QC-D-03 | Reps reassignable after performer death | Rep in `IN_PROGRESS` with dead session → metronome resets to `PENDING` | Integration | `Rep.status=PENDING`; `Rep.agent_session_id` cleared or new |
| QC-D-04 | Context snapshots saved on session completion | Completed session has non-null `context_snapshot` | Unit | `AgentSession.context_snapshot IS NOT NULL` |
| QC-D-05 | Memory records persist across sessions | `AgentMemory` created in session 1 retrievable in session 2 for same definition | Integration | `memory_manager.get_memories()` returns memories from prior session |

---

## E) Talent Pool Persistence

| ID | Observable Behavior | Acceptance Criteria | Test Type | Asserted Artifacts |
|----|--------------------|--------------------|-----------|-------------------|
| QC-E-01 | Performer record persists across corps | Performer created in corps A, queryable when corps B starts | Integration | `Performer` row exists with unchanged `name`, `trust_score` |
| QC-E-02 | Trust score accumulates across shows | Performer completes sessions in two corps → `total_sessions` reflects both | Integration | `Performer.total_sessions == sessions_corps_a + sessions_corps_b` |
| QC-E-03 | Retired performer excluded from auditions | Performer with `status=RETIRED` not returned by `conduct_auditions` | Unit | Returned performer list does not contain retired performer |
| QC-E-04 | Probation status persists | Performer set to `PROBATION` retains status after new corps creation | Integration | `Performer.status == PROBATION` after corps B init |
| QC-E-05 | Specialties survive across corps | Performer specialties set in corps A readable in corps B | Integration | `Performer.specialties` unchanged |

---

## F) Lifecycle Transitions

| ID | Observable Behavior | Acceptance Criteria | Test Type | Asserted Artifacts |
|----|--------------------|--------------------|-----------|-------------------|
| QC-F-01 | Corps follows INITIALIZING → WINTER_CAMPS → ON_TOUR → COMPLETED | Each transition only moves forward through valid states | Unit | State machine: invalid transitions raise error |
| QC-F-02 | Rehearsal mode progresses BASICS → SECTIONALS → FULL_ENSEMBLE → RUN_THROUGH | `rehearsal_progression` advances mode only when criteria met | Integration | `Corps.rehearsal_mode` value after each advancement |
| QC-F-03 | Performer ages out at MAX_PERFORMER_AGE | `age_performer` on performer with `age=22` → `status=RETIRED` | Unit | `Performer.status == RETIRED` |
| QC-F-04 | Season transition increments experience | `conduct_season_transition` → `experience_seasons += 1` | Unit | `Performer.experience_seasons == old + 1` |
| QC-F-05 | Critical role auto-respawns on death | ED session fails → metronome creates new ED session | Integration | New `AgentSession` with `role=executive_director`, `status=ACTIVE` |
| QC-F-06 | Non-critical role stays dead | Performer session fails → no auto-respawn | Integration | No new `AgentSession` for that performer role after failure |

---

## G) Competition & Scoring

| ID | Observable Behavior | Acceptance Criteria | Test Type | Asserted Artifacts |
|----|--------------------|--------------------|-----------|-------------------|
| QC-G-01 | Each judge type produces a score | All `JudgeType` values produce `Score` rows for a completed show | Integration | One `Score` per `JudgeType` per corps |
| QC-G-02 | Penalties deduct from total | Corps with `PenaltyType.TIMING` penalty has lower final score than clean corps | Unit | `final_score == raw_score - penalty_amount` |
| QC-G-03 | Scores are per-corps, not cross-contaminated | Score for corps A not visible when querying corps B | Unit | `Score` query filtered by `corps_id` returns only that corps' scores |
| QC-G-04 | Rankings ordered by total score descending | Given 3 corps with known scores, ranking returns correct order | Unit | Ordered list matches expected sort |
| QC-G-05 | Timing penalty applied for deadline violation | Rep completed past deadline → `Penalty` row with `type=TIMING` | Integration | `Penalty` row linked to corps with correct type |

---

## H) Evolution Windows

| ID | Observable Behavior | Acceptance Criteria | Test Type | Asserted Artifacts |
|----|--------------------|--------------------|-----------|-------------------|
| QC-H-01 | Self-improvement blocked during ON_TOUR | Agent proposing change while `corps.status=ON_TOUR` → rejected | Unit | `SelfImprovementLog` not created or immediately rejected |
| QC-H-02 | Self-improvement allowed during WINTER_CAMPS | Agent proposing change while `corps.status=WINTER_CAMPS` → log created with `PENDING` | Unit | `SelfImprovementLog.status=PENDING` |
| QC-H-03 | No definition version bump mid-show | `AgentDefinition.version` unchanged for duration of ON_TOUR status | Contract | Assert version at tour start == version at tour end |
| QC-H-04 | Evolution applies between seasons | After `conduct_season_transition`, approved improvements take effect | Integration | `AgentDefinition` fields reflect approved changes post-transition |
| QC-H-05 | Rehearsal mode changes don't count as evolution | Advancing from BASICS to SECTIONALS doesn't trigger improvement guard | Unit | Mode advances without `SelfImprovementLog` creation |

---

## I) TDD Enforcement

| ID | Observable Behavior | Acceptance Criteria | Test Type | Asserted Artifacts |
|----|--------------------|--------------------|-----------|-------------------|
| QC-I-01 | Tuner rejects code without test | `tuner.validate` on rep with code changes but no test file → validation failure | Unit | `ValidationResult.passed == False`; error mentions missing tests |
| QC-I-02 | Tuner passes when test added first | Rep with test file added before implementation → `tuner.validate` passes test-presence check | Unit | `ValidationResult.passed == True` for test-presence rule |
| QC-I-03 | Rep cannot move to COMPLETED without passing tuner | `Rep` transition `REVIEW → COMPLETED` blocked if tuner validation fails | Integration | `Rep.status` remains `REVIEW`; transition raises error |
| QC-I-04 | Test file must exercise changed code | Tuner checks test imports/references match changed modules | Unit | `ValidationResult` includes coverage-relevance check |
| QC-I-05 | CI gate rejects PR without test delta | `run-through` (pytest) fails if feature diff has no corresponding test diff | Contract | pytest exit code != 0; output identifies missing test coverage |

---

## Test Infrastructure Notes

- **Unit tests**: pytest with in-memory SQLite (`backend/tests/`), mock LLM client
- **Integration tests**: Full service stack with real DB, mocked LLM responses
- **Contract tests**: Assertions on system invariants across multi-step workflows; run as part of `dci run-through`
- **Key fixtures**: `db` (session-scoped SQLite), `corps` (initialized corps), `agent_def` (role definition), `performer` (talent pool entry)

## Files to Modify

No code changes in this plan — this is a test matrix specification only. Implementation will create/modify:
- `backend/tests/test_quality_contract.py` (new, organized by QC-* identifiers)
- Possibly individual test modules per domain if the file grows large
- `backend/services/lifecycle_manager.py` — may need evolution window guard (QC-H-01)
- `backend/tools/tuner.py` — may need TDD enforcement logic (QC-I-01 through QC-I-04)

## Verification

After implementation, run `dci run-through` and confirm all QC-* tests pass. Each test should be individually addressable via `pytest -k QC_A_01` pattern.
