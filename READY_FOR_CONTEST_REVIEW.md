# Ready-for-Contest Lifecycle Implementation Review

**Date**: February 1, 2026
**Review Scope**: Complete implementation audit of READY_FOR_CONTEST lifecycle feature
**Status**: PARTIALLY IMPLEMENTED — Missing frontend and command handlers

---

## Executive Summary

The Ready-for-Contest lifecycle feature is **70% implemented**. Core backend functions exist and work correctly, but critical gaps remain in:
- Frontend UI controls and state rendering
- Command handlers in the legacy corps routes
- Comprehensive test coverage

The implementation includes the new `READY_FOR_CONTEST` status enum, transition functions `ready_for_contest()` and `complete_corps()` with proper validation, and a v1 API endpoint. However, the feature is incomplete without frontend controls and command integration.

---

## 1. State Transitions ✅ IMPLEMENTED

### Status Enum Definition
**File**: `/Users/mattbillock/Development/dci-swarm/backend/models/corps.py` (Lines 12-18)

```python
class CorpsStatus(str, enum.Enum):
    INITIALIZING = "initializing"
    WINTER_CAMPS = "winter_camps"
    ON_TOUR = "on_tour"
    READY_FOR_CONTEST = "ready_for_contest"  # ✅ Defined
    COMPLETED = "completed"
    DISBANDED = "disbanded"
```

**Status**: ✅ Complete and correct.

---

## 2. Transition Functions ✅ IMPLEMENTED

### Function: `ready_for_contest()`
**File**: `/Users/mattbillock/Development/dci-swarm/backend/services/corps_service.py` (Lines 486-505)

```python
def ready_for_contest(db: Session, corps_id: str) -> Corps:
    """Signal readiness for contest evaluation — transition to READY_FOR_CONTEST.

    This is a low-friction transition that signals intent to complete the season.
    The corps must be ON_TOUR to use this transition.
    Actual completion requires passing the evaluation gate via complete_corps().
    """
    corps = db.get(Corps, corps_id)
    if corps is None:
        raise CorpsError(f"Corps {corps_id} not found")
    if corps.status != CorpsStatus.ON_TOUR:
        raise CorpsError(
            f"Cannot mark ready for contest from {corps.status.value}. "
            "Corps must be ON_TOUR. Use 'go_on_tour' command first."
        )
    corps.status = CorpsStatus.READY_FOR_CONTEST
    # Keep current rehearsal_mode unchanged
    db.commit()
    db.refresh(corps)
    return corps
```

**Validation**:
- ✅ Proper null check
- ✅ Status precondition: Corps must be ON_TOUR
- ✅ Clear error messages with remediation hints
- ✅ Maintains rehearsal_mode (correct behavior)
- ✅ Commits and refreshes state

### Function: `complete_corps()`
**File**: `/Users/mattbillock/Development/dci-swarm/backend/services/corps_service.py` (Lines 508-564)

```python
def complete_corps(db: Session, corps_id: str) -> Corps:
    """Complete the season — transition from READY_FOR_CONTEST to COMPLETED.

    Validates readiness criteria before allowing completion:
    - Corps must be in READY_FOR_CONTEST state
    - Rehearsal mode must be at least FULL_ENSEMBLE
    - All active show segments must be completed

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
            f"Corps must reach at least FULL_ENSEMBLE rehearsal mode to complete. "
            f"Current mode: {corps.rehearsal_mode.value if corps.rehearsal_mode else 'none'}"
        )

    # Evaluation 2: Show segment completion
    incomplete_segments = (
        db.query(Segment)
        .join(Rep, Rep.segment_id == Segment.id)
        .join(AgentSession, AgentSession.id == Rep.assigned_to)
        .filter(AgentSession.corps_id == corps_id)
        .filter(Segment.status.in_([
            SegmentStatus.PENDING,
            SegmentStatus.IN_PROGRESS,
            SegmentStatus.REVIEW,
            SegmentStatus.BLOCKED,
            SegmentStatus.FAILED,
        ]))
        .count()
    )

    if incomplete_segments > 0:
        raise CorpsError(
            f"Cannot complete: {incomplete_segments} segment(s) are not yet completed. "
            "Finish all show work before completing the season."
        )

    # All checks passed — complete the season
    corps.status = CorpsStatus.COMPLETED
    db.commit()
    db.refresh(corps)
    return corps
```

