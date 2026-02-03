## Show Concept
Remove manual lifecycle transition buttons from CorpsDetailV2 and replace with a read-only status bar. Users should see where their corps is in the lifecycle without being able to manually push state transitions. Operational commands (Resume Hut, Attention, etc.) remain.

## Musical Design
No backend changes needed. This is a frontend-only show.

## Visual Design
Modify frontend/src/pages/CorpsDetailV2.tsx OverviewTab:

1. Remove the Lifecycle Controls panel that contains Go On Tour, Return to Camps, Ready for Contest, Complete Corps, and Back to Tour buttons.

2. Add a new LifecycleStatusBar component (inline or separate file) that renders a horizontal stepper showing: INITIALIZING -> WINTER_CAMPS -> ON_TOUR -> READY_FOR_CONTEST -> COMPLETED. The current state is highlighted with the accent color and a filled circle. Past states are dimmed. Future states are outlined. Use CSS transitions for visual polish.

3. Keep the operational commands as a separate panel below the status bar: Resume Hut, Attention, Metronome Tick, and the rehearsal mode buttons (basics, sectionals, full_ensemble, run_through).

4. When corps.state is winter_camps, show a PrepStatus panel below the status bar that displays:
   - Staffing status (roster_size out of 16)
   - Current rehearsal mode
   - A list of readiness checks (e.g. "Staff hired: Yes/No", "Rehearsal mode: basics")

Styling: Use Field Commander Brutalism design. The status bar should have sharp borders, monospace text for states, and the accent color for the active state.

## Guard Design
Handle edge cases: corps with state=initializing (before any staffing), corps with state=disbanded (show all states greyed out with a DISBANDED overlay).

## General Effect
The lifecycle becomes informational rather than interactive - users understand where their corps is without accidentally triggering state changes. System-driven transitions make the lifecycle feel more managed.

## Constraints
- Do not remove or change any backend endpoints.
- Do not add new API calls - use existing corps detail data (state, rehearsal_mode, roster_size).
- Keep the Resume Hut, Attention, Metronome Tick, and rehearsal mode buttons.
- Do not break the tab navigation in CorpsDetailV2.

## Deliverables
- Modified frontend/src/pages/CorpsDetailV2.tsx with lifecycle status bar, removed lifecycle buttons, added prep status panel

## Evaluation Rubric
- Lifecycle buttons removed: 20 points
- Read-only status bar rendered correctly: 30 points
- PrepStatus panel shown in WINTER_CAMPS: 20 points
- Operational commands preserved: 15 points
- TypeScript compiles clean: 15 points