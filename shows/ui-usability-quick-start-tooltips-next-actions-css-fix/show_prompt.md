### Objective

Deliver production-ready tooltip infrastructure, Quick Start onboarding, status badges, and MessageArchive CSS across Command Center, Show Library, Design Room, and MessageArchive—zero breaking changes, Field Commander Brutalism aesthetic, accessibility ≥95/100, all constraints honored.

### Deliverables

- **React-Tooltip Provider** — `TooltipProvider` wrapper in `AppLayout.tsx` with `useTooltip` hook (100ms delay, dark theme #1a1a1a, monospace styling, max-width 200px); zero console errors; responsive positioning on mobile
- **Quick Start Panel** — 7-step collapsible guide (left sidebar above SideNav); localStorage persistence (`cc_quick_start_dismissed` boolean); dismiss button clears state; graceful migration of old state
- **Status Badge Component** — Enum-driven badge system (DRAFT/RECORDING/EDITING/PUBLISHED/ARCHIVED); deployed to Show Library, Show Detail header, Design Room status bar; color-coded with next-action hints; WCAG AA contrast verified
- **Tooltip Deployment** — Tooltips on vitals cards, SideNav items, Design Room buttons (with keyboard shortcuts), MessageArchive filters; 100ms delay; semantic HTML triggers; keyboard-accessible (Enter/Space to show, Escape to close)
- **MessageArchive CSS Grid** — 12-column layout (16px gap); dark message cards (#0a0a0a) with monospace headers; hover shadow lift; responsive 1–3 column breakpoints (<768px / 768–1023px / ≥1024px); pagination controls; no layout shift on load
- **Design Room Button Suite** — Consistent button family (primary red #e74c3c, secondary border #f5f5f5, icon-only gray #7f8c8d); hover/active states with subtle opacity shift; focus visible on keyboard; tooltips with keyboard shortcut hints
- **Accessibility & QA Verification** — Zero console errors; TypeScript strict mode pass; Lighthouse audit ≥95/100; cross-browser smoke test (Chrome, Firefox, Safari, Edge); mobile/tablet/desktop responsive rendering; all strings marked for i18n

### Constraints

- **Phase 1 (Infrastructure) is a critical blocker** — no other phases begin until Phase 1 passes QA and zero console errors confirmed
- **Parallel execution authorized** — Phases 2 & 3 run in parallel after Phase 1 live; Phase 4 starts after Phase 1 QA; Phase 5 runs independent; Phase 6 starts after Phase 4 QA
- **No breaking changes** — all phases maintain backwards compatibility; existing API contracts, routing, and component props untouched
- **No new npm dependencies** beyond `react-tooltip@5.x`; no new fonts, colors, or border-radius values outside 4px/8px/16px grid
- **TypeScript strict mode required** — all new code passes `tsc --noEmit` without `@ts-ignore` or implicit `any`
- **Performance budgets** — react-tooltip < 15KB gzipped; Quick Start state < 1KB; MessageArchive grid render < 100ms for 100 messages
- **Backwards compatibility** — localStorage/sessionStorage migration must gracefully handle old state; invalid badge enums fallback to DRAFT with dev warning only
- **Tailwind CSS preservation** — no overrides; all new styles use CSS classes or inline styles that respect existing Tailwind utilities
- **All new strings marked for i18n** — prepared for translation (English-only at ship, but infrastructure ready)

### Acceptance Criteria

**Phase 1: Infrastructure (MUST PASS before other phases proceed)**

- [ ] `react-tooltip@5.x` installed; zero version conflicts in `package.