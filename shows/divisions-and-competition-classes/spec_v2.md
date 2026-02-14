# Divisions and Competition Classes

## Goal
Add division support to the DCI swarm season and competition system. Corps are assigned to divisions (World Class, Open Class, Div 3) within a season. Standings and scores are grouped by division.

## Acceptance Criteria
1. Season metadata gains `divisions: list[str]` stored in season.yaml metadata dict
2. Corps-season registration gains optional `division: str` field (nullable, mutable)
3. PUT /seasons/{season_id} accepts `divisions` list in metadata
4. POST /seasons/{season_id}/corps accepts optional `division` field
5. PUT /seasons/{season_id}/corps/{corps_id} updates division assignment (NEW endpoint)
6. GET /seasons/{season_id}/standings returns division-grouped rankings (NEW endpoint)
7. GET /competitions/{competition_id}/scores supports `?division=` query filter
8. SeasonWorkshop page gets division config section with add/remove and dropdown in corps registration
9. Standings component gets tab bar: one tab per division + All tab
10. v1.ts gets typed methods: updateSeasonDivisions, updateCorpsDivision, getSeasonStandings
11. TypeScript compiles clean
12. Backend tests pass

## Constraints
- Store divisions in season metadata dict, not a separate DB table
- Division is a simple string field on registration, not a foreign key
- Empty divisions list means no division filtering (flat mode, backward compatible)
- Unassigned corps (division=null) appear in All tab only
- If a division is removed from season config, corps in that division become Unassigned
- Use v1.ts for all API calls, not legacy api.ts