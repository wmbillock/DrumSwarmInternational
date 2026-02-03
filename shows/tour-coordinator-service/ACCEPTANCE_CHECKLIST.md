# Acceptance Checklist

- `backend/services/tour_coordinator.py` provides schedule generation and round advancement.
- `generate_schedule()` builds cross-divisional rounds ensuring required_scores appearances.
- `run_competition_round()` scores a round, updates standings, and triggers improvement cycles.
- Endpoints: POST `/seasons/{id}/advance`, GET `/seasons/{id}/tour-status`, POST `/seasons/{id}/enter-finals`.
- Competitions draw random corps from any division; divisions remain show-based.
- Non-leaders get full basics cycle; leaders get abbreviated cycle.
