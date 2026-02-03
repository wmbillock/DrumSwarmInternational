## Show Concept
Build the finals system - the culmination of a season where winners are declared per division.

## Musical Design
Backend changes in backend/api/v1/seasons.py:

1. POST /api/v1/seasons/{id}/enter-finals - Transition season to finals status. Validates all corps have met required_scores threshold. Returns qualification status per corps.
2. GET /api/v1/seasons/{id}/finals - Returns finals data: per-division rankings (top N corps per show), qualification status, declared winners.
3. POST /api/v1/seasons/{id}/finals/declare-winner - Body: {show_slug: str, corps_id: str}. Declares the winner for a division. Only works when season is in finals status. Locks that division.

Backend changes in backend/services/season_persistence.py:
- Add finals data to season.yaml: finals_status, qualified_corps (list), division_winners (dict show_slug -> corps_id), finals_locked (bool)
- save_finals_data(), load_finals_data(), declare_winner()

## Visual Design
Frontend changes:

### frontend/src/pages/Finals.tsx (rewrite existing stub)
Route: /finals/{seasonId}
- Header: season name, finals status badge
- Per-division section: show the show name, ranked corps with scores, qualification badge
- For each division: if no winner declared, show "Declare Winner" button next to #1 ranked corps
- Winner display: gold highlight with trophy icon for declared winners
- Overall season champion: the corps with highest aggregate score across divisions

### frontend/src/pages/SeasonWorkshop.tsx
Add a Finals tab that appears when season status is finals or completed. Links to /finals/{seasonId}.

### frontend/src/services/v1.ts
Add: enterFinals, getSeasonFinals, declareWinner API calls.

## Guard Design
- Cannot declare winner if season not in finals status
- Cannot declare winner for division that already has one
- Enter-finals fails if any corps lacks required_scores
- Handle season not found (404)

## General Effect
The finals create a dramatic conclusion to each season with clear winners and celebration.

## Constraints
- Reuse the existing Finals.tsx file (it already has a route at /finals and /finals/:seasonId)
- Use v1.ts for API calls
- Keep backward compatibility with season.yaml format
- Do not modify scoring logic

## Deliverables
- Modified backend/api/v1/seasons.py with 3 finals endpoints
- Modified backend/services/season_persistence.py with finals data management
- Rewritten frontend/src/pages/Finals.tsx
- Modified frontend/src/pages/SeasonWorkshop.tsx with finals tab
- Modified frontend/src/services/v1.ts with new API calls

## Evaluation Rubric
- Enter-finals validation and transition: 20 points
- Finals data endpoint returns correct per-division rankings: 20 points
- Declare winner works with proper validation: 15 points
- Finals.tsx renders per-division rankings: 20 points
- Declare Winner UI button works: 10 points
- Season Workshop finals tab: 5 points
- TypeScript compiles: 10 points