# Ready-for-Contest Lifecycle — Design Notes
**Drill Writer: George Vivace**
**Date: 2026-02-01**

## Executive Summary

The READY_FOR_CONTEST lifecycle feature introduces a new state between ON_TOUR and COMPLETED, creating an evaluation gate that ensures corps meet quality criteria before completing their season. This prevents premature completion and enforces readiness standards.

### Current State Analysis

**Already Implemented:**
- `CorpsStatus.READY_FOR_CONTEST` enum value exists in `backend/models/corps.py:16`
- Status guidance text exists in `CORPS_STATUS_GUIDANCE` dict in `backend/services/corps_service.py:665-668`
- Database schema supports the new status value (enum-based)

**Not Yet Implemented:**
- No `ready_for_contest()` transition function in `corps_service.py`
- No `complete_corps()` transition function
- No 'ready_for_contest' or 'complete' commands in `CORPS_COMMANDS`
- No command handlers in `app.py`
- No evaluation logic to determine readiness criteria
- No frontend UI for the new lifecycle controls
- No tests for the new state transitions

---

## Choreography: State Machine Design

### Current Lifecycle Flow
```
INITIALIZING → WINTER_CAMPS ⇄ ON_TOUR → [jump to] COMPLETED / DISBANDED
                     ↑____________↓
```

**Problem:** Corps can jump directly from ON_TOUR to COMPLETED without any validation.

### Proposed Lifecycle Flow
```
INITIALIZING → WINTER_CAMPS ⇄ ON_TOUR → READY_FOR_CONTEST → COMPLETED
                     ↑____________↓           ↕                    ↓
                                          [evaluation]        DISBANDED
                                             gate
```

### Valid Transitions

| From State | To State | Command | Validation Required |
|------------|----------|---------|-------------------|
| ON_TOUR | READY_FOR_CONTEST | `ready_for_contest` | None (intent signal) |
| READY_FOR_CONTEST | ON_TOUR | `return_to_tour` or `go_on_tour` | None (allow rework) |
| READY_FOR_CONTEST | COMPLETED | `complete` | YES (evaluation gate) |
| READY_FOR_CONTEST | WINTER_CAMPS | `return_to_camps` | None (allow planning) |

**Key Design Decision:** `ready_for_contest` is a LOW-friction transition (just intent), but `complete` is HIGH-friction (must pass evaluation).

---

## Movement Breakdown

### Movement I: Backend Model Updates ✅ (PARTIALLY DONE)

**Status:** Enum value and guidance already exist. Need transition function.

**Tasks:**
1. ✅ `CorpsStatus.READY_FOR_CONTEST` enum — DONE
2. ✅ Status guidance text — DONE
3. ❌ Add `ready_for_contest(db, corps_id)` function to `corps_service.py`
   - Allow transition from: `ON_TOUR` only
   - Set status to `READY_FOR_CONTEST`
   - Keep current rehearsal_mode unchanged
   - Return updated corps
4. ❌ Update `go_on_tour()` to also allow `READY_FOR_CONTEST → ON_TOUR`
   - Change line 458 condition to include `CorpsStatus.READY_FOR_CONTEST`

**Code Location:** `backend/services/corps_service.py` after `return_to_camps()` (line 476)

---

### Movement II: Lifecycle Commands & API Endpoints

**New Commands to Add:**
1. `ready_for_contest` — Signal readiness for evaluation
2. `complete` — Attempt to complete the season (with validation)

**CORPS_COMMANDS additions** (app.py:1380):
```python
"ready_for_contest": {
    "label": "Ready for Contest",
    "description": "Mark corps as ready for competition evaluation",
    "category": "execution"
},
"complete": {
    "label": "Complete Season",
    "description": "Complete the season (requires readiness check)",
    "category": "execution"
},
```

**Command Handlers** (app.py, after line 1527):
```python
elif cmd == "ready_for_contest":
    try:
        ready_for_contest(db, corps_id)
        await manager.broadcast(corps_id, {
            "type": "command", "command": "ready_for_contest",
            "content": "Ready for Contest — awaiting competition evaluation.",
        })
        result["detail"] = "Ready for Contest"
    except CorpsError as e:
        raise HTTPException(400, str(e))

elif cmd == "complete":
    try:
        complete_corps(db, corps_id)
        await manager.broadcast(corps_id, {
            "type": "command", "command": "complete",
            "content": "Season completed! Congratulations!",
        })
        result["detail"] = "Season Completed"
    except CorpsError as e:
        raise HTTPException(400, str(e))
```

**Import Update** (app.py:1406):
```python
from backend.services.corps_service import (
    go_on_tour, return_to_camps, set_rehearsal_mode, disband_corps,
    merge_monitor_check, ready_for_contest, complete_corps, CorpsError,
)
```

---

### Movement III: Evaluation Gate Logic

**Readiness Criteria Design:**

The evaluation gate checks the following before allowing READY_FOR_CONTEST → COMPLETED:

1. **Show Completion:** All segments in the corps's active show(s) must be COMPLETED
   - Query all segments for the corps's shows
   - Ensure none are PENDING, IN_PROGRESS, FAILED, or BLOCKED

