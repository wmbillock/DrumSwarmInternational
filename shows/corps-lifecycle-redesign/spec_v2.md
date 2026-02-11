```markdown
# Corps Lifecycle Redesign

## Show Concept

**Vision:** Transform CorpsDetailV2 from a hybrid state-management + operations interface into two distinct, purpose-built zones: a **read-only lifecycle dashboard** and a **command center for operational control**. By removing manual state transition buttons (Go On Tour, Return to Camps, Ready for Contest, Complete Corps), we eliminate the possibility of inconsistent state changes while preserving full granular control over rehearsal, drill, and tour logistics.

The corps lifecycle follows a canonical progression: **INITIALIZING → WINTER_CAMPS → ON_TOUR → READY_FOR_CONTEST → COMPLETED**. This progression is system-driven (triggered by rules-based conditions or administrative commands at the swarm level), never by front-end button clicks. The status bar visualizes this progression as an informational timeline, giving Program Coordinators and Instructional Staff immediate situational awareness.

When a corps enters **WINTER_CAMPS**, a secondary **Prep Status Panel** surfaces pre-tour readiness: staffing fill rate, equipment inventory status, section assignments, rehearsal schedule completeness, and logistics readiness. This contextual information enables proactive problem-solving before the corps moves on tour.

## Musical Design

**Not Applicable** — This is an operational/administrative system redesign. The DCI Swarm's "musical design" concerns lie in show concept, visual guard design, and competitive scoring frameworks, which are orthogonal to this corps management UI refactor.

## Visual Design

### Lifecycle Status Bar
- **Layout:** Horizontal left-to-right progression across the CorpsDetailV2 header or dedicated status zone
- **State Indicators:** Five states displayed as nodes or segments in sequence, each labeled clearly (INITIALIZING, WINTER_CAMPS, ON_TOUR, READY_FOR_CONTEST, COMPLETED)
- **Current State Styling:** Highlighted with accent color (e.g., primary blue), bold text, or filled icon; focus ring for accessibility
- **Completed State Styling:** Dimmed background + checkmark icon or muted color to signal achievement
- **Future States:** Outlined nodes, lighter typography, no interactive affordances
- **Timeline Metadata (optional):** Hover tooltips or small text badges showing state entry date or milestones (e.g., "Entered: Jan 15")
- **Responsive Behavior:** On mobile, condense to vertical stack or carousel; maintain label visibility
- **Accessibility:** ARIA role `progressbar` or `status`; semantic HTML (`<nav>`, `<ol>`, `<li>`); focus management; screen-reader friendly state descriptions

### Prep Status Panel (Conditional: Visible in WINTER_CAMPS Only)
- **Layout:** Positioned below the status bar or in a collapsible card in the OverviewTab
- **Two-Part Structure:**
  1. **Staffing Status Bar:** Numeric progress indicator (e.g., "3 of 5 key positions filled" with a horizontal bar at 60%)
  2. **Readiness Checklist:** Itemized list of pre-tour checks:
     - Equipment Inventory (All instruments + travel cases accounted for)
     - Section Leadership Assignments (Each instrument section has assigned lead + backup)
     - Rehearsal Schedule Finalized (All winter camps dates published)
     - Media & Logistics Approved (Photos, transport, lodging confirmed)
- **Visual Indicators per Item:** Checkbox icon (pending ☐, in progress ◐, complete ☑) or color-coded label (gray = pending, yellow = in progress, green = complete)
- **Interactive Elements (optional):** Click-through to detail view or external task management; no edit capability from this panel
- **Styling:** Subtle background color or border to visually distinguish from operational commands; remains read-only

### Operational Command Buttons (Preserved & Unchanged)
- **Resume Hut:** Reconnect/reload current session
- **Attention:** Pause ensemble for administrative announcements
- **Metronome Tick:** Sync rehearsal timing via metronome tool
- **Rehearsal Mode Toggles:** BASICS → SECTIONALS → FULL_ENSEMBLE → RUN_THROUGH state machine
- **Layout:** Grouped in a dedicated "Operations" tray or action bar below the status bar; maintained in current location if already established
- **Styling:** No changes to button appearance, size, or color
- **Behavior:** No modifications to onClick logic or async side effects
- **Accessibility:** Maintain existing ARIA labels and keyboard shortcuts

## Guard Design

**Not Applicable** — This is a corps management interface (administrative/operational layer), not a visual performance design element. DCI show guard designs concern choreography, flags, silks, and visual ensemble formations, which do not apply to back-office UI.

## General Effect

**Cognitive Impact:** The redesign decouples **state awareness** (read-only, informational) from **operational execution** (interactive, command-driven). Users scan the status bar to understand *where* a corps is in its lifecycle, then use operational buttons to *do things* (resume rehearsal, sync timing, toggle drill modes). This mental separation reduces decision-making friction and prevents accidental state changes.

**Staffing & Logistics:** The prep panel surfaces readiness gaps during WINTER_CAMPS, the most critical planning window. By surfacing staffing count, equipment status, and schedule completeness in one glance, Program Coordinators can prioritize hiring, procurement, or logistics efforts before tour begins.

**Risk Mitigation:** Removing manual state buttons eliminates a common UX anti-pattern: giving users the ability to corrupt system state. State progression now flows through authenticated backend rules only, ensuring data integrity.

## Constraints

- TypeScript must compile without errors
- Existing unit tests must pass
- CorpsDetailV2 OverviewTab must remove all lifecycle progression buttons (Go On Tour, Return to Camps, Ready for Contest, Complete Corps)
- Operational commands must remain fully functional
- Prep status panel only displays when corps state === WINTER_CAMPS
- Status bar must be read-only (no interactive state transitions from UI)
- No breaking changes to parent components or existing props interfaces
- Lifecycle status bar must display all five states regardless of current corps state (future states shown as outlined/disabled)

## Deliverables

- **Lifecycle Status Bar Component:** Read-only visual component displaying five corps states (INITIALIZING → WINTER_CAMPS → ON_TOUR → READY_FOR_CONTEST → COMPLETED) with current state highlighted and completed states marked with checkmarks
- **Prep Status Panel Component:** Conditional component visible only when corps.state === WINTER_CAMPS; displays staffing count (e.g., "3 of 5 staff assigned") and readiness checklist items with completion indicators (pending, in progress, complete)
- **Updated CorpsDetailV2 OverviewTab:** Remove Go On Tour, Return to Camps, Ready for Contest, and Complete Corps buttons; integrate new status bar and prep panel above operational command section
- **Preserved Operational Commands:** Ensure Resume Hut, Attention, Metronome Tick, and rehearsal mode buttons remain fully clickable, functional, and visually intact in their current locations
- **Updated Unit Tests:** Verify removal of lifecycle progression buttons, confirm new components render with correct props, validate prep panel conditional visibility, confirm operational commands retain functionality, and verify TypeScript compilation succeeds
- **TypeScript Compilation:** Zero compilation errors; all type annotations correct and type safety maintained

## Objective

Refactor the CorpsDetailV2 interface to eliminate manual lifecycle state progression buttons and replace them with a read-only lifecycle status bar. Preserve all operational commands. Add a prep status panel for the WINTER_CAMPS state to surface staffing and readiness information. The goal is to clarify the separation between system-managed state progression and user-controlled operational commands, reducing interface cognitive load while maintaining full operational capability.

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

## Swarm Prompt

### Objective

Refactor the CorpsDetailV2 interface to eliminate manual lifecycle state progression buttons and replace them with a read-only lifecycle status bar. Preserve all operational commands. Add a prep status panel for the WINTER_CAMPS state to surface staffing and readiness information. The goal is to clarify the separation between system-managed state progression and user-controlled operational commands, reducing interface cognitive load while maintaining full operational capability.

### Deliverables

- **Lifecycle Status Bar Component:** Read-only visual component displaying five corps states (INITIALIZING → WINTER_CAMPS → ON_TOUR → READY_FOR_CONTEST → COMPLETED) with current state highlighted and completed states marked with checkmarks
- **Prep Status Panel Component:** Conditional component visible only when corps.state === WINTER_CAMPS; displays staffing count (e.g., "3 of 5 staff assigned") and readiness checklist items with completion indicators (pending, in progress, complete)
- **Updated CorpsDetailV2 OverviewTab:** Remove Go On Tour, Return to Camps, Ready for Contest, and Complete Corps buttons; integrate new status bar and prep panel above operational command section
- **Preserved Operational Commands:** Ensure Resume Hut, Attention, Metronome Tick, and rehearsal mode buttons remain fully clickable, functional, and visually intact in their current locations
- **Updated Unit Tests:** Verify removal of lifecycle progression buttons, confirm new components render with correct props, validate prep panel conditional visibility, confirm operational commands retain functionality, and verify TypeScript compilation succeeds
- **TypeScript Compilation:** Zero compilation errors; all type annotations correct and type safety maintained

### Constraints

- TypeScript must compile without errors
- All existing unit tests must pass
- Prep status panel renders only when corps.state === WINTER_CAMPS
- Status bar is read-only; no onClick handlers for state transitions
- Operational commands retain full functionality and current styling
- No breaking changes to parent components or existing props interfaces
- Lifecycle status bar must display all five states regardless of current corps state (future states shown as outlined/disabled)

### Acceptance Criteria

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