# Tour Coordinator Service

## Goal
New backend service that generates competition schedules and runs competition rounds.

## Acceptance Criteria
1. New file backend/services/tour_coordinator.py
2. generate_schedule(): creates random cross-divisional competition slots ensuring all corps get required_scores appearances
3. run_competition_round(): dispatch corps to competition, score them, update standings, trigger self-improvement cycles for non-leaders
4. Backend endpoints: POST /seasons/{id}/advance, GET /seasons/{id}/tour-status, POST /seasons/{id}/enter-finals
5. Division = all corps assigned to same show. Competition = single scored event with N random corps from ANY division
6. After each competition: non-leaders get full improvement cycle, leaders get abbreviated cycle
7. Tests pass