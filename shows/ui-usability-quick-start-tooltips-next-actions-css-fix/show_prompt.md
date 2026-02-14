## Objective

Deliver production-ready tooltip infrastructure, Quick Start onboarding, status badges, and MessageArchive CSS across Command Center, Show Library, Design Room, and MessageArchive—zero breaking changes, Field Commander Brutalism aesthetic, accessibility ≥95/100, all constraints honored.

## Deliverables

- **React-Tooltip Provider Component** — Install react-tooltip@5.x; create `TooltipProvider` wrapper in `AppLayout.tsx`; export `useTooltip` custom hook with 100ms delay, dark theme (#1a1a1a), monospace styling, max-width 200px, responsive positioning; zero console errors
- **Command Center Quick Start Panel** — 7-step collapsible guide (left sidebar above SideNav); icon + title + description (max 140 chars) + "Learn More" links; localStorage persistence key `cc_quick_start_dismissed` (boolean); dismiss button (X icon) with tooltip; graceful migration of old state
- **Show Library Status Badge Component** — Enum-driven badge system (DRAFT/RECORDING/EDITING/PUBLISHED/ARCHIVED); deployed to Show Library grid, Show Detail header, Design Room status bar; color-coded (gray/yellow/blue/green/red); optional next-action hints; WCAG AA contrast verified (≥4.5:1)
- **Tooltip Deployment Layer** — Tooltips on vitals cards (Command Center), SideNav items, Design Room buttons (with keyboard shortcuts), MessageArchive filter controls; 100ms delay; semantic HTML triggers; keyboard-accessible (Enter/Space to show, Escape to close); mobile long-press fallback
- **MessageArchive CSS Grid** — 12-column layout (16px gap); dark message cards (#0a0a0a) with monospace headers, 4px border-radius; hover shadow lift (0 4px 16px rgba(255, 255, 255, 0.1)); responsive 1–3 column breakpoints (mobile <768px / tablet 768–1023px / desktop ≥1024px); pagination controls; archive header; no layout shift on load
- **Design Room Button Suite** — Consistent button family (primary red #e74c3c, secondary border #f5f5f5, icon-only gray #7f8c8d); save/export/preview/undo/redo buttons; hover/active states with subtle opacity shift (+10%); focus visible on keyboard; tooltips with keyboard shortcut hints
- **Accessibility & QA Verification** — Zero console errors; TypeScript strict mode pass (`tsc --noEmit` no `@ts-ignore`); Lighthouse audit ≥95/100; cross-browser smoke test (Chrome, Firefox, Safari, Edge); mobile/tablet/desktop responsive rendering verified; all new strings marked for i18n

## Constraints

- **Phase 1 (React-Tooltip Infrastructure) is a critical blocker** — no other phases may begin until Phase 1 passes QA and zero console errors confirmed
- **Parallel execution authorized** — Phases 2 & 3 run in parallel after Phase 1 live; Phase 4 starts after Phase 1 QA; Phase 5 runs independent; Phase 6 starts after Phase 4 QA
- **No breaking changes** — all phases maintain backwards compatibility with existing API contracts, routing, and component props
- **No new npm dependencies** beyond react-tooltip@5.x; no new fonts, colors, or border-radius values outside the spec'd palette (4px/8px/16px grid, JetBrains