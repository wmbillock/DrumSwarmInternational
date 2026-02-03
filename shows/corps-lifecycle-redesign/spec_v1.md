# Corps Lifecycle Redesign

## Goal
Remove manual lifecycle buttons from CorpsDetailV2 and replace with read-only lifecycle status bar. Keep operational commands. Add prep status panel in WINTER_CAMPS.

## Acceptance Criteria
1. CorpsDetailV2 OverviewTab no longer shows Go On Tour, Return to Camps, Ready for Contest, Complete Corps buttons
2. New read-only lifecycle status bar showing: INITIALIZING -> WINTER_CAMPS -> ON_TOUR -> READY_FOR_CONTEST -> COMPLETED with current state highlighted
3. Operational commands preserved: Resume Hut, Attention, Metronome Tick, rehearsal mode buttons
4. When corps is in WINTER_CAMPS, show a prep status panel with staffing status and readiness checks
5. TypeScript compiles clean
6. Existing tests pass