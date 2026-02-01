# Swarm Prompt: Divisions and Competition Classes

## Show Concept
Add division support to the DCI swarm season and competition system. Corps are assigned to divisions (World Class, Open Class, Div 3) within a season. Standings and scores are grouped by division. This enables tiered competition just like real DCI.

## Musical Design
Backend data model and API changes:

1. **Season metadata** gains `divisions: list[str]` stored in season.yaml metadata dict
2. **Corps-season registration** gains optional `division: str` field (nullable, mutable)
3. **Standings** calculated per-division via query-time grouping

Endpoints to add/modify in `backend/api/v1/router.py`:
- `PUT /seasons/{season_id}` — Accept `divisions` list in metadata
- `POST /seasons/{season_id}/corps` — Accept optional `division` field
- `PUT /seasons/{season_id}/corps/{corps_id}` — NEW: update division assignment
- `GET /seasons/{season_id}/standings` — NEW: division-grouped standings
- `GET /competitions/{competition_id}/scores` — Accept `?division=` query filter

Standings response shape:
```json
{"season_id": "x", "divisions": {"World Class": [{"corps_id": "uuid", "name": "...", "score": 95.5, "rank": 1}], "Open Class": [...], "Unassigned": [...]}}
```

## Visual Design
Frontend changes:

1. **SeasonWorkshop page** — Division config section: editable list of divisions with add/remove. Default: [World Class, Open Class, Div 3]. Division dropdown in corps registration.
2. **Standings component** — Tab bar at top: one tab per division + All tab. Each division tab shows only that division corps ranked. All tab shows everyone with division column.
3. **v1.ts API client** — Add typed methods: updateSeasonDivisions, updateCorpsDivision, getSeasonStandings
4. **types/index.ts** — Add Division types, SeasonStandings interface

## Guard Design
Edge cases and validation:
- Division field on registration must match one of the season configured divisions (or null)
- If a division is removed from season config, corps in that division become Unassigned
- Empty divisions list means no division filtering (flat mode, backward compatible)
- Unassigned corps (division=null) appear in All tab only, not in any division tab

## General Effect
This feature enables the core DCI experience of tiered competition. Users can configure divisions per season, assign corps, and view standings filtered by division. It is backward compatible — seasons without divisions work exactly as before.

## Constraints
- Use existing v1.ts API client patterns (do NOT use legacy api.ts)
- Store divisions in season metadata dict, not a separate DB table
- Division is a simple string field on registration, not a foreign key
- Do NOT create new LLM clients or agent systems
- Do NOT modify app.py lifespan or add new routers

## Deliverables
- Modified backend/api/v1/router.py with division endpoints
- Modified backend/services/season_persistence.py for division storage
- Modified frontend/src/services/v1.ts with division API methods
- Modified frontend/src/types/index.ts with division types
- Modified SeasonWorkshop page with division config UI
- New or modified standings component with division tabs
- All TypeScript compiles (npx tsc --noEmit)
- All backend tests pass (python -m pytest backend/tests/)

## Evaluation Rubric
- PUT /seasons/{id} accepts and persists divisions list: PASS/FAIL
- POST /seasons/{id}/corps accepts optional division field: PASS/FAIL
- PUT /seasons/{id}/corps/{corps_id} updates division: PASS/FAIL
- GET /seasons/{id}/standings returns division-grouped rankings: PASS/FAIL
- GET /competitions/{id}/scores supports ?division= filter: PASS/FAIL
- Frontend division config UI renders and saves: PASS/FAIL
- Frontend standings tabs filter by division: PASS/FAIL
- TypeScript compilation clean: PASS/FAIL
- Backend tests pass: PASS/FAIL