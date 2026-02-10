# Divisions and Competition Classes

## Show Concept

**Divisions and Competition Classes** is a systems feature enabling DCI Swarm to organize corps into competitive tiers within a season. This mirrors real DCI structure: World Class, Open Class, and Division III competitions. The system allows season administrators to define divisions, assign corps at registration time (or later), and view standings filtered by division or across all corps.

## Musical Design

TBD — awaiting design input. (This is a systems/infrastructure feature, not a musical design spec.)

## Visual Design

The frontend integrates division management into three key areas:

1. **SeasonWorkshop page**: Division configuration panel where admins can add/remove/reorder divisions (default: World Class, Open Class, Div 3).
2. **Corps Registration form**: Dropdown to assign division at registration time (optional; defaults to unassigned).
3. **Standings view**: Tab bar with one tab per configured division + "All" tab. Division tabs show only corps in that division; "All" tab shows all corps with a division column.

## Guard Design

TBD — awaiting design input. (This is a systems/infrastructure feature.)

## General Effect

Division support enhances DCI Swarm's competition management by:
- Isolating standings by competitive tier for realistic scoring and rankings
- Allowing corps to be reassigned mid-season without data loss
- Maintaining backward compatibility (empty divisions list = flat mode, no filtering)
- Keeping unassigned corps visible in "All" tab for easy auditing

## Objective

Add division support to the DCI Swarm season and competition system. Corps are assigned to divisions (World Class, Open Class, Div 3) within a season. Standings and scores are grouped by division.

## Constraints

- Store divisions in season metadata dict, not a separate DB table
- Division is a simple string field on registration, not a foreign key
- Empty divisions list means no division filtering (flat mode, backward compatible)
- Unassigned corps (division=null) appear in All tab only
- If a division is removed from season config, corps in that division become Unassigned
- Use v1.ts for all API calls, not legacy api.ts
- Default divisions: World Class, Open Class, Div 3

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

## Deliverables

### Backend

1. **Database Schema**
   - `Season` model: Add `divisions` field (list of strings) in metadata dict, persist to season.yaml
   - `CorpsSeasonRegistration` model: Add optional `division` field (nullable string)

2. **API Endpoints**
   - `PUT /seasons/{season_id}` — Update season metadata (including divisions list)
   - `POST /seasons/{season_id}/corps` — Register corps with optional division (defaults to null)
   - `PUT /seasons/{season_id}/corps/{corps_id}` — Update corps division assignment (NEW)
   - `GET /seasons/{season_id}/standings` — Return standings grouped by division (NEW)
   - `GET /competitions/{competition_id}/scores` — Support `?division=` query filter

3. **Router Implementation** (`backend/api/v1/seasons.py` and `backend/api/v1/competitions.py`)
   - Update season router to handle divisions in metadata
   - Add corps division assignment endpoint
   - Add standings query endpoint with division filtering
   - Update competition scores endpoint to filter by division

4. **Service Layer** (`backend/services/`)
   - Update `season_persistence.py` to persist divisions to season.yaml
   - Add division validation logic (check division exists in season config)
   - Add standings calculation with division grouping

5. **Tests**
   - Unit tests for division CRUD operations
   - Unit tests for standings grouping and filtering
   - Integration tests for API endpoints
   - Ensure all existing tests pass

### Frontend

1. **API Client** (`frontend/src/services/v1.ts`)
   - `updateSeasonDivisions(seasonId, divisions)` — Update season divisions list
   - `updateCorpsDivision(seasonId, corpsId, division)` — Assign/change corps division
   - `getSeasonStandings(seasonId, division?)` — Fetch standings (optionally filtered by division)

2. **SeasonWorkshop page** (`frontend/src/pages/SeasonWorkshop.tsx`)
   - Add division config section with:
     - Display list of configured divisions
     - "Add division" input + button
     - "Remove division" button per division
     - Reorder UI (drag/drop or up/down buttons)

3. **Corps Registration Form** (within SeasonWorkshop or modal)
   - Add division dropdown:
     - Options: All configured divisions + "Unassigned"
     - Default: "Unassigned"
     - Optional (can be changed later via PUT)

4. **Standings Component** (`frontend/src/components/Standings.tsx` or new `DivisionalStandings.tsx`)
   - Tab bar: One tab per division + "All" tab
   - Each division tab shows:
     - Corps in that division only
     - Ranking, score, division column
   - "All" tab shows:
     - All corps
     - Ranking, score, division column
     - Unassigned corps appear with null/empty division
   - Styling: Subtle borders or background to distinguish tabs

5. **TypeScript Compilation**
   - Ensure all new types compile without errors
   - No implicit `any` types

### Documentation

- Update `docs/api/openapi.md` with new endpoints
- Add division concepts to `docs/domain-glossary.md`
- Update `docs/seasons/` with division management workflow

