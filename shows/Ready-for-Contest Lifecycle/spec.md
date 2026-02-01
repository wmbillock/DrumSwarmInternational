# Ready-for-Contest Lifecycle

## Overview

Add a READY_FOR_CONTEST lifecycle state between ON_TOUR and COMPLETED, creating an evaluation gate that ensures corps meet quality criteria before completing their season.

## Acceptance Criteria

1. **State transitions**: ON_TOUR → READY_FOR_CONTEST → COMPLETED. Corps can return to ON_TOUR from READY_FOR_CONTEST for rework.
2. **Transition functions**: `ready_for_contest()` and `complete_corps()` in corps_service.py with proper validation.
3. **Corps commands**: Add `ready_for_contest`, `complete`, and `return_to_tour` to CORPS_COMMANDS with handlers.
4. **Evaluation gate**: `evaluate_readiness()` checks minimum score thresholds, rep completion rates, and active agent sessions before allowing COMPLETED transition.
5. **Frontend controls**: Lifecycle buttons on CorpsDetailV2.tsx update to show READY_FOR_CONTEST state and its available transitions.
6. **Tests**: State transition tests covering valid/invalid paths, evaluation gate pass/fail, and command handler integration.

## Constraints

- Must not break existing INITIALIZING → WINTER_CAMPS ⇄ ON_TOUR flow
- DISBANDED remains reachable from any state
- Evaluation criteria should be configurable per corps (not hardcoded thresholds)

## Deliverables

- Updated corps_service.py with transition functions and evaluation logic
- Updated CORPS_COMMANDS registry
- Frontend lifecycle controls for the new state
- Test coverage for all new transitions
