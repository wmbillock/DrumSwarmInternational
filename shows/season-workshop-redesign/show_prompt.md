## Show Concept
Redesign the Season Workshop page with a setup checklist flow and new backend endpoints for the full season lifecycle. Replace the current tab-based layout with a step-by-step guided setup.

## Musical Design
Backend changes in multiple files:

### backend/api/v1/seasons.py - New endpoints:
1. POST /api/v1/seasons/{season_id}/shows - Add a show to the season. Body: {show_slug: str}. Updates season.yaml shows list.
2. DELETE /api/v1/seasons/{season_id}/shows/{show_slug} - Remove a show from the season.
3. POST /api/v1/seasons/{season_id}/assign - Auto-assign corps to shows creating divisions. Body: {} (uses all registered corps and shows). Each corps-show pair = a division. Stores in season.yaml divisions map.
4. PUT /api/v1/seasons/{season_id}/config - Update competition settings. Body: {corps_per_contest: int, required_scores: int}. Stores in season.yaml config.
5. POST /api/v1/seasons/{season_id}/lock - Lock the season (no more changes to corps/shows/config). Sets status to locked.
6. POST /api/v1/seasons/{season_id}/start-tour - Transition all registered corps to ON_TOUR, set season status to on_tour.
7. GET /api/v1/seasons/{season_id}/schedule - Return generated competition schedule.
8. GET /api/v1/seasons/{season_id}/standings - Return current standings per division and overall.

### backend/api/v1/schemas.py - New models:
- AddSeasonShowRequest(show_slug: str)
- SeasonConfigRequest(corps_per_contest: int = 3, required_scores: int = 3)

### backend/services/season_persistence.py - Updated functions:
- Updated season.yaml format: add shows (list[str]), divisions (dict[str, list[str]] mapping show_slug to corps_ids), config (dict), schedule (list), standings (dict), status (str)
- add_show_to_season(), remove_show_from_season(), assign_divisions(), update_config(), lock_season(), get_schedule(), get_standings()

## Visual Design
Frontend: Rewrite frontend/src/pages/SeasonWorkshop.tsx detail view.

Replace the tab layout with a vertical checklist/stepper:

Step 1 - Add Corps: Show registered corps by display_name (resolve UUID via corps list). Button to add more corps.
Step 2 - Assign Shows: Dropdown/list to add published shows. Shows the resulting divisions (show -> corps list).
Step 3 - Competition Settings: Form for corps_per_contest (default 3) and required_scores (default 3).
Step 4 - Lock & Prepare: Button to lock. Shows validation summary.
Step 5 - Start Tour: Big button to start the tour. Transitions to tour view.

Each step shows a checkmark when complete. Steps are sequential - later steps are disabled until earlier ones are done.

Add API calls to v1.ts: addSeasonShow, removeSeasonShow, assignSeasonDivisions, updateSeasonConfig, lockSeason, startSeasonTour, getSeasonSchedule, getSeasonStandings.

## Guard Design
Validation on lock: must have at least 2 corps, at least 1 show, config must be set. Return clear error messages.

## General Effect
The setup checklist guides users through season creation step by step, making it impossible to miss required configuration.

## Constraints
- Keep the season list view as-is.
- The detail view replaces the current tab layout.
- Season.yaml backwards compatibility: old seasons without the new fields should still load.
- Use v1.ts for all frontend API calls.
- Do not break existing endpoints (list seasons, create season, delete season, register corps).

## Deliverables
- Modified backend/api/v1/seasons.py with 8 new endpoints
- Modified backend/api/v1/schemas.py with new request models
- Modified backend/services/season_persistence.py with new functions and format
- Rewritten frontend/src/pages/SeasonWorkshop.tsx detail view
- Modified frontend/src/services/v1.ts with new API calls

## Evaluation Rubric
- All 8 backend endpoints implemented and return correct data: 30 points
- Season.yaml format updated with backward compatibility: 15 points
- Frontend checklist UI renders correctly: 25 points
- Corps shown by name not UUID: 10 points
- v1.ts API calls added: 10 points
- TypeScript compiles and tests pass: 10 points