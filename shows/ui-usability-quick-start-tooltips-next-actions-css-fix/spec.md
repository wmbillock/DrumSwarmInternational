```markdown
# UI Usability: Quick Start, Tooltips, Next Actions, CSS Fix

## Show Concept

Five integrated UI/UX deliverables grounded in Field Commander Brutalism to improve user onboarding, task discoverability, and visual coherence. The spec balances infrastructure (React-tooltip provider), user guidance (Quick Start panel), content clarity (status badges), and visual polish (MessageArchive.css completion). This show runs in the Command Center, Show Library, Design Room, and MessageArchive—each a stage where users need immediate clarity on "where to start," "what this does," "what state we're in," and "how to navigate."

The show executes in strict waterfall for Phase 1 (infrastructure blocker), then runs Phases 2–3 in parallel once the provider is live, enabling rapid badge and tooltip deployment across all UI surfaces. Phase 4 (tooltip decoration) follows Phase 1 QA; Phase 5 (MessageArchive CSS) runs independent; Phase 6 (button polish) completes the suite.

## Musical Design

N/A — This is a UI/UX infrastructure show, not a visual performance narrative. The "rhythm" of this show is **cognitive clarity**: users encounter Quick Start → status badges → tooltips → MessageArchive organization in a natural progression that teaches the application semantics through immediate visual feedback and next-action hints.

## Visual Design

**Field Commander Brutalism Aesthetic**

- **Typography**: JetBrains Mono, fallback Courier New; all labels in caps for status badges and button hints
- **Color Palette**:
  - Near-black: #0a0a0a (backgrounds, text on light)
  - Near-white: #f5f5f5 (text on dark, light surfaces)
  - Dark gray: #1a1a1a (tooltip backgrounds, panel backgrounds)
  - Gray: #7f8c8d (DRAFT badge, secondary UI)
  - Red: #e74c3c (warnings, ARCHIVED badge, primary buttons)
  - Yellow: #f39c12 (caution, RECORDING badge)
  - Blue: #3498db (info, EDITING badge)
  - Green: #27ae60 (success, PUBLISHED badge)
- **Spacing**: 16px grid gutters (MessageArchive, Quick Start steps), 8px internal padding (badges, tooltips)
- **Border Radius**: 4px on all cards, badges, tooltip containers, buttons
- **Status Badges**:
  - Solid color fill with white (#f5f5f5) text
  - Monospace label (e.g., "DRAFT", "RECORDING", "PUBLISHED")
  - Optional next-action hint below label (e.g., "waiting for input", "ready to archive")
  - 4px border-radius, 8px horizontal padding, 4px vertical padding
- **Tooltips**:
  - Dark background (#1a1a1a), white text (#f5f5f5)
  - Monospace label, max-width 200px
  - 4px rounded corners, 8px padding
  - 100ms hover delay
  - Keyboard-accessible (Enter/Space to trigger)
- **Quick Start Panel**:
  - Left sidebar (above existing SideNav content)
  - Dark background (#1a1a1a), white text
  - Step indicators: numbered badge (1–7), monospace font
  - Each step: icon + title + description (max 140 chars) + optional "Learn More" link
  - Dismiss button (X icon) with tooltip "Don't show this again"
  - Collapsible/expandable state
- **MessageArchive Grid**:
  - CSS Grid 12-column layout, 16px gap
  - Message cards: dark background (#0a0a0a), white text, monospace headers, 4px border-radius
  - Hover state: subtle shadow lift (box-shadow: 0 4px 16px rgba(255, 255, 255, 0.1))
  - Responsive: 1 col (mobile <768px), 2 col (tablet 768–1023px), 3 col (desktop ≥1024px)
- **Design Room Buttons**:
  - Primary: red accent (#e74c3c) background, white text, monospace label, 4px corners
  - Secondary: monospace border (#f5f5f5), transparent background, hover lift
  - Icon-only: gray background (#7f8c8d), white icon, tooltip on hover
  - Undo/Redo: gray border, monospace icons, tooltip with keyboard shortcut (Ctrl+Z / Ctrl+Shift+Z)
  - Hover/active: slight background shift (opacity +10%), no transition lag

## Guard Design

**Content Safety & Accessibility**

- All interactive elements have `aria-label` and `aria-describedby` attributes
- Tooltip content is semantic HTML, not render prop abuse
- Quick Start dismissal is explicit (button click), not accidental (click-outside)
- Status badges have sufficient color contrast (WCAG AA minimum, 4.5:1 ratio verified)
- MessageArchive keyboard navigation enabled (Tab, Enter, Escape)
- No tooltip flicker or focus trap; Escape key closes all tooltips
- Focus indicators visible on all interactive elements (outline or border highlight)
- Modal or trap-free: tooltips do not prevent keyboard navigation or form submission

**Data Integrity**

- Quick Start localStorage uses JSON serialization with try/catch error handling
  - Key: `cc_quick_start_dismissed` (boolean)
  - Fallback: if localStorage unavailable, panel displays but doesn't persist
  - Migration: users with old state structures migrate gracefully (reset to default)
- Tooltip state is ephemeral (no persistence, in-memory only)
- Badge status values are validated against a closed enum: `DRAFT | RECORDING | EDITING | PUBLISHED | ARCHIVED`
  - Invalid status values render as DRAFT with console warning (dev only)
- MessageArchive filter/sort state persists to sessionStorage (cleared on tab close)
- All user input in MessageArchive search/filter sanitized before display (no XSS risk)

## General Effect

Users immediately understand:

1. **Where to start** — Quick Start panel on first visit to Command Center, 7 clear steps with icons and "Learn More" links
2. **What each element does** — Tooltips on vitals cards (hover/focus), SideNav shortcuts (icon-only), Design Room buttons (with keyboard shortcut hints)
3. **What state a show is in** — Status badges in Show Library, Show Detail header, and Design Room status bar (color-coded next action)
4. **How to organize messages** — MessageArchive CSS grid with clear card hierarchy, pagination, and filter controls
5. **Why buttons matter** — Design Room buttons styled distinctly (primary red, secondary border, icon-only with tooltips)

**Success metrics:**

- Reduced time-to-first-task by ≥30% (measured by analytics on Quick Start interactions)
- Zero support questions about "what is this button?" or "what state am I in?"
- Accessibility audit ≥95/100 (Lighthouse)
- Mobile/tablet/desktop responsive rendering verified (no layout shift on load)
- Keyboard navigation fully functional (no mouse required)

## Constraints

- **No breaking changes** to existing page layouts, routing, API contracts, or component props
- **React 18+ only** — no legacy Hooks patterns, no deprecated lifecycle methods
- **Design system variables only** — no new color definitions outside the spec'd palette (red, green, blue, yellow, gray, dark, light)
- **Performance budgets maintained**:
  - react-tooltip library < 15KB gzipped
  - Quick Start state (localStorage) < 1KB
  - MessageArchive grid render time < 100ms for 100 messages
- **TypeScript strict mode** — all new code compiles without `@ts-ignore`; no implicit `any`
- **Backwards compatibility** — users with old localStorage Quick Start state migrate gracefully (no errors, default to panel shown)
- **Single source of truth for badges** — enum-driven, shared across Show Library + Show Detail + Design Room
- **No additional npm dependencies** beyond react-tooltip@5.x (no new icon libraries, form libraries, etc.)
- **Existing Tailwind CSS must not be overridden** — all new styles use CSS classes or inline styles that respect Tailwind utility classes
- **All new strings are marked for i18n** (prepared for future translation, but English-only at ship)
- **Strict waterfall for Phase 1** — no other phases may begin until infrastructure QA passes
- **Parallel execution allowed** — Phases 2 & 3 may run in parallel once Phase 1 is live; Phase 4 starts after Phase 1 QA; Phase 5 runs independent; Phase 6 starts after Phase 4 QA

## Deliverables

### Phase 1: React-Tooltip Infrastructure (Critical Path)

- Install `react-tooltip@5.x` and `@types/react-tooltip`
- Create `TooltipProvider` wrapper in `AppLayout.tsx` (wraps entire app)
- Export `useTooltip` custom hook for sensible defaults (100ms delay, dark theme, monospace styling)
- Zero console errors; no style collisions with existing Tailwind
- Responsive positioning (no overflow off-viewport on mobile; smart reposition on scroll)

### Phase 2: Command Center Quick Start Guide (Parallel with Phase 3 after Phase 1 QA)

- Collapsible 7-step guide panel in Command Center (left sidebar, above existing content)
- Each step: icon + title + description (max 140 chars) + optional "Learn More" link
- localStorage key: `cc_quick_start_dismissed` (boolean)
- Dismiss button (X icon, tooltip "Don't show this again") clears state and collapses panel
- Panel re-appears on next session if not dismissed
- Styling: dark background (#1a1a1a), step indicators (numbered badges 1–7), monospace labels, 16px padding

### Phase 3: Show Library Status Badges (Parallel with Phase 2 after Phase 1 QA)

- Enum-driven badge system: `DRAFT` (gray #7f8c8d), `RECORDING` (yellow #f39c12), `EDITING` (blue #3498db), `PUBLISHED` (green #27ae60), `ARCHIVED` (red #e74c3c)
- Badge placement: Show Library grid (top-right of each show card), Show Detail header, Design Room status bar
- Badge includes status label + optional next-action hint (e.g., "RECORDING — waiting for input" vs "PUBLISHED — ready to archive")
- Consistent styling across all three locations (no variations)
- Color contrast ≥4.5:1 (WCAG AA verified)

### Phase 4: Tooltip Deployment Across Key Interactive Elements (After Phase 1 QA)

- **Vitals cards** (Command Center): tooltip on each metric (e.g., "Shows in progress — click to filter by status")
- **SideNav items** (left navigation): tooltip on icon-only shortcuts (e.g., "New Show", "Show Library", "Messages")
- **Design Room buttons** (save, export, preview, undo/redo): tooltip on each action button with keyboard shortcut hint
- **MessageArchive search/filter buttons**: tooltip explaining filter syntax (e.g., "Filter by keyword or status")
- All tooltips: 100ms delay, monospace label, semantic HTML trigger, keyboard-accessible (Enter/Space to show, Escape to close)
- Mobile fallback: long-press opens tooltip (if supported by react-tooltip)

### Phase 5: MessageArchive.css Completion (Independent, may run in parallel)

- CSS Grid 12-column layout (gap: 16px)
- Message card styling: dark background (#0a0a0a), white text (#f5f5f5), monospace headers, 4px border-radius, hover state (subtle shadow lift)
- Responsive breakpoints: 1 col (mobile <768px), 2 col (tablet 768–1023px), 3 col (desktop ≥1024px)
- Pagination controls: styled to match Field Commander Brutalism (monospace, high-contrast buttons, no rounded corners or gradients)
- Archive header: "Messages" title + sort/filter controls + clear button (all aligned left, monospace font)
- No layout shift on load; all grid cells consistent height

### Phase 6: Design Room Button Styling (After Phase 4 QA)

- Consistent button family: primary (red accent #e74c3c), secondary (monospace border #f5f5f5), icon-only (gray #7f8c8d with tooltip)
- Save/export/preview buttons: red accent background, white text, monospace label, 4px corners
- Undo/redo buttons: gray border, monospace icons, tooltip with keyboard shortcut (Ctrl+Z / Ctrl+Shift+Z)
- Hover/active states: subtle background shift (+10% opacity), no transition lag
- Focus visible: outline or border highlight on keyboard focus

### Phase 7: General Polish & QA

- Zero console errors or warnings (including deprecation warnings)
- TypeScript strict mode: `"strict": true` passes all files
- Accessibility audit (Lighthouse) ≥95/100
- Pixel-perfect rendering matches design system variables (color hex verified)
- No new fonts or colors introduced outside the spec'd palette
- Cross-browser smoke test (Chrome, Firefox, Safari, Edge)
- Mobile/tablet/desktop responsive rendering verified (no layout shift)
- All new strings prepared for i18n (even if English-only at ship)

---

## Swarm Prompt

### Objective

Deliver production-ready tooltip infrastructure, Quick Start onboarding, status badges, and MessageArchive CSS across Command Center, Show Library, Design Room, and MessageArchive—zero breaking changes, Field Commander Brutalism aesthetic, accessibility ≥95/100, all constraints honored.

### Deliverables

- **React-Tooltip Provider Component** — Install react-tooltip@5.x; create `TooltipProvider` wrapper in `AppLayout.tsx`; export `useTooltip` custom hook with 100ms delay, dark theme (#1a1a1a), monospace styling, max-width 200px, responsive positioning; zero console errors
- **Command Center Quick Start Panel** — 7-step collapsible guide (left sidebar above SideNav); icon + title + description (max 140 chars) + "Learn More" links; localStorage persistence key `cc_quick_start_dismissed` (boolean); dismiss button (X icon) with tooltip; graceful migration of old state
- **Show Library Status Badge Component** — Enum-driven badge system (DRAFT/RECORDING/EDITING/PUBLISHED/ARCHIVED); deployed to Show Library grid, Show Detail header, Design Room status bar; color-coded (gray/yellow/blue/green/red); optional next-action hints; WCAG AA contrast verified (≥4.5:1)
- **Tooltip Deployment Layer** — Tooltips on vitals cards (Command Center), SideNav items, Design Room buttons (with keyboard shortcuts), MessageArchive filter controls; 100ms delay; semantic HTML triggers; keyboard-accessible (Enter/Space to show, Escape to close); mobile long-press fallback
- **MessageArchive CSS Grid** — 12-column layout (16px gap); dark message cards (#0a0a0a) with monospace headers, 4px border-radius; hover shadow lift (0 4px 16px rgba(255, 255, 255, 0.1)); responsive 1–3 column breakpoints (mobile <768px / tablet 768–1023px / desktop ≥1024px); pagination controls; archive header; no layout shift on load
- **Design Room Button Suite** — Consistent button family (primary red #e74c3c, secondary border #f5f5f5, icon-only gray #7f8c8d); save/export/preview/undo/redo buttons; hover/active states with subtle opacity shift (+10%); focus visible on keyboard; tooltips with keyboard shortcut hints
- **Accessibility & QA Verification** — Zero console errors; TypeScript strict mode pass (`tsc --noEmit` no `@ts-ignore`); Lighthouse audit ≥95/100; cross-browser smoke test (Chrome, Firefox, Safari, Edge); mobile/tablet/desktop responsive rendering verified; all new strings marked for i18n

### Constraints

- **Phase 1 (React-Tooltip Infrastructure) is a critical blocker** — no other phases may begin until Phase 1 passes QA and zero console errors confirmed
- **Parallel execution authorized** — Phases 2 & 3 run in parallel after Phase 1 live; Phase 4 starts after Phase 1 QA; Phase 5 runs independent; Phase 6 starts after Phase 4 QA
- **No breaking changes** — all phases maintain backwards compatibility with existing API contracts, routing, and component props
- **No new npm dependencies** beyond react-tooltip@5.x; no new fonts, colors, or border-radius values outside the spec'd palette (4px/8px/16px grid, JetBrains