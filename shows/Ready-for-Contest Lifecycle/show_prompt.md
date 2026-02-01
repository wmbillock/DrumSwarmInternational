# Ready-for-Contest Lifecycle — Implementation Spec

## Overview

Add a READY_FOR_CONTEST state to the corps lifecycle, creating an evaluation gate between ON_TOUR and COMPLETED. This ensures corps meet quality standards before completing their season.

## Movements

### Movement I: Backend Model Updates

**Owner:** Brass/Percussion Caption Head
**Complexity:** Simple
**Estimated Reps:** 1

**Deliverables:**
- `ready_for_contest()` transition function in `corps_service.py`
- Update `go_on_tour()` to allow READY_FOR_CONTEST → ON_TOUR transition

**Acceptance Criteria:**
- `ready_for_contest(db, corps_id)` changes status from ON_TOUR to READY_FOR_CONTEST
- Function raises CorpsError if called from invalid state
- `go_on_tour()` allows transition from READY_FOR_CONTEST

---

### Movement II: API Commands & Endpoints

**Owner:** Brass/Percussion Caption Head
**Complexity:** Simple
**Estimated Reps:** 1

**Deliverables:**
- Add `ready_for_contest` command to CORPS_COMMANDS
- Add `complete` command to CORPS_COMMANDS
- Add command handlers in `api_execute_corps_command()`
- Update imports

**Acceptance Criteria:**
- `POST /api/corps/{id}/command` with `{command: "ready_for_contest"}` works
- `POST /api/corps/{id}/command` with `{command: "complete"}` works (will fail validation until Movement III)
- WebSocket broadcasts work for both commands
- Commands return appropriate error messages on failure

---

### Movement III: Evaluation Gate Logic

**Owner:** Brass/Percussion Caption Head
**Complexity:** Moderate
**Estimated Reps:** 2

**Deliverables:**
- `complete_corps()` function with validation logic
- Readiness checks: rehearsal proficiency, segment completion

**Acceptance Criteria:**
- `complete_corps()` raises CorpsError if status != READY_FOR_CONTEST
- Validation fails if rehearsal_mode < FULL_ENSEMBLE
- Validation fails if any active show has incomplete segments
- Validation passes and transitions to COMPLETED when all criteria met
- Error messages are clear and actionable

---

### Movement IV: Frontend Lifecycle Controls

**Owner:** Visual Caption Head
**Complexity:** Moderate
**Estimated Reps:** 2

**Deliverables:**
- Update `CorpsDetailV2.tsx` with new lifecycle buttons
- Add status badge styling for READY_FOR_CONTEST
- Update TypeScript types if needed

**Acceptance Criteria:**
- "Ready for Contest" button appears when status is ON_TOUR
- "Complete Season" and "Back to Tour" buttons appear when status is READY_FOR_CONTEST
- Clicking buttons calls correct API endpoint
- Error messages display when completion validation fails
- Status badge shows amber/yellow for READY_FOR_CONTEST state
- UI updates after successful state transitions

---

### Movement V: Tests & Documentation

**Owner:** Drum Major (tests), Visual Tech (docs)
**Complexity:** Moderate
**Estimated Reps:** 2 (1 for tests, 1 for docs)

**Deliverables:**
- 7 test cases in `test_corps.py` covering all transitions
- Updated lifecycle diagram in `docs/architecture.md`
- Description of evaluation criteria in docs

**Acceptance Criteria:**
- All 7 test cases pass:
  1. ON_TOUR → READY_FOR_CONTEST valid transition
  2. WINTER_CAMPS → READY_FOR_CONTEST invalid transition
  3. READY_FOR_CONTEST → COMPLETED with passing evaluation
  4. READY_FOR_CONTEST → COMPLETED fails without rehearsal proficiency
  5. READY_FOR_CONTEST → COMPLETED fails with incomplete segments
  6. READY_FOR_CONTEST → ON_TOUR valid transition (rework)
  7. ON_TOUR → COMPLETED invalid (must go through READY_FOR_CONTEST)
- Architecture doc shows updated lifecycle diagram
- Evaluation criteria documented

---

## Dependencies

```
Movement I (Backend Model)
    ↓
Movement II (API Commands) → Movement III (Evaluation)
    ↓
Movement IV (Frontend)
    ↓
Movement V (Tests & Docs)
```

**Critical Path:** I → II → IV (Frontend depends on API working)
**Parallel Work:** Movement III can be developed alongside II, integrated before IV

---

## Definition of Done

- [ ] All 5 movements completed
- [ ] All tests pass
- [ ] Frontend displays correct buttons for all states
- [ ] Manual E2E test: Create corps, go on tour, mark ready for contest, attempt completion (should fail without work), complete work, complete successfully
- [ ] Documentation updated
- [ ] No regressions in existing lifecycle transitions
- [ ] Code reviewed and merged

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Frontend type mismatch | HIGH | Verify TypeScript types before deployment |
| Incomplete segment query performance | MEDIUM | Use indexed queries, test with large datasets |
| WebSocket timing issues | LOW | Frontend should refetch after commands |

---

## Rollback Plan

If issues occur in production:
1. Revert API command handlers (remove ready_for_contest, complete from CORPS_COMMANDS)
2. Revert frontend button changes
3. Keep backend model changes (enum value is safe, just unused)
4. Fix issues, redeploy

---

**Show Status:** draft → needs_review (after design notes complete)
**Total Estimated Reps:** 8 reps
**Total Estimated Complexity:** 1 simple + 4 moderate = Moderate overall
