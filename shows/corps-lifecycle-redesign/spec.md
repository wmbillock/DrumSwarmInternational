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

1. **LifecycleStatusBar Component** (`frontend/src/components/LifecycleStatusBar.tsx`)
   - Renders horizontal (desktop) / vertical (mobile) five-state progression
   - Current state: accent color + bold + filled icon
   - Completed states: checkmark icon + muted styling
   - Future states: outlined placeholder nodes, no interactive affordances
   - Props: `currentState: CorpsLifecycleState`, `allStates?: CorpsLifecycleState[]`, `timestamps?: Record<...>`, `className?: string`
   - Zero interactive handlers (read-only)
   - Accessibility: ARIA `progressbar` role, semantic HTML, focus management

2. **PrepStatusPanel Component** (`frontend/src/components/PrepStatusPanel.tsx`)
   - Conditional render: returns `null` if `corps.state !== 'WINTER_CAMPS'`
   - Staffing section: "X of Y positions filled" with progress bar
   - Readiness checklist: items with status icons (pending ☐, in progress ◐, complete ☑)
   - Props: `corps: Corps`, `staffingStatus: { filled, required }`, `readinessItems: ReadinessCheckItem[]`, `onItemClick?: (id: string) => void`, `className?: string`
   - Styling: subtle background/border to distinguish from operational buttons

3. **Refactored CorpsDetailV2 OverviewTab** (`frontend/src/pages/CorpsDetailV2.tsx`)
   - Delete: Go On Tour, Return to Camps, Ready for Contest, Complete Corps button code
   - Import: LifecycleStatusBar and PrepStatusPanel components
   - Position: LifecycleStatusBar in header/status zone; PrepStatusPanel below it
   - Pass props: currentState from `corps.state`; staffing/readiness data from API or local state
   - Preserve: Resume Hut, Attention, Metronome Tick, rehearsal toggles (unchanged layout, styling, behavior)

4. **Unit Tests** (`frontend/src/__tests__/`)
   - **LifecycleStatusBar.test.tsx** (7+ cases): render all states, highlight current, no handlers, responsive, a11y
   - **PrepStatusPanel.test.tsx** (6+ cases): conditional visibility, staffing display, readiness items, accessibility
   - **CorpsDetailV2.test.tsx additions** (5+ cases): button removal, component integration, operational preservation
   - Snapshot tests for visual regression detection
   - All new tests pass; all existing tests continue to pass

5. **TypeScript Type Definitions** (`frontend/src/types/`)
   - Export `CorpsLifecycleState` union type
   - Export `LifecycleStatusBarProps`, `PrepStatusPanelProps`, `ReadinessCheckItem` interfaces
   - All props strictly typed; no `any` types

6. **Documentation** (optional, `docs/ui/corps-lifecycle-redesign.md`)
   - Component usage examples, visual references, integration guide, accessibility notes

## Swarm Prompt

### Objective

**Build a read-only lifecycle timeline UI for CorpsDetailV2 that separates state awareness from operational command execution.** Remove four manual state-transition buttons (Go On Tour, Return to Camps, Ready for Contest, Complete Corps) and replace with a visual, non-interactive status bar showing corps progression through five canonical lifecycle states (INITIALIZING → WINTER_CAMPS → ON_TOUR → READY_FOR_CONTEST → COMPLETED). Add a contextual **Prep Status Panel** visible only during WINTER_CAMPS, surfacing staffing fill rate and pre-tour readiness checks. All operational commands (Resume Hut, Attention, Metronome Tick, rehearsal toggles) remain unchanged.

**Success Metric:** Corps management users can instantly identify lifecycle state (via read-only status bar) and execute operational commands (via preserved button UI) without confusion. TypeScript compiles clean; all tests pass; no regressions in existing functionality.

### Deliverables (Actionable for Agent Swarm)

1. **Create LifecycleStatusBar Component**
   - File: `frontend/src/components/LifecycleStatusBar.tsx`
   - Implement horizontal (desktop) / vertical (mobile) state progression display
   - Current state: accent color + bold + filled icon
   - Completed states: checkmark icon + muted/dimmed styling
   - Future states: outlined placeholder nodes, no interactive affordances
   - TypeScript props: `currentState`, `allStates?`, `timestamps?`, `className?`
   - Accessibility: ARIA `progressbar` or `status` role; semantic HTML (`<ol>`, `<li>`, `<nav>`); focus ring on current state

2. **Create PrepStatusPanel Component**
   - File: `frontend/src/components/PrepStatusPanel.tsx`
   - Conditional render: return `null` if `corps.state !== 'WINTER_CAMPS'`; render if state is WINTER_CAMPS
   - Staffing section: display "X of Y positions filled" with horizontal progress bar (e.g., 60% filled)
   - Readiness checklist: render items with status indicators
     - Pending: ☐ (empty checkbox) + gray text
     - In progress: ◐ (half-filled circle) + orange/yellow text
     - Complete: ☑ (checkmark) + green text
   - TypeScript props: `corps`, `staffingStatus`, `readinessItems`, `onItemClick?`, `className?`
   - Styling: subtle background or left border to distinguish from operational commands
   - No edit capability; read-only display

