# Seasons & Standings UI

## Show Concept
Enhance the SeasonWorkshop page to include competition standings, score breakdowns, and recap views. The SeasonWorkshop page at frontend/src/pages/SeasonWorkshop.tsx currently has three tabs (Setup, Winter Camps, Ready Check). Add a fourth Standings tab that pulls competition data for the selected season and displays ranked results with sortable tables and expandable corps detail rows.

## Musical Design
The data rhythm follows the season lifecycle: seasons contain competitions, competitions contain scores, scores break down into captions. The Standings tab MUST load competitions filtered by seasonId, then for each completed competition fetch scores via v1.getScores(competitionId). Display results in a ranked table sorted by final_score descending by default. Each row shows: rank number, corps display name (resolved from corps list), caption scores for GE/Visual/Music, penalties, and final composite score. Column headers MUST be clickable to sort ascending/descending. Use the V1StandingEntry and V1Standings types from v1.ts.

## Visual Design
Follow the Field Commander Brutalism aesthetic established in the project. Headings and numeric data use JetBrains Mono (var(--font-display)). Labels and body text use IBM Plex Sans (var(--font-body)). Use stage color variables from App.css: --stage-amber for highlights, --bg-surface for panels, --border for dividers. Score cells MUST be right-aligned with monospace font. Rank column is narrow (40px). Corps name column takes remaining space. Caption score columns are fixed width (80px each). Use Badge components for competition status indicators. The expanded corps breakdown row MUST have a subtle background color (var(--bg-surface-raised) or similar) to distinguish it from normal rows.

## Guard Design
The recap sub-view renders full competition recap data from v1.getRecap(competitionId). Display as a formatted table matching the standings structure but with additional detail: per-caption rep and perf sub-scores shown in smaller text below the total. Add a toggle or secondary tab within Standings to switch between Standings view (ranked by final score) and Recap view (full detail). Clicking a corps row in either view expands an inline detail panel showing the output of v1.getCorpsBreakdown(competitionId, corpsId) with weighted caption scores and commentary if available.

## General Effect
The standings page MUST feel like a live scoreboard. Numbers should be prominent and scannable. The sorted column MUST have a visual indicator (arrow icon or bold header). Empty states (no competitions, no scores yet) MUST show helpful messages rather than blank space. Loading states MUST use skeleton placeholders or the existing page-loading pattern. Competition selector (if multiple competitions exist in the season) MUST be a clear dropdown or segmented control above the table.

## Constraints
- Use v1.ts API client exclusively: listCompetitions, getScores, getRecap, getCorpsBreakdown, listTapes
- Use existing UI components from frontend/src/ui/index.ts: Panel, Badge, DataTable, Tabs
- MUST NOT import from legacy api.ts
- MUST compile with npx tsc --noEmit (no TypeScript errors)
- MUST work with React hooks rules (all hooks before early returns)
- Modify only frontend/src/pages/SeasonWorkshop.tsx and optionally add a new StandingsPanel.tsx component in frontend/src/components/
- Add any needed CSS to frontend/src/App.css using existing variable conventions
- Do not modify backend code

## Deliverables
- Modified frontend/src/pages/SeasonWorkshop.tsx with Standings tab added
- Optional new component frontend/src/components/StandingsPanel.tsx if extracted
- CSS additions in frontend/src/App.css for standings-specific styles
- All files must pass TypeScript compilation

## Evaluation Rubric
- Standings tab appears and loads data correctly: 30 points
- Sortable columns work (click to toggle sort direction): 20 points
- Corps breakdown expand/collapse works: 15 points
- Recap view displays detailed score data: 15 points
- Visual design matches Field Commander Brutalism (fonts, colors, layout): 10 points
- Empty and loading states handled gracefully: 5 points
- TypeScript compiles without errors: 5 points