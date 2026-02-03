# Season Workshop Redesign

## Goal
Full redesign of SeasonWorkshop.tsx with setup checklist flow. New backend endpoints. Updated season.yaml format.

## Acceptance Criteria
1. SeasonWorkshop detail view has a step-by-step checklist: Add Corps, Assign Shows (creates divisions), Competition Settings, Lock & Prepare, Start Tour
2. Registered corps shown by name not UUID
3. New backend endpoints: POST /seasons/{id}/shows, DELETE /seasons/{id}/shows/{slug}, POST /seasons/{id}/assign, PUT /seasons/{id}/config, POST /seasons/{id}/lock, POST /seasons/{id}/start-tour, GET /seasons/{id}/schedule, GET /seasons/{id}/standings
4. New Pydantic request models in schemas.py
5. Updated season.yaml format with shows, divisions, config (corps_per_contest, required_scores), schedule
6. season_persistence.py updated for new format
7. TypeScript compiles, tests pass