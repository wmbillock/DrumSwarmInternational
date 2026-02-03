## Show Concept
When a season is on tour, the SeasonWorkshop page should show a rich tour status view with schedule timeline, division standings, and rankings.

## Musical Design
No new backend endpoints - this show uses the endpoints created by the Season Workshop Redesign and Tour Coordinator shows (GET /seasons/{id}/schedule, GET /seasons/{id}/standings, GET /seasons/{id}/tour-status).

## Visual Design
Frontend changes:

### frontend/src/pages/SeasonWorkshop.tsx
When the season status is on_tour, replace the setup checklist with a tour dashboard view:
- Summary bar: current round / total rounds, corps count, scores recorded
- TourSchedule component (below)
- Division standings tables
- Overall rankings table
- Advance Round button (calls POST /seasons/{id}/advance)
- Enter Finals button (when all rounds complete, calls POST /seasons/{id}/enter-finals)

### New: frontend/src/components/TourSchedule.tsx
A visual schedule timeline component:
- Horizontal timeline with round markers
- Each round shows which corps competed
- Color code by division (each show/division gets a unique color)
- Past rounds show scores, current round pulses, future rounds are dimmed
- Click a round to see detail (corps, scores, results)
- Responsive layout for many rounds

Styling: Field Commander Brutalism - sharp borders, monospace numbers, accent color highlights, dark background.

### frontend/src/services/v1.ts
Add if not already present: getSeasonTourStatus, advanceSeason API calls.

## Guard Design
Handle loading states for schedule and standings data. Show skeleton/loading states while fetching. Handle empty schedule gracefully.

## General Effect
The tour status view transforms the season workshop into a live competition tracker. Users can watch their season progress round by round.

## Constraints
- Do not modify backend code - use existing endpoints.
- Use v1.ts for all API calls.
- The tour view replaces the setup checklist when status is on_tour - do not show both.
- Keep the season list view unchanged.

## Deliverables
- Modified frontend/src/pages/SeasonWorkshop.tsx with tour status view
- New frontend/src/components/TourSchedule.tsx
- Modified frontend/src/services/v1.ts with new API calls if needed

## Evaluation Rubric
- Tour status view renders when status=on_tour: 25 points
- TourSchedule component with timeline visualization: 30 points
- Division standings and rankings display: 20 points
- Advance Round and Enter Finals buttons work: 15 points
- TypeScript compiles clean: 10 points