2. **Minimum Rehearsal Proficiency:** Corps has reached at least FULL_ENSEMBLE mode
   - `corps.rehearsal_mode >= RehearsalMode.FULL_ENSEMBLE`

3. **Design Room Artifacts Approved:** (Optional — may be V2)
   - Check if show status is 'published' or 'approved'

**Implementation: `complete_corps()` function**

```python
def complete_corps(db: Session, corps_id: str) -> Corps:
    """Complete the season — transition from READY_FOR_CONTEST to COMPLETED.

    Validates readiness criteria before allowing completion.
    Raises CorpsError if validation fails.
    """
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")

    if corps.status != CorpsStatus.READY_FOR_CONTEST:
        raise CorpsError(
            f"Cannot complete from {corps.status.value}. "
            "Corps must be in READY_FOR_CONTEST state. "
            "Use 'ready_for_contest' command first."
        )

    # Evaluation 1: Rehearsal proficiency
    if corps.rehearsal_mode not in (RehearsalMode.FULL_ENSEMBLE, RehearsalMode.RUN_THROUGH):
        raise CorpsError(
            f"Corps must reach at least FULL_ENSEMBLE rehearsal mode. "
            f"Current mode: {corps.rehearsal_mode.value if corps.rehearsal_mode else 'none'}"
        )

    # Evaluation 2: Show segment completion
    from backend.models.show import Show
    active_shows = db.query(Show).filter(
        Show.corps_id == corps_id,
        Show.status == 'active'
    ).all()

    for show in active_shows:
        incomplete_segments = db.query(Segment).filter(
            Segment.id == show.id,  # show is also a segment (type='show')
        ).filter(
            Segment.status.in_([
                SegmentStatus.PENDING,
                SegmentStatus.IN_PROGRESS,
                SegmentStatus.REVIEW,
                SegmentStatus.BLOCKED,
                SegmentStatus.FAILED,
            ])
        ).count()

        if incomplete_segments > 0:
            raise CorpsError(
                f"Cannot complete: Show '{show.title}' has {incomplete_segments} "
                "incomplete segments. Finish all work before completing."
            )

    # All checks passed — complete the season
    corps.status = CorpsStatus.COMPLETED
    db.commit()
    db.refresh(corps)
    return corps
```

**Code Location:** `backend/services/corps_service.py` after `ready_for_contest()` function

**Error Messages Philosophy:**
- Be specific about what failed
- Tell the user what action to take
- Provide current state context

---

### Movement IV: Frontend Lifecycle Controls

**File:** `frontend/src/pages/CorpsDetailV2.tsx`

**Current Lifecycle Buttons** (need to verify exact location):
- "Go On Tour" — when status is WINTER_CAMPS
- "Return to Camps" — when status is ON_TOUR

**New Button Logic:**

| Corps Status | Buttons to Show |
|--------------|-----------------|
| WINTER_CAMPS | "Go On Tour" |
| ON_TOUR | "Ready for Contest", "Return to Camps" |
| READY_FOR_CONTEST | "Complete Season", "Back to Tour", "Return to Camps" |
| COMPLETED | (no buttons — show completion badge) |
| DISBANDED | (no buttons) |

**Status Badge Updates:**
- Add `READY_FOR_CONTEST` to status badge color mapping
- Suggested color: amber/yellow (transition state)

**TypeScript Type Updates:**
- Verify `CorpsStatus` enum in frontend includes `'ready_for_contest'`
- File: `frontend/src/services/v1.ts` or `frontend/src/types/`

**UI Interactions:**
1. "Ready for Contest" button → calls `POST /api/corps/{id}/command` with `{command: "ready_for_contest"}`
2. "Complete Season" button → calls `POST /api/corps/{id}/command` with `{command: "complete"}`
   - On error (400), display error message explaining why completion failed
   - Suggest "Back to Tour" to fix issues
3. "Back to Tour" button → calls `POST /api/corps/{id}/command` with `{command: "go_on_tour"}`

---

### Movement V: Tests & Documentation

**Test File:** `backend/tests/test_corps.py`

**Test Cases to Add:**

1. `test_ready_for_contest_transition_from_on_tour`
   - Create corps in ON_TOUR
   - Call `ready_for_contest(db, corps_id)`
   - Assert status == READY_FOR_CONTEST

2. `test_ready_for_contest_invalid_from_winter_camps`
   - Create corps in WINTER_CAMPS
   - Call `ready_for_contest(db, corps_id)`
   - Assert raises CorpsError

3. `test_complete_corps_with_passing_evaluation`
   - Create corps in READY_FOR_CONTEST
   - Set rehearsal_mode = RUN_THROUGH
   - Create show with all segments COMPLETED
   - Call `complete_corps(db, corps_id)`
   - Assert status == COMPLETED

4. `test_complete_corps_fails_without_rehearsal_proficiency`
   - Create corps in READY_FOR_CONTEST
   - Set rehearsal_mode = BASICS
   - Call `complete_corps(db, corps_id)`
   - Assert raises CorpsError with message about rehearsal mode

