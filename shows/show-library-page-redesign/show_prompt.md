# Show Library Page Redesign

## Show Concept
Redesign the Show Library page (frontend/src/pages/ShowLibrary.tsx) to follow Field Commander Brutalism design language. Replace the current cluttered layout with a clean, scannable card grid that communicates show status through visual hierarchy rather than badge spam.

## Musical Design
N/A — This is a frontend UI task, not a musical composition.

## Visual Design
Lineup Board Brutalism direction:
- Hero cards with JetBrains Mono titles (24px bold) as primary anchor
- Left-edge color bars indicating status: PUBLISHED=#DC143C (crimson), APPROVED=#FFA500 (amber), DRAFT=#2D3436 (charcoal)
- IBM Plex Sans descriptions (14px, opacity 0.75, 2-3 lines max truncated)
- Bottom metadata strip: created date, spec indicator, last modified — monospaced, low contrast
- 2-column grid on desktop, 1-column on mobile
- Stats bar at top with stage palette colors and monospace numbers
- Hover: left bar grows 3px to 5px, color saturates
- Card bg #1A1A1A, text #F5F5F5, CTA gold #FFD700

## Guard Design
N/A — This is a frontend UI task.

## General Effect
The page should read like a competition stage roster — raw, legible from distance, with status dominance communicated visually through color position rather than text badges. Zero clutter. Information hierarchy: title dominates, description supports, metadata is footnote.

## Constraints
- Must maintain all existing functionality: search, filter by status, New Show button
- Must use existing Field Commander Brutalism design system variables (--font-heading, --font-body, stage colors)
- Remove raw slug display from cards
- Remove Assign Season dropdown from cards (move to detail view)
- Add show description/summary to each card
- Single file change preferred (ShowLibrary.tsx) unless v1.ts needs new fields

## Deliverables
- Updated ShowLibrary.tsx with redesigned layout
- Updated v1.ts if new API data is needed for descriptions
- All existing functionality preserved and working

## Evaluation Rubric
- Visual hierarchy: Title dominates, status is color-coded, metadata is subordinate (30%)
- Design system compliance: Uses JetBrains Mono, IBM Plex Sans, stage colors (20%)
- Decluttering: No slug display, no season dropdown on cards (20%)
- Functionality preserved: Search, filter, create all work (20%)
- Responsiveness: Works on desktop and mobile (10%)