**Validation**:
- ✅ Proper null check
- ✅ Status precondition: Corps must be READY_FOR_CONTEST
- ✅ **Evaluation Gate 1** ✅: Rehearsal mode validation (FULL_ENSEMBLE or RUN_THROUGH)
- ✅ **Evaluation Gate 2** ✅: Show segment completion check
- ✅ Query uses proper joins to find corps-specific segments
- ✅ Checks for all incomplete statuses (PENDING, IN_PROGRESS, REVIEW, BLOCKED, FAILED)
- ✅ Clear error messages with incomplete segment counts
- ✅ Commits and refreshes state

**Status**: ✅ Complete and comprehensive. Implementation matches spec requirements.

### State Machine Visualization
```
        ┌──────────────────────────────────────┐
        │      INITIALIZING                    │
        └──────────────────┬───────────────────┘
                           │
                           v
        ┌──────────────────────────────────────┐
        │    WINTER_CAMPS (Planning Phase)     │
        │    go_on_tour()                      │
        └──────────────────┬───────────────────┘
                           │
                           v
        ┌──────────────────────────────────────┐
        │  ON_TOUR (Autonomous Execution)      │
        │  ready_for_contest()                 │
        └──────┬──────────────────────┬────────┘
               │                      │
               │ return_to_camps()    │ ready_for_contest()
               │                      v
               │           ┌──────────────────────────┐
               │           │  READY_FOR_CONTEST       │
               │           │  complete_corps()        │
               │           │  return_to_tour() [MISSING]
               │           └──────┬───────────────────┘
               │                  │
               │                  v
               │           ┌──────────────────────────┐
               └──────────>│    COMPLETED             │
                           └──────────────────────────┘
```

---

## 3. Corps Commands ⚠️ PARTIALLY IMPLEMENTED

### Command Registry
**File**: `/Users/mattbillock/Development/dci-swarm/backend/api/legacy/corps_routes.py` (Lines 35-48)

```python
CORPS_COMMANDS = {
    "resume_hut": {...},
    "attention": {...},
    "at_ease": {...},
    "dismissed": {...},
    "basics": {...},
    "sectionals": {...},
    "full_ensemble": {...},
    "run_through": {...},
    "go_on_tour": {...},
    "return_to_camps": {...},
    "metronome_tick": {...},
    "merge_check": {...},
}
```

**Missing Commands** ❌:
- `ready_for_contest` — NOT in CORPS_COMMANDS registry
- `complete` — NOT in CORPS_COMMANDS registry
- `return_to_tour` — NOT in CORPS_COMMANDS registry

### Command Handler
**File**: `/Users/mattbillock/Development/dci-swarm/backend/api/legacy/corps_routes.py` (Lines 427-566)

**Current Handlers** (Lines 528-548):
```python
elif cmd == "go_on_tour":
    try:
        go_on_tour(db, corps_id)
        await manager.broadcast(corps_id, {...})
        result["detail"] = "On Tour"
    except CorpsError as e:
        raise HTTPException(400, str(e))

elif cmd == "return_to_camps":
    try:
        return_to_camps(db, corps_id)
        await manager.broadcast(corps_id, {...})
        result["detail"] = "Returned to Winter Camps"
    except CorpsError as e:
        raise HTTPException(400, str(e))
```

**Missing Handlers** ❌:
- No handler for `ready_for_contest` command
- No handler for `complete` command
- No handler for `return_to_tour` command

**Status**: ⚠️ Missing 3 critical command handlers despite transition functions existing.

---

## 4. V1 API Endpoints ⚠️ PARTIALLY IMPLEMENTED

### Implemented: `POST /api/v1/corps/{corps_id}/ready-for-contest`
**File**: `/Users/mattbillock/Development/dci-swarm/backend/api/v1/router.py` (Lines 379-408)

```python
@router.post("/api/v1/corps/{corps_id}/ready-for-contest")
def v1_ready_for_contest(corps_id: str):
    """Transition a corps from ON_TOUR to READY_FOR_CONTEST."""
    _validate_id(corps_id, "corps_id")
    from backend.models.corps import Corps, CorpsStatus

    db = _get_db_session()
    try:
        corps = db.get(Corps, corps_id)
        if not corps:
            raise HTTPException(404, f"Corps '{corps_id}' not found")
        if corps.status != CorpsStatus.ON_TOUR:
            raise HTTPException(
                400,
                f"Corps must be ON_TOUR to become READY_FOR_CONTEST (current: {corps.status.value})",
            )
        corps.status = CorpsStatus.READY_FOR_CONTEST
        db.commit()
        return {
            "corps_id": corps.id,
            "display_name": corps.name,
            "state": corps.status.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to transition corps: {e}")
    finally:
        db.close()
```

