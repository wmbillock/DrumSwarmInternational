# Show Prompt: UI Usability Quick Start Tooltips Next-Action Badges CSS Fix

## Show Concept
Implement 5 integrated UI usability improvements for the DCI Swarm frontend: react-tooltip infrastructure, Command Center Quick Start guide, Show Library next-action badges, contextual tooltips across vitals/SideNav/Design Room, and MessageArchive.css completion. All adhering to Field Commander Brutalism aesthetic.

## Musical Design
Phased execution with clear dependencies:
- Phase 1: Install react-tooltip, add TooltipProvider in AppLayout.tsx. Black bg, white text, JetBrains Mono, no border-radius, 1px solid white border.
- Phase 2 (parallel): Quick Start guide in CommandCenter.tsx (7 steps, collapsible, localStorage dci-quickstart-dismissed) AND MessageArchive.css completion.
- Phase 3 (parallel): Show Library status badges in ShowLibrary.tsx AND tooltip rollout on vitals, SideNav, Design Room buttons.

## Visual Design
- Tooltips: black background, white text, JetBrains Mono font, no border-radius, 1px solid white border
- Quick Start: monospace step numbers, bordered cards, no rounded corners, collapsible header
- Badges: uppercase monospace text, 1px solid border, no border-radius. Colors by status: draft=yellow/black, needs_review=orange/black, approved=green/black, published=white/black
- MessageArchive: thread list, message cards, search input, bulk actions bar, empty states all styled to Brutalism patterns

## Guard Design
- Zero TypeScript errors (npx tsc --noEmit)
- Zero console errors in browser
- localStorage persistence for Quick Start dismissal
- Tooltips render on hover without layout shift
- MessageArchive.css produces no unstyled elements
- All badges display correct text and color per status

## General Effect
- New users see Quick Start guide on first visit to Command Center, can dismiss permanently
- Show Library communicates next action at a glance via status badges
- Tooltips provide contextual help without cluttering the UI
- MessageArchive looks complete and consistent with the rest of the app

## Constraints
- No breaking changes to existing components
- React 18+ compatible
- All new components must be accessible (aria labels, keyboard navigation)
- Field Commander Brutalism: JetBrains Mono for code/labels, IBM Plex Sans for body, stage colors only
- No border-radius anywhere

## Deliverables
- frontend/src/layouts/AppLayout.tsx - add react-tooltip TooltipProvider
- frontend/src/pages/CommandCenter.tsx - add Quick Start guide component
- frontend/src/pages/ShowLibrary.tsx - add next-action status badges
- frontend/src/pages/DesignRoom.tsx - add tooltips to action buttons
- frontend/src/components/SideNav.tsx - add tooltips to nav items
- frontend/src/styles/MessageArchive.css - complete all missing styles
- frontend/package.json - add react-tooltip dependency