5. `test_complete_corps_fails_with_incomplete_segments`
   - Create corps in READY_FOR_CONTEST
   - Set rehearsal_mode = RUN_THROUGH
   - Create show with 1 segment IN_PROGRESS
   - Call `complete_corps(db, corps_id)`
   - Assert raises CorpsError with message about incomplete work

6. `test_ready_for_contest_to_on_tour_transition`
   - Create corps in READY_FOR_CONTEST
   - Call `go_on_tour(db, corps_id)`
   - Assert status == ON_TOUR
   - Assert this is allowed (rework cycle)

7. `test_invalid_complete_from_on_tour`
   - Create corps in ON_TOUR (not READY_FOR_CONTEST)
   - Call `complete_corps(db, corps_id)`
   - Assert raises CorpsError

**Documentation Updates:**

File: `docs/architecture.md`

Update the lifecycle diagram in the "Corps Lifecycle" section to show:

```
┌─────────────────┐
│  INITIALIZING   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│  WINTER_CAMPS   │◄────►│    ON_TOUR      │
└─────────────────┘      └────────┬────────┘
         │                        │
         │                        ▼
         │              ┌─────────────────────┐
         │              │ READY_FOR_CONTEST   │
         │              └──────────┬──────────┘
         │                         │
         │                    [evaluation]
         │                         │ pass
         │                         ▼
         │              ┌─────────────────┐
         └─────────────►│   COMPLETED     │
                        └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   DISBANDED     │
                        └─────────────────┘
```

Add description of evaluation criteria and the purpose of READY_FOR_CONTEST.

---

## Design Philosophy

### Why This Approach?

1. **Low Friction to Signal Intent:** `ready_for_contest` has NO validation. It's a signal that the corps THINKS they're ready. This encourages teams to self-assess.

2. **High Friction to Complete:** `complete` has STRICT validation. This prevents premature completion and ensures quality standards.

3. **Reversible Until Committed:** Corps can move back from READY_FOR_CONTEST → ON_TOUR without penalty. This supports iteration and rework.

4. **Clear Error Messages:** When validation fails, tell the user exactly what's wrong and how to fix it.

5. **Progressive Validation:** Start with 2 simple checks (rehearsal mode, segment completion). Can add more criteria in V2 (e.g., artifact approval, performance scores).

---

## Risk Analysis

### Potential Issues

1. **Segment Completion Query Performance:** If corps have 100+ segments, the completion check could be slow.
   - **Mitigation:** Use indexed status column, filter at DB level

2. **Edge Case: No Active Shows:** What if corps has no shows?
   - **Decision:** Allow completion (empty show list = no work to validate)

3. **Frontend Type Mismatches:** If `CorpsStatus` enum isn't updated in frontend
   - **Mitigation:** Check `v1.ts` types before deployment

4. **WebSocket Broadcast Timing:** State changes might not immediately reflect in UI
   - **Mitigation:** Frontend should refetch corps detail after command success

---

## Implementation Order

**Recommended sequence for minimal breakage:**

1. **Backend Model** (Movement I) — Add transition functions first
2. **API Commands** (Movement II) — Wire up commands to functions
3. **Manual Testing** — Use curl/Postman to test state transitions
4. **Evaluation Logic** (Movement III) — Add validation to `complete_corps()`
5. **Tests** (Movement V part 1) — Ensure all transitions work
6. **Frontend UI** (Movement IV) — Add buttons and status badges
7. **Documentation** (Movement V part 2) — Update architecture doc
8. **End-to-End Test** — Create a corps, move through full lifecycle

---

## Open Questions

1. Should READY_FOR_CONTEST allow transition back to WINTER_CAMPS?
   - **Answer:** YES — allow full reversibility except from COMPLETED

2. Should we auto-transition to READY_FOR_CONTEST when all segments complete?
   - **Answer:** NO — require explicit user intent via command

3. What happens to READY_FOR_CONTEST corps in heartbeat/metronome?
   - **Answer:** They should be IDLE — no work to do, waiting for evaluation

4. Should evaluation criteria be configurable per-corps?
   - **Answer:** V2 feature — start with hardcoded criteria

---

## Success Criteria

✅ Corps can transition ON_TOUR → READY_FOR_CONTEST
✅ Corps can transition READY_FOR_CONTEST → COMPLETED (with validation)
✅ Corps can transition READY_FOR_CONTEST → ON_TOUR (rework)
✅ Validation prevents completion without rehearsal proficiency
✅ Validation prevents completion with incomplete segments
✅ Frontend displays correct buttons per state
✅ Status badges show READY_FOR_CONTEST correctly
✅ All tests pass
✅ Documentation reflects new lifecycle

---

**END OF DESIGN NOTES**

---

## Next Steps for Percussion Section

These design notes should be handed off to the appropriate caption heads:

1. **Brass/Percussion** — Backend implementation (Movements I-III)
2. **Visual/Guard** — Frontend UI updates (Movement IV)
3. **Drum Major** — Testing and validation (Movement V)

The Program Coordinator should create reps for each movement and assign to the appropriate sections.
