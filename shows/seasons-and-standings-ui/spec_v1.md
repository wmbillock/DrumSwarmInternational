# Brief: Seasons & Standings UI

## Problem
The SeasonWorkshop page has Setup, Winter Camps, and Ready Check tabs but no Standings or Competition Results tab. Users cannot view competition scores, rankings, or caption breakdowns within the season UI.

## Goal
Add a Standings tab to SeasonWorkshop.tsx that displays ranked competition results with sortable tables, caption score breakdowns, and drill-down to per-corps tape details.

## Scope
1. Add a Standings tab to SeasonWorkshop.tsx showing competition results for the selected season
2. Within Standings, list all competitions for that season with their status
3. For completed competitions, show a ranked table: Rank, Corps Name, Caption Scores (GE, Visual, Music), Penalties, Final Score
4. Table must be sortable by any column (click column header to toggle asc/desc)
5. Clicking a corps row expands to show detailed breakdown using getCorpsBreakdown()
6. Add a Recap sub-view that renders getRecap() data in a formatted table
7. Use existing v1.ts functions: listCompetitions, getScores, getRecap, getCorpsBreakdown, listTapes
8. Follow Field Commander Brutalism aesthetic: JetBrains Mono for headings/data, IBM Plex Sans for labels, stage colors from App.css
9. Use existing UI components (Panel, Badge, DataTable, Tabs) from ../ui

## Acceptance Criteria
- SeasonWorkshop has 4 tabs: Setup, Winter Camps, Ready Check, Standings
- Standings tab loads competitions for the current season and displays scores
- Score table is sortable by clicking column headers
- Corps breakdown is accessible from the standings table
- Recap view shows full competition recap
- All data comes from v1.ts API client
- TypeScript compiles with no errors
- Responsive layout at 1024px+