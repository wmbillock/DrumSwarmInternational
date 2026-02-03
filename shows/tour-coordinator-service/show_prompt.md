## Show Concept
Create a tour coordinator service that generates competition schedules and manages competition rounds. This is the core engine that runs the tour.

## Musical Design
New file: backend/services/tour_coordinator.py

### generate_schedule(season_dir, config) -> list[dict]
Inputs: season directory path, config dict with corps_per_contest and required_scores.
Reads season.yaml for divisions (show_slug -> corps_ids mapping).
Algorithm:
- Each corps needs required_scores appearances total.
- Each competition slot has corps_per_contest corps, randomly selected from ANY division (cross-divisional).
- Generate enough rounds so every corps gets at least required_scores appearances.
- Return list of rounds, each round is a list of competition slots: {round: int, slot: int, corps_ids: list[str], show_slugs: list[str]}.
- Write schedule to season.yaml.

### run_competition_round(season_dir, round_number, db, llm_client) -> dict
- Load the round from schedule.
- For each competition slot in the round:
  - Create a competition via the existing competition creation logic.
  - Run it (dispatch corps, generate scores).
  - Update standings.
- After scoring:
  - Corps NOT in first place: trigger full self-improvement cycle (run basics for all captions).
  - Corps in first place: abbreviated cycle (run basics for weakest caption only).
- Return round results.

### Backend endpoints in backend/api/v1/seasons.py:
1. POST /api/v1/seasons/{id}/advance - Run the next round. Calls run_competition_round for the next unplayed round.
2. GET /api/v1/seasons/{id}/tour-status - Returns {current_round: int, total_rounds: int, rounds_completed: int, schedule: list, standings: dict}.
3. POST /api/v1/seasons/{id}/enter-finals - Validate all corps have required_scores, transition season to finals status.

## Visual Design
No frontend changes in this show - frontend is covered by the Tour Status View show.

## Guard Design
- Handle edge case: not enough corps to fill a slot (use fewer corps).
- Handle scoring failures gracefully (log and continue).
- Idempotent advance: calling advance when all rounds are done returns a message, does not error.
- Enter-finals validates that all corps have minimum required_scores.

## General Effect
The tour coordinator is the engine that drives autonomous competition execution. It transforms a configured season into a running tournament.

## Constraints
- Use the existing competition creation and scoring infrastructure (POST /competitions, POST /competitions/{id}/run).
- Do not modify the scoring logic itself.
- Self-improvement cycles use the existing run_basics function from backend/services/improvement.py.
- Store all schedule and standings data in season.yaml (via season_persistence.py).

## Deliverables
- New backend/services/tour_coordinator.py with generate_schedule and run_competition_round
- Modified backend/api/v1/seasons.py with advance, tour-status, enter-finals endpoints
- Modified backend/services/season_persistence.py if needed for schedule/standings persistence

## Evaluation Rubric
- generate_schedule produces valid schedule covering all corps: 25 points
- run_competition_round creates and scores competitions: 25 points
- Self-improvement dispatch works: 15 points
- Endpoints return correct data: 20 points
- Edge cases handled: 10 points
- Tests pass: 5 points