---

## Swarm Prompt

### Objective

Implement division support for DCI Swarm seasons and competitions. Divisions are lists of strings (e.g., "World Class", "Open Class", "Div 3") stored in season metadata. Corps are assigned to divisions at registration time (optional) or later via admin endpoints. Standings are filtered/grouped by division in the UI.

### Deliverables

- [ ] `Season` model gains `divisions` field in metadata dict; persisted to season.yaml
- [ ] `CorpsSeasonRegistration` model gains optional `division` field (nullable string, mutable)
- [ ] `PUT /seasons/{season_id}` accepts `metadata.divisions` in request body
- [ ] `POST /seasons/{season_id}/corps` accepts optional `division` field; defaults to null
- [ ] `PUT /seasons/{season_id}/corps/{corps_id}` endpoint created to update division
- [ ] `GET /seasons/{season_id}/standings` endpoint created to return standings grouped by division
- [ ] `GET /competitions/{competition_id}/scores?division=<div>` query filter implemented
- [ ] `frontend/src/services/v1.ts` gains three new typed methods:
  - `updateSeasonDivisions(seasonId, divisions)`
  - `updateCorpsDivision(seasonId, corpsId, division)`
  - `getSeasonStandings(seasonId, division?)`
- [ ] SeasonWorkshop page gains division config UI (add/remove/reorder)
- [ ] Corps registration form gains division dropdown
- [ ] Standings component gains tab bar (one per division + All)
- [ ] TypeScript compiles clean (`cd frontend && npx tsc --noEmit`)
- [ ] All backend tests pass (`./dci run-through`)

### Constraints

- Store divisions in season metadata dict under key `divisions`, not a separate DB table
- Division field on registration is a simple nullable string, no versioning
- Empty divisions list or null division → flat mode (no filtering)
- Unassigned corps (division=null) appear in "All" tab only, never in division-specific tabs
- If a division is removed from season config, corps assigned to that division become unassigned
- Use `v1.ts` for all frontend API calls; do not use legacy `api.ts`
- Default divisions at season creation: `["World Class", "Open Class", "Div 3"]`
- Division names are case-sensitive strings; validation happens at the router layer

### Acceptance Criteria

1. Season metadata includes `divisions: list[str]` persisted to season.yaml
2. Corps-season registration includes optional `division: str` field
3. All four new/updated endpoints work:
   - `PUT /seasons/{id}` with divisions in metadata
   - `POST /seasons/{id}/corps` with optional division
   - `PUT /seasons/{id}/corps/{corps_id}` to update division
   - `GET /seasons/{id}/standings` returns grouped standings
4. `GET /competitions/{id}/scores?division=<div>` filters results
5. Frontend UI: SeasonWorkshop has division config section; corps registration has division dropdown; standings have division tabs
6. Three new v1.ts methods are typed and exported
7. TypeScript compilation passes
8. Backend test suite passes (0 failures)

---

## API Contract (Full Detail)

### Divisions Management Endpoints

#### **1. GET /seasons/{season_id}**

Returns season detail including divisions list.

**Response:**
```json
{
  "id": "season-2026-1",
  "name": "2026 Season",
  "metadata": {
    "divisions": ["World Class", "Open Class", "Div 3"]
  },
  "corps_registrations": [...]
}
```

---

#### **2. PUT /seasons/{season_id}**

Update season metadata (including divisions list).

**Request:**
```json
{
  "metadata": {
    "divisions": ["World Class", "Open Class", "Div 3", "Div 2"]
  }
}
```

**Response:** Updated season object with new divisions list.

```json
{
  "id": "season-2026-1",
  "name": "2026 Season",
  "metadata": {
    "divisions": ["World Class", "Open Class", "Div 3", "Div 2"]
  }
}
```

---

#### **3. POST /seasons/{season_id}/corps**

Register corps to season with optional division.

**Request:**
```json
{
  "corps_id": "corps-uuid-123",
  "division": null
}
```

or

```json
{
  "corps_id": "corps-uuid-123",
  "division": "World Class"
}
```

**Response:**
```json
{
  "season_id": "season-2026-1",
  "corps_id": "corps-uuid-123",
  "division": null,
  "status": "registered",
  "registered_at": "2026-02-01T10:00:00Z"
}
```

---

#### **4. PUT /seasons/{season_id}/corps/{corps_id}**

Assign or change division for a registered corps (mutable, no versioning).

**Request:**
```json
{
  "division": "World Class"
}
```

or (to unassign):

```json
{
  "division": null
}
```

**Response:**
```json
{
  "season_id": "season-2026-1",
  "corps_id": "corps-uuid-123",
  "division": "World Class",
  "updated_at": "2026-02-01T12:00:00Z"
}
```

