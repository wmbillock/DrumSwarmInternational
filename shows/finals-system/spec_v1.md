# Finals System

## Goal
Finals page redesign and backend support for declaring winners.

## Acceptance Criteria
1. Finals.tsx redesign at /finals/{seasonId}: per-division rankings, artifact review, Declare Winner button
2. Backend: POST /seasons/{id}/enter-finals, GET /seasons/{id}/finals, POST /seasons/{id}/finals/declare-winner
3. Season workshop gets a Finals tab when season status allows it
4. Finals show qualification status (which corps met required_scores threshold)
5. Winner declaration locks the season
6. TypeScript compiles, tests pass