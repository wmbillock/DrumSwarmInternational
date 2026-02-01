# Seasons & Standings UI

## Overview

Build frontend pages for season management and competition standings display, connecting to existing V1 API season/competition endpoints.

## Acceptance Criteria

1. **Seasons list page**: Display all seasons with create/edit controls, registered corps counts, and status.
2. **Season detail page**: Show season metadata, registered corps, and linked competitions.
3. **Standings view**: Ranked table of corps scores within a season, updated after each competition run.
4. **Competition results**: Per-competition score breakdown with caption scores, penalties, and composite totals.
5. **Navigation**: Seasons accessible from main nav, with drill-down to standings and competition results.

## Constraints

- Use v1.ts API client exclusively (listSeasons, getSeason, listCompetitions, getScores, getCorpsBreakdown)
- Follow existing frontend patterns (React + TypeScript)
- Responsive layout for desktop and tablet

## Deliverables

- SeasonsPage.tsx with CRUD controls
- SeasonDetail.tsx with standings table
- CompetitionResults.tsx with score breakdowns
- Navigation updates in App.tsx
