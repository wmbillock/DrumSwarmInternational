## Objective

Refactor the CorpsDetailV2 interface to eliminate manual lifecycle state progression buttons and replace them with a read-only lifecycle status bar. Preserve all operational commands. Add a prep status panel for the WINTER_CAMPS state to surface staffing and readiness information. The goal is to clarify the separation between system-managed state progression and user-controlled operational commands, reducing interface cognitive load while maintaining full operational capability.

## Deliverables

- **Lifecycle Status Bar Component:** Read-only visual component displaying five corps states (INITIALIZING → WINTER_CAMPS → ON_TOUR → READY_FOR_CONTEST → COMPLETED) with current state highlighted and completed states marked with checkmarks
- **Prep Status Panel Component:** Conditional component visible only when corps.state === WINTER_CAMPS; displays staffing count (e.g., "3 of 5 staff assigned") and readiness checklist items with completion indicators (pending, in progress, complete)
- **Updated CorpsDetailV2 OverviewTab:** Remove Go On Tour, Return to Camps, Ready for Contest, and Complete Corps buttons; integrate new status bar and prep panel above operational command section
- **Preserved Operational Commands:** Ensure Resume Hut, Attention, Metronome Tick, and rehearsal mode buttons remain fully clickable, functional, and visually intact in their current locations
- **Updated Unit Tests:** Verify removal of lifecycle progression buttons, confirm new components render with correct props, validate prep panel conditional visibility, confirm operational commands retain functionality, and verify TypeScript compilation succeeds
- **TypeScript Compilation:** Zero compilation errors; all type annotations correct and type safety maintained

## Constraints

- TypeScript must compile without errors
- All existing unit tests must pass
- Prep status panel renders only when corps.state === WINTER_CAMPS
- Status bar is read-only; no onClick handlers for state transitions
- Operational commands retain full functionality and current styling
- No breaking changes to parent components or existing props interfaces
- Lifecycle status bar must display all five states regardless of current corps state (future states shown as outlined/disabled)

## Acceptance Criteria

1. CorpsDetailV2 OverviewTab no longer displays manual lifecycle progression buttons (Go On Tour, Return to Camps, Ready for Contest, Complete Corps)
2. Read-only lifecycle status bar renders correctly showing all five states with current state visually distinguished (filled, bold, accent color)
3. Completed states in status bar display checkmark icon and muted styling
4. Future states in status bar display outlined nodes with lighter typography and no interactive affordances
5. Prep status panel appears and displays staffing + readiness information only when corps.state === WINTER_CAMPS
6. Prep status panel contains staffing progress indicator (e.g., "3 of 5 positions filled") and readiness checklist with visual completion indicators
7. All operational commands (Resume Hut, Attention, Metronome Tick, rehearsal mode) remain clickable, functional, and visually intact
8. Operational commands maintain their current layout and styling; no visual or behavioral changes
9. TypeScript compilation succeeds with zero errors
10. All unit tests pass; button removal verified; new components verified for presence and correct prop binding; operational commands functionality confirmed
11. No regression in existing corps detail functionality outside of lifecycle button removal
12. Status bar and prep panel are read-only and non-interactive (except optional click-through links in prep panel to external task management)
```