3. **Refactor CorpsDetailV2 OverviewTab**
   - File: `frontend/src/pages/CorpsDetailV2.tsx`
   - **Delete:** Go On Tour, Return to Camps, Ready for Contest, Complete Corps button code (search for button text and remove)
   - **Import:** LifecycleStatusBar and PrepStatusPanel components
   - **Position new components:** Insert LifecycleStatusBar near top of OverviewTab (in header or dedicated status zone); place PrepStatusPanel below it
   - **Pass props:** currentState from `corps.state`; staffing/readiness data from API fetch or local state
   - **Verify:** Resume Hut, Attention, Metronome Tick, rehearsal toggles buttons remain unchanged in layout, styling, and onClick handlers

4. **Write Unit Tests**
   - **LifecycleStatusBar.test.tsx** (7+ cases)
     - ✅ Renders all five states in correct order (INITIALIZING → WINTER_CAMPS → ON_TOUR → READY_FOR_CONTEST → COMPLETED)
     - ✅ Current state receives accent color and bold styling
     - ✅ No onClick or onKeyDown handlers (read-only)
     - ✅ Completed states show checkmark and muted color
     - ✅ Future states display as outlined placeholders
     - ✅ Responsive layout on mobile (<576px)
     - ✅ ARIA role and labels present; screen-reader friendly
   - **PrepStatusPanel.test.tsx** (6+ cases)
     - ✅ Renders when `corps.state === 'WINTER_CAMPS'`
     - ✅ Returns `null` (does not render) when state is other than WINTER_CAMPS
     - ✅ Staffing bar displays "3 of 5" format and correct percentage
     - ✅ All readiness items render with correct status icons (☐, ◐, ☑)
     - ✅ Optional onItemClick fires when item clicked
     - ✅ Accessible labels and ARIA attributes present
   - **CorpsDetailV2.test.tsx additions** (5+ cases)
     - ✅ Four lifecycle buttons (Go On Tour, Return to Camps, Ready for Contest, Complete Corps) do not exist in DOM
     - ✅ LifecycleStatusBar component mounts with correct props
     - ✅ PrepStatusPanel component mounts with correct props
     - ✅ Resume Hut, Attention, Metronome Tick, rehearsal toggles buttons present and clickable
     - ✅ No regression in existing OverviewTab functionality outside of button removal
   - **Snapshot tests:** Add for LifecycleStatusBar and PrepStatusPanel to detect unintended visual drift

5. **TypeScript Type Definitions**
   - File: `frontend/src/types/` (create or extend existing types file)
   - Export `CorpsLifecycleState` union type (literal strings: 'INITIALIZING' | 'WINTER_CAMPS' | 'ON_TOUR' | 'READY_FOR_CONTEST' | 'COMPLETED')
   - Export `LifecycleStatusBarProps` interface (all required and optional props)
   - Export `PrepStatusPanelProps` interface
   - Export `ReadinessCheckItem` interface
   - Ensure no `any` types; all generic parameters strict

6. **Verify TypeScript Compilation**
   - Run: `npm run type-check` (or `npx tsc --noEmit`)
   - Result: Zero errors, zero warnings

### Constraints

- **TypeScript:** `--strict` mode compliant; no `any` types in new components
- **Tests:** All existing tests pass; new test cases for all new components and changes
- **Behavior:**
  - Status bar: read-only, no click handlers, no state transitions from UI
  - Prep panel: visible only when `corps.state === 'WINTER_CAMPS'`
  - Operational buttons: preserved exactly as-is (no layout, styling, or behavior changes)
  - No breaking changes to CorpsDetailV2 parent props or public interface
- **Accessibility:** ARIA roles, semantic HTML, color contrast ≥4.5:1 (WCAG AA), keyboard navigation, screen-reader tested
- **Responsive:** Graceful layout adaptation to mobile/tablet/desktop viewports
- **Performance:** No unnecessary re-renders; React.memo() where beneficial

### Acceptance Criteria

1. ✅ **Button Removal:** DOM confirms zero instances of Go On Tour, Return to Camps, Ready for Contest, Complete Corps buttons
2. ✅ **Status Bar Rendering:** LifecycleStatusBar renders all five states left-to-right; current state visually highlighted (accent color, bold, filled icon)
3. ✅ **State Styling:** Completed states show checkmark + muted color; future states show outline placeholders + lighter text; no interactive affordances on any state
4. ✅ **Prep Panel Visibility:** PrepStatusPanel renders if `corps.state === 'WINTER_CAMPS'`; returns `null` in all other states
5. ✅ **Prep Panel Content:** Staffing bar displays "X of Y" accurately; readiness checklist displays all items with correct status icons
6. ✅ **Operational Commands:** Resume Hut, Attention, Metronome Tick, rehearsal toggles buttons present, clickable, and functionally unchanged
7. ✅ **TypeScript:** `npm run type-check` passes with zero errors; all new components fully typed
8. ✅ **Unit Tests:** All tests pass (existing + new); button removal verified; component integration verified; operational preservation verified
9. ✅ **No Regressions:** Existing CorpsDetailV2 functionality outside of removed buttons works identically to before
10. ✅ **Accessibility:** ARIA roles present; focus management working; screen-reader tested; color contrast compliant
11. ✅ **Responsiveness:** Components adapt gracefully to mobile, tablet, desktop viewports
12. ✅ **Read-Only Integrity:** Status bar and prep panel have no onClick, onSubmit, or form submission handlers (read-only display only)
