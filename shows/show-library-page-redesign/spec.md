# Show Library Page Redesign

## Goal
Redesign ShowLibrary.tsx to follow Field Commander Brutalism design language. Replace cluttered layout with clean, scannable card grid communicating status through visual hierarchy.

## Acceptance Criteria
1. Hero cards with JetBrains Mono titles (24px bold) as primary anchor
2. Left-edge color bars indicating status: PUBLISHED=#DC143C, APPROVED=#FFA500, DRAFT=#2D3436
3. IBM Plex Sans descriptions (14px, opacity 0.75, 2-3 lines max truncated)
4. Bottom metadata strip: created date, spec indicator, last modified in monospace
5. 2-column grid desktop, 1-column mobile
6. Stats bar at top with stage palette colors and monospace numbers
7. Hover: left bar grows 3px to 5px, color saturates
8. Card bg #1A1A1A, text #F5F5F5, CTA gold #FFD700
9. All existing functionality preserved: search, filter by status, New Show button
10. Remove raw slug display and Assign Season dropdown from cards
11. TypeScript compiles clean

## Constraints
- Single file change preferred (ShowLibrary.tsx) unless v1.ts needs new fields
- Must use existing Field Commander Brutalism design system variables
- Remove raw slug display from cards
- Remove Assign Season dropdown from cards (move to detail view)