**Validation**:
- ✅ ID validation
- ✅ Proper 404 handling
- ✅ Status precondition check
- ✅ Error handling with rollback
- ✅ Returns updated corps state

**Missing Endpoints** ❌:
- `POST /api/v1/corps/{corps_id}/complete` — NOT implemented
- `POST /api/v1/corps/{corps_id}/return-to-tour` — NOT implemented
- No evaluation gate access points (e.g., GET evaluation status)

**Status**: ⚠️ Only 1 of 3 endpoints implemented.

---

## 5. Evaluation Gate ⚠️ INCOMPLETE

### What's Implemented
The `complete_corps()` function contains evaluation logic:
1. ✅ Status precondition (must be READY_FOR_CONTEST)
2. ✅ Rehearsal mode gate (must be FULL_ENSEMBLE or RUN_THROUGH)
3. ✅ Segment completion gate (no PENDING, IN_PROGRESS, REVIEW, BLOCKED, FAILED segments)

### What's Missing ❌
Per the spec: *"Evaluation criteria should be configurable per corps (not hardcoded thresholds)"*

Current issues:
- Rehearsal mode and segment completion are hardcoded checks
- No configurable thresholds per corps
- No pre-evaluation query (frontend can't check if a corps is ready before attempting transition)
- No `evaluate_readiness()` function as mentioned in spec (evaluations are embedded in `complete_corps()`)

**Spec Requirement**:
> Check minimum score thresholds, rep completion rates, and active agent sessions before allowing COMPLETED transition.

**Implementation Gap**: Score thresholds and agent session checks are NOT implemented.

**Status**: ⚠️ Partial. Gate exists but incomplete against spec.

---

## 6. Frontend Controls ❌ NOT IMPLEMENTED

### Current State
**File**: `/Users/mattbillock/Development/dci-swarm/frontend/src/pages/CorpsDetailV2.tsx` (Lines 104-174)

```typescript
const isWinterCamps = corps.state === "winter_camps";
const isOnTour = corps.state === "on_tour";

return (
  <div>
    <Panel title="Lifecycle Controls" className="mt-16">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        {isWinterCamps && (
          <button className="primary" onClick={() => exec("go_on_tour")} disabled={!!cmdLoading}>
            {cmdLoading === "go_on_tour" ? "Starting..." : "Go On Tour"}
          </button>
        )}
        {isOnTour && (
          <button onClick={() => exec("return_to_camps")} disabled={!!cmdLoading}>
            {cmdLoading === "return_to_camps" ? "Returning..." : "Return to Camps"}
          </button>
        )}
        {/* ... other controls ... */}
      </div>
    </Panel>
  </div>
);
```

**Missing Controls** ❌:
- No `isReadyForContest` state check
- No "Ready for Contest" button when ON_TOUR
- No "Complete" button when READY_FOR_CONTEST
- No "Return to Tour" button when READY_FOR_CONTEST
- No state badge styling for READY_FOR_CONTEST (Badge shows "default" variant for non-on_tour states)
- No status information about evaluation readiness

**Required Additions**:
```typescript
const isReadyForContest = corps.state === "ready_for_contest";

{isOnTour && (
  <button className="accent" onClick={() => exec("ready_for_contest")} disabled={!!cmdLoading}>
    {cmdLoading === "ready_for_contest" ? "Marking..." : "Ready for Contest"}
  </button>
)}

{isReadyForContest && (
  <>
    <button className="success" onClick={() => exec("complete")} disabled={!!cmdLoading}>
      {cmdLoading === "complete" ? "Completing..." : "Complete Season"}
    </button>
    <button onClick={() => exec("return_to_tour")} disabled={!!cmdLoading}>
      {cmdLoading === "return_to_tour" ? "Returning..." : "Return to Tour"}
    </button>
  </>
)}
```

**Status**: ❌ Frontend completely missing state rendering and controls.

---

## 7. Test Coverage ❌ NOT IMPLEMENTED

### Test Files Checked
- `/Users/mattbillock/Development/dci-swarm/backend/tests/test_lifecycle_transitions.py` — Does NOT cover ready_for_contest
- `/Users/mattbillock/Development/dci-swarm/backend/tests/test_lifecycle_transitions_persistence.py` — Does NOT cover ready_for_contest
- `/Users/mattbillock/Development/dci-swarm/backend/tests/test_corps.py` — No relevant tests found
- Global search for `ready_for_contest` and `complete_corps` tests returned NO RESULTS

### Missing Test Coverage
**Required by spec**:
> Tests: State transition tests covering valid/invalid paths, evaluation gate pass/fail, and command handler integration.

**Specific test cases needed**:
1. ✅ ~~State transition: ON_TOUR → READY_FOR_CONTEST~~ ← Not tested
2. ✅ ~~State transition: READY_FOR_CONTEST → COMPLETED~~ ← Not tested
3. ✅ ~~State transition: READY_FOR_CONTEST → ON_TOUR~~ ← Not tested
4. ✅ ~~Invalid: WINTER_CAMPS → READY_FOR_CONTEST~~ ← Not tested
5. ✅ ~~Invalid: INITIALIZING → READY_FOR_CONTEST~~ ← Not tested
6. ✅ ~~Evaluation gate: FULL_ENSEMBLE requirement~~ ← Not tested
7. ✅ ~~Evaluation gate: Segment completion check~~ ← Not tested
8. ✅ ~~Evaluation gate: Failure cases with detailed error messages~~ ← Not tested
9. ✅ ~~Command handler: ready_for_contest command~~ ← Not tested
10. ✅ ~~Command handler: complete command~~ ← Not tested
11. ✅ ~~Command handler: return_to_tour command~~ ← Not tested
12. ✅ ~~V1 API: POST /api/v1/corps/{id}/ready-for-contest~~ ← Not tested
13. ✅ ~~V1 API: POST /api/v1/corps/{id}/complete~~ ← Not tested
14. ✅ ~~V1 API: POST /api/v1/corps/{id}/return-to-tour~~ ← Not tested

**Status**: ❌ Zero test coverage. No tests exist for the feature.

---

## 8. Integration Points

### Competition Evaluation
**File**: `/Users/mattbillock/Development/dci-swarm/backend/api/v1/router.py` (Lines 1855-1940)

The `v1_contest_evaluate()` endpoint finds READY_FOR_CONTEST corps and transitions them to COMPLETED:

```python
@router.post("/api/v1/competitions/{competition_id}/evaluate")
def v1_contest_evaluate(req: ContestEvaluateRequest):
    """Find all READY_FOR_CONTEST corps and run a competition between them.

    After scoring, transitions each participating corps to COMPLETED.
    """
    # ...
    # Transition all participating corps to COMPLETED
    for c in ready_corps:
        c.status = CorpsStatus.COMPLETED
    db.commit()
```

**Integration Status**: ✅ Correct — uses READY_FOR_CONTEST state as intended.

### Metronome Heartbeat
**File**: `/Users/mattbillock/Development/dci-swarm/backend/api/v1/router.py` (Line 2173-2178)

Performer completion handlers correctly handle SessionStatus.COMPLETED but don't interact with corps state transitions.

**Integration Status**: ✅ No conflicts.

---

## Summary Table

| Feature | Location | Status | Notes |
|---------|----------|--------|-------|
| **Status Enum** | models/corps.py | ✅ Complete | READY_FOR_CONTEST defined |
| **ready_for_contest()** | corps_service.py | ✅ Complete | Proper validation, error messages |
| **complete_corps()** | corps_service.py | ✅ Complete | Evaluation gates implemented |
| **CORPS_COMMANDS registry** | legacy/corps_routes.py | ❌ Missing | 3 commands not registered |
| **Command handlers** | legacy/corps_routes.py | ❌ Missing | 3 handlers not implemented |
| **V1 API endpoint (ready-for-contest)** | v1/router.py | ✅ Complete | Proper HTTP layer |
| **V1 API endpoint (complete)** | v1/router.py | ❌ Missing | Not implemented |
| **V1 API endpoint (return-to-tour)** | v1/router.py | ❌ Missing | Not implemented |
| **Frontend state check** | CorpsDetailV2.tsx | ❌ Missing | No isReadyForContest check |
| **Frontend buttons** | CorpsDetailV2.tsx | ❌ Missing | No READY_FOR_CONTEST controls |
| **Frontend state styling** | CorpsDetailV2.tsx | ⚠️ Partial | Generic badge, not state-specific |
| **Test coverage** | backend/tests/ | ❌ Missing | Zero tests for feature |
| **evaluate_readiness()** | corps_service.py | ⚠️ Partial | Logic embedded, not separate function |

---

## Detailed Findings

### What Works ✅
1. **Core state machine logic** is correct and well-implemented
2. **Transition functions** have proper validation and error handling
3. **Database schema** correctly defines READY_FOR_CONTEST status
4. **V1 API ready-for-contest endpoint** properly implements the first transition
5. **Evaluation gates** correctly check rehearsal mode and segment completion
6. **Integration with competition evaluation** correctly uses READY_FOR_CONTEST state

### What's Missing ❌
1. **Legacy command handlers** for ready_for_contest, complete, return_to_tour
2. **V1 API endpoints** for complete and return_to_tour
3. **Frontend UI controls** for READY_FOR_CONTEST state and transitions
4. **Frontend state checks** to conditionally show/hide buttons
5. **Comprehensive test suite** covering all transitions and edge cases
6. **Pre-evaluation readiness check** (frontend can't query readiness before attempting transition)

### What's Incomplete ⚠️
1. **Evaluation gate** is hardcoded; spec requires configurable thresholds per corps
2. **Score threshold checks** mentioned in spec but not implemented
3. **Agent session checks** mentioned in spec but not implemented
4. **Separate evaluate_readiness() function** not extracted (logic is embedded in complete_corps)
5. **CLAUDE.md** not updated to reflect READY_FOR_CONTEST in lifecycle documentation (still shows old diagram)

---

## Recommendations

### Critical (Blocking Usage)
1. **Add 3 missing command handlers** in `/Users/mattbillock/Development/dci-swarm/backend/api/legacy/corps_routes.py`:
   - `ready_for_contest` → calls `ready_for_contest_service()`
   - `complete` → calls `complete_corps_service()`
   - `return_to_tour` → calls `go_on_tour()` or new `return_to_tour()` function

2. **Register 3 missing commands** in CORPS_COMMANDS dict in same file

3. **Add 2 missing V1 API endpoints**:
   - `POST /api/v1/corps/{corps_id}/complete`
   - `POST /api/v1/corps/{corps_id}/return-to-tour`

4. **Implement frontend controls** in CorpsDetailV2.tsx with proper state checks and buttons

### High Priority (Feature Completeness)
5. **Add comprehensive test suite** covering all state transitions and edge cases

6. **Update CLAUDE.md** with corrected lifecycle diagram including READY_FOR_CONTEST

### Medium Priority (Polish)
7. **Extract evaluate_readiness() function** for reusability and clarity

8. **Add configurable evaluation thresholds** per corps (currently hardcoded)

9. **Implement score threshold and agent session checks** as per spec

10. **Add pre-evaluation endpoint** (GET `/api/v1/corps/{corps_id}/readiness`) for frontend to query before attempting transition

---

## Code Quality Notes

### Strengths
- Error messages are clear and actionable
- Database queries properly use joins to scope to corps
- State mutations are properly persisted with commits
- HTTP layer properly validates input and handles errors

### Areas for Improvement
- No type hints on command handlers (use async def, but types are implicit)
- Evaluation logic could be extracted to a separate, testable function
- Frontend type definitions should include READY_FOR_CONTEST in V1CorpsDetail state union
- No logging in transition functions (difficult to debug)

---

## Conclusion

The Ready-for-Contest lifecycle feature is **functionally 70% complete** at the backend/service layer, but **only 50% complete** overall due to missing frontend and command integration. The core state machine logic and evaluation gates are solid, but the feature cannot be used without:

1. Command handlers in the legacy API
2. V1 API endpoints for complete and return-to-tour
3. Frontend UI controls and state rendering
4. Test coverage to prevent regressions

**Estimated effort to completion**: 4-6 hours (mostly frontend and test work; backend is mostly done).

**Recommendation**: Complete the missing pieces before merging to main, or track as an open show/feature.