**Error Cases:**
- 404: Corps not registered to season
- 400: Division not in season config

---

#### **5. GET /seasons/{season_id}/standings**

Return standings grouped by division. Optional query param `division` filters to a single division.

**Request (All Corps):**
```
GET /seasons/season-2026-1/standings
```

**Request (Single Division):**
```
GET /seasons/season-2026-1/standings?division=World%20Class
```

**Response (All):**
```json
{
  "season_id": "season-2026-1",
  "total_corps": 15,
  "standings": [
    {
      "rank": 1,
      "corps_id": "corps-abc",
      "corps_name": "Phantom Regiment",
      "division": "World Class",
      "score": 97.5,
      "status": "completed"
    },
    {
      "rank": 2,
      "corps_id": "corps-def",
      "corps_name": "Blue Devils",
      "division": "World Class",
      "score": 96.8,
      "status": "completed"
    },
    {
      "rank": 3,
      "corps_id": "corps-ghi",
      "corps_name": "Unassigned Corps",
      "division": null,
      "score": 92.0,
      "status": "completed"
    }
  ]
}
```

**Response (Single Division):**
```json
{
  "season_id": "season-2026-1",
  "division": "World Class",
  "division_corps_count": 8,
  "standings": [
    {
      "rank": 1,
      "corps_id": "corps-abc",
      "corps_name": "Phantom Regiment",
      "division": "World Class",
      "score": 97.5,
      "status": "completed"
    },
    {
      "rank": 2,
      "corps_id": "corps-def",
      "corps_name": "Blue Devils",
      "division": "World Class",
      "score": 96.8,
      "status": "completed"
    }
  ]
}
```

---

#### **6. GET /competitions/{competition_id}/scores**

Return competition scores. Supports `?division=` query filter.

**Request (All):**
```
GET /competitions/season-2026-1-my-show/scores
```

**Request (Single Division):**
```
GET /competitions/season-2026-1-my-show/scores?division=World%20Class
```

**Response (All):**
```json
{
  "competition_id": "season-2026-1-my-show",
  "season_id": "season-2026-1",
  "show_slug": "my-show",
  "total_scores": 15,
  "scores": [
    {
      "corps_id": "corps-abc",
      "corps_name": "Phantom Regiment",
      "division": "World Class",
      "overall_score": 97.5,
      "captions": {
        "brass": 95.2,
        "percussion": 98.0,
        "guard": 97.1
      }
    },
    {
      "corps_id": "corps-ghi",
      "corps_name": "Unassigned Corps",
      "division": null,
      "overall_score": 92.0,
      "captions": {
        "brass": 90.5,
        "percussion": 92.3,
        "guard": 91.2
      }
    }
  ]
}
```

**Response (Single Division):**
```json
{
  "competition_id": "season-2026-1-my-show",
  "season_id": "season-2026-1",
  "show_slug": "my-show",
  "division": "World Class",
  "division_scores_count": 8,
  "scores": [
    {
      "corps_id": "corps-abc",
      "corps_name": "Phantom Regiment",
      "division": "World Class",
      "overall_score": 97.5,
      "captions": {
        "brass": 95.2,
        "percussion": 98.0,
        "guard": 97.1
      }
    }
  ]
}
```

---

## Implementation Notes

### Backend

1. **Season Metadata Persistence**
   - Divisions list stored in `Season.metadata` dict with key `divisions`
   - Persist to `seasons/<season_id>/season.yaml` under `metadata.divisions`
   - Default: `["World Class", "Open Class", "Div 3"]` at season creation

2. **Corps Division Assignment**
   - `CorpsSeasonRegistration.division` is a nullable string field
   - No foreign key to a divisions table
   - Mutable: can be updated via PUT without creating audit trail
   - Validation: if division is provided, must exist in season config (or raise 400)

3. **Standings Grouping**
   - Calculate standings from existing competition scores
   - Filter by division in router layer (not DB)
   - Sort by composite score within each division
   - Return metadata: total corps, division name, division corps count

4. **Backward Compatibility**
   - If divisions list is empty, treat as flat mode (no filtering)
   - If corps division is null, include in "All" results only

### Frontend

1. **Type Safety**
   - Add `Division` type: `string` (no enum, allow custom divisions)
   - Add to `Season` interface: `divisions?: string[]`
   - Add to `CorpsSeasonRegistration` interface: `division?: string | null`

2. **UI State**
   - SeasonWorkshop: Use controlled component for division input
   - Standings: Use React tabs component; render one tab per division + All
   - Corps form: Use select dropdown with options from season divisions

3. **API Calls**
   - All three v1.ts methods use `try-catch` with user-friendly error messages
   - Handle 404 (corps not registered) and 400 (invalid division) errors
