# Acceptance Checklist

- Finals page supports `/finals/{seasonId}` with per-division rankings and artifact review.
- Finals endpoints exist: POST `/seasons/{id}/enter-finals`, GET `/seasons/{id}/finals`, POST `/seasons/{id}/finals/declare-winner`.
- Season Workshop shows a Finals tab when the season status allows it.
- Qualification status is displayed using required score thresholds.
- Winner declaration locks the season.
