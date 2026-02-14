# UI Usability: Quick Start, Tooltips, Next Actions, CSS Fix

## Show Concept
Five integrated UI/UX deliverables grounded in Field Commander Brutalism to improve user onboarding, task discoverability, and visual coherence. The spec balances infrastructure (React-tooltip provider), user guidance (Quick Start panel), content clarity (status badges), and visual polish (MessageArchive.css completion).

## Musical Design
N/A — This is a UI/UX infrastructure show, not a visual performance narrative.

## Visual Design
**Field Commander Brutalism Aesthetic**
- Monospace typography (JetBrains Mono, fallback: Courier New)
- High contrast: near-black (#0a0a0a) / near-white (#f5f5f5)
- Accent colors: red (#e74c3c) for warnings, green (#27ae60) for success, blue (#3498db) for info, yellow (#f39c12) for caution
- Minimal ornamentation; function-first layout
- Status badges: solid color fills with white text, 4px border-radius
- Tooltips: dark background (#1a1a1a), white text, monospace label, max-width 200px, 4px rounded corners, 8px padding
- SideNav: left-aligned, high-contrast text, icon + label pairs
- MessageArchive grid: CSS Grid 12-column layout, card-based message display, consistent spacing (16px gutters)

## Guard Design
**Content Safety & Accessibility**
- All interactive elements have `aria-label` and `aria-describedby` attributes
- Tooltip content is semantic HTML, not render prop abuse
- Quick Start dismissal is explicit (button), not accidental (click-outside)
- Status badges have sufficient color contrast (WCAG AA minimum)
- MessageArchive keyboard navigation enabled (Tab, Enter, Escape)
- No tooltip flicker or focus trap

**Data Integrity**
- Quick Start localStorage uses JSON serialization with try/catch error handling
- Tooltip state is ephemeral (no persistence)
- Badge status values are validated against a closed enum (DRAFT, RECORDING, EDITING, PUBLISHED, ARCHIVED)

## General Effect
Users immediately understand:
1. **Where to start** — Quick Start panel on first visit to Command Center
2. **What each element does** — Tooltips on vitals cards, SideNav shortcuts, Design Room buttons
3. **What state a show is in** — Status badges in Show Library (next action color-coded)
4. **How to organize messages** — MessageArchive CSS grid with clear card hierarchy

Success = reduced time-to-first-task, zero support questions about "what is this button?", accessibility audit ≥95/100.

## Constraints
- **No breaking changes** to existing page layouts, routing, or API contracts
- **React 18+ only** — no legacy Hooks patterns
- **All CSS uses existing design system variables** — no new color definitions outside the spec'd palette
- **Performance budgets maintained** — tooltip library < 15KB gzipped, Quick Start state < 1KB
- **TypeScript strict mode** — all new code compiles without `@ts-ignore`
- **Backwards compatible** — users with old localStorage Quick Start state migrate gracefully
- **Single source of truth for badges** — enum-driven, shared across Show Library + Show Detail + Design Room

## Deliverables

### 1. React-Tooltip Infrastructure (Critical Path)
- Install `react-tooltip@5.x` and `@types/react-tooltip`
- Create `TooltipProvider` wrapper in `AppLayout.tsx`
- Export `useTooltip` custom hook for ease of use
- Zero console errors; no style collisions with existing Tailwind
- Responsive positioning (no overflow off-viewport)
- **Acceptance**: Provider renders without error, tooltips appear on hover/focus

### 2. Command Center Quick Start Guide (High-Impact UX)
- Collapsible 7-step guide panel in Command Center (left sidebar, above existing content)
- Each step: icon + title + description (max 140 chars) + optional "Learn More" link
- localStorage key: `cc_quick_start_dismissed` (boolean)
- Dismiss button (X icon, tooltip "Don't show this again") clears state and collapses panel
- Panel re-appears on next session if not dismissed
- Styling: dark background (#1a1a1a), step indicators (numbered badges), monospace labels
- **Acceptance**: Panel persists across page reload, dismissal survives refresh, zero errors

### 3. Show Library Status Badges (Content Clarity)
- Enum-driven badge system: `DRAFT` (gray #7f8c8d), `RECORDING` (yellow #f39c12), `EDITING` (blue #3498db), `PUBLISHED` (green #27ae60), `ARCHIVED` (red #e74c3c)
- Badge placement: Show Library grid, top-right of each show card
- Badge includes status label + next-action hint (e.g., "RECORDING — waiting for input" vs "PUBLISHED — ready to archive")
- Consistent styling across Show Library, Show Detail header, Design Room status bar
- **Acceptance**: All shows display correct badge; color contrast ≥4.5:1; badge text matches defined enum values

### 4. Tooltip Deployment Across Key Interactive Elements
- **Vitals cards** (Command Center): tooltip on each metric (e.g., "Shows in progress — click to filter by status")
- **SideNav items** (left navigation): tooltip on icon-only shortcuts (e.g., "New Show", "Show Library", "Messages")
- **Design Room buttons** (save, export, preview, undo/redo): tooltip on each action button with keyboard shortcut hint
- **MessageArchive search/filter buttons**: tooltip explaining filter syntax
- All tooltips: 100ms delay, monospace label, semantic HTML trigger, keyboard-accessible (Enter/Space to show)
- **Acceptance**: All tooltips render without flicker; no focus traps; keyboard navigation works; mobile-friendly (long-press fallback)

### 5. MessageArchive.css Completion
- CSS Grid 12-column layout (gap: 16px)
- Message card styling: dark background, white text, monospace headers, 4px border-radius, hover state (subtle shadow lift)
- Responsive breakpoints: 1 col (mobile), 2 col (tablet), 3 col (desktop ≥1024px)
- Pagination controls: styled to match Field Commander Brutalism (monospace, high-contrast buttons)
- Archive header: "Messages" title + sort/filter controls + clear button
- **Acceptance**: Grid displays all messages without overflow; pagination functional; mobile rendering responsive; no layout shift on load

### 6. Design Room Button Styling (Polish)
- Consistent button family: primary (red accent), secondary (monospace border), icon-only (with tooltip)
- Save/export/preview buttons: red accent background, white text, monospace label, 4px corners
- Undo/redo buttons: gray border, monospace icons, tooltip with keyboard shortcut (Ctrl+Z / Ctrl+Shift+Z)
- Hover/active states: slight background shift, no transition lag
- **Acceptance**: All buttons styled consistently; no orphan button styles; keyboard focus visible

### 7. General Polish & QA
- Zero console errors or warnings
- TypeScript strict mode: `"strict": true` passes
- Accessibility audit (Lighthouse) ≥95/100
- Pixel-perfect rendering matches design system variables
- No new fonts or colors introduced outside the spec'd palette

## Swarm Prompt

### Objective
Deliver production-ready tooltip infrastructure, Quick Start onboarding, status badges, and MessageArchive CSS across Command Center, Show Library, Design Room, and MessageArchive—zero breaking changes, Field Commander Brutalism aesthetic, accessibility ≥95/100.

### Deliverables

**Phase 1: Infrastructure (Blocker for Phases 2–5)**
1. Install & configure `react-tooltip@5.x` with provider in `AppLayout.tsx`
2. Export `useTooltip` custom hook with sensible defaults (100ms delay, monospace styling)
3. Verify zero console errors and no Tailwind style collisions

**Phase 2: Quick Start Onboarding (Parallel with Phase 3)**
1. Create `QuickStartPanel.tsx` component (7-step collapsible guide)
2. Implement localStorage persistence (`cc_quick_start_dismissed`)
3. Style with dark background (#1a1a1a), numbered step indicators, monospace labels
4. Test dismissal → re-appear on next session

**Phase 3: Status Badges (Parallel with Phase 2)**
1. Define badge enum: `DRAFT | RECORDING | EDITING | PUBLISHED | ARCHIVED`
2. Create `StatusBadge.tsx` component with color mapping
3. Deploy to Show Library, Show Detail header, Design Room status bar
4. Verify color contrast ≥4.5:1 (WCAG AA)

**Phase 4: Tooltip Deployment (Runs after Phase 1)**
1. Add tooltips to vitals cards (Command Center)
2. Add tooltips to SideNav items (icon-only shortcuts)
3. Add tooltips to Design Room buttons (save, export, preview, undo/redo with shortcut hints)
4. Add tooltips to MessageArchive search/filter buttons
5. Verify keyboard accessibility (Enter/Space to trigger, no focus trap)

**Phase 5: MessageArchive CSS (Independent)**
1. Rewrite MessageArchive layout as CSS Grid (12-column, 16px gap)
2. Style message cards: dark background, white text, monospace headers, 4px radius, hover lift
3. Implement responsive breakpoints (1/2/3 col for mobile/tablet/desktop)
4. Style pagination controls and archive header
5. Test pagination functional end-to-end

**Phase 6: Design Room Button Styling (Polish, runs after Phase 4)**
1. Unify button family: primary (red accent), secondary (border), icon-only (with tooltip)
2. Apply consistent hover/active states (subtle background shift, no lag)
3. Ensure undo/redo buttons include keyboard shortcut hints in tooltips

**Phase 7: QA & Validation**
1. Run Lighthouse accessibility audit → ≥95/100
2. Verify zero console errors/warnings
3. TypeScript strict mode check (`"strict": true`)
4. Pixel-perfect rendering test against design variables
5. Cross-browser smoke test (Chrome, Firefox, Safari)
6. Mobile/tablet responsive check (all components)

### Constraints
- **No breaking changes** — all existing functionality must work unchanged
- **React 18+ only** — no legacy Hook patterns
- **Design system variables only** — no new colors outside the spec'd palette (red #e74c3c, green #27ae60, blue #3498db, yellow #f39c12, gray #7f8c8d, dark #1a1a1a/#0a0a0a, light #f5f5f5)
- **TypeScript strict mode** — all new code compiles without `@ts-ignore`
- **Performance budgets** — react-tooltip library < 15KB gzipped, Quick Start localStorage < 1KB
- **Backwards compatibility** — users with old Quick Start state migrate gracefully

### Acceptance Criteria
1. ✅ Tooltip provider renders in `AppLayout`, zero errors
2. ✅ Quick Start panel persists across sessions (localStorage) and dismissal is explicit
3. ✅ Status badges display correct colors; all enum values validated
4. ✅ All interactive elements (vitals, SideNav, Design Room, MessageArchive) have tooltips
5. ✅ Tooltips trigger on hover/focus; keyboard-accessible (Enter/Space); no focus trap
6. ✅ MessageArchive grid displays all messages (12-col layout, responsive breakpoints)
7. ✅ Design Room buttons styled consistently; undo/redo show keyboard shortcuts
8. ✅ Zero console errors/warnings; TypeScript strict mode passes
9. ✅ Lighthouse accessibility audit ≥95/100
10. ✅ Pixel-perfect rendering matches Field Commander Brutalism aesthetic
11. ✅ All components tested on mobile, tablet, desktop; responsive layout verified