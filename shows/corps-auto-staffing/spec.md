# Corps Auto-Staffing with Visible Hiring

## Show Concept

A real-time corps staffing experience where the hiring process becomes visible to the user. When a new corps is created via API, the system immediately begins recruiting agents across all 16 leadership and performing roles. The frontend displays live progress—current role being filled, total hired count, and a dynamic progress indicator—transforming an invisible backend operation into an observable, engaging creation moment.

## Musical Design

TBD — awaiting design input

## Visual Design

**HiringProgress Component** (new):
- Large circular or linear progress bar showing `hired / 16` roles filled
- Current role name displayed prominently (e.g., "Recruiting Mellophone Instructor...")
- Smooth polling updates every 2 seconds from `/api/v1/corps/{id}/staffing-status`
- Animated progress transitions (fade/slide as each role completes)
- Responsive layout: full-width on mobile, sidebar/modal on desktop

**CorpsCreateModal** (updated):
- After successful POST to `/api/v1/corps`, modal remains open
- Transitions from form → HiringProgress component
- Shows hiring until `hired == 16` or error occurs
- Close button available once hiring completes

**CorpsList** (updated):
- Each corps card includes a staff_count badge (e.g., "12/16 hired")
- Badge styling reflects completion: amber (in-progress), green (complete), gray (pending)

## Guard Design

TBD — awaiting design input

## General Effect

The goal is to eliminate the "dead zone" between form submission and a usable corps. Instead of a spinner or success modal, users witness the real-time hiring process—seeing role names appear as agents are recruited. This creates transparency, builds confidence in the system's activity, and enables quick iteration if hiring fails.

## Constraints

1. **Auto-initialization on POST**: `/api/v1/corps` must call `initialize_corps()` immediately after creating the corps record in the database.
2. **Staffing-status endpoint**: GET `/api/v1/corps/{id}/staffing-status` returns JSON `{total_roles: 16, hired: N, current_role: "..."}` within 500ms.
3. **Frontend polling**: HiringProgress component polls every 2 seconds; must not block UI or cause excessive requests.
4. **Existing tests**: All 1231 backend tests + 11 frontend tests must pass without modification.
5. **TypeScript compilation**: `cd frontend && npx tsc --noEmit` must complete clean.
6. **No breaking API changes**: Corps list endpoint gains `staff_count` field; must be backward-compatible.

## Deliverables

### Backend
- [ ] Update `POST /api/v1/corps` to call `initialize_corps()` before returning response
- [ ] Create GET `/api/v1/corps/{id}/staffing-status` endpoint returning `{total_roles: 16, hired: N, current_role: "..."}`
- [ ] Update `GET /api/v1/corps` list endpoint to include `staff_count` field per corps (query or join)
- [ ] Unit tests for staffing-status endpoint (edge cases: corps not found, hiring in-progress, hiring complete, error states)
- [ ] Integration test: POST corps → staffing-status transitions from 0 → 16 hired

### Frontend
- [ ] New `HiringProgress.tsx` component:
  - Progress bar (circular or linear)
  - Current role name display
  - `useEffect` polling hook (every 2s) to fetch `/api/v1/corps/{id}/staffing-status`
  - Error boundary (retry button if fetch fails)
  - Completion detection (`hired === 16`)
- [ ] Update `CorpsCreateModal.tsx`:
  - Form submission triggers corps creation
  - On success, show HiringProgress instead of closing
  - Provide close button once hiring completes or errors
- [ ] Update `CorpsList.tsx`:
  - Render staff_count badge on each corps card (e.g., "12/16 hired")
  - Badge styling by status: amber (active), green (complete), gray (pending)
- [ ] TypeScript types in `src/services/v1.ts`:
  - `StaffingStatusResponse` interface: `{total_roles: number, hired: number, current_role: string}`
  - Update `CorpsResponse` to include `staff_count?: number`
- [ ] Tests:
  - HiringProgress component: renders, polls, handles updates, error recovery
  - CorpsCreateModal: shows progress after creation
  - CorpsList: displays badges correctly

### Documentation
- [ ] Update API docs (Swagger/OpenAPI) with new endpoint schema
- [ ] Design notes: rationale for auto-initialization + real-time visibility

## Acceptance Criteria

1. ✅ POST `/api/v1/corps` returns immediately; staffing begins asynchronously
2. ✅ GET `/api/v1/corps/{id}/staffing-status` returns accurate counts and role name within 500ms
3. ✅ Corps list endpoint returns all existing corps with `staff_count` field populated
4. ✅ HiringProgress component appears after corps creation and polls every ~2 seconds
5. ✅ Progress bar and role name update visibly as staffing advances
6. ✅ CorpsList badges show staff counts accurately
7. ✅ Hiring modal closes and transitions to corps detail on completion or user action
8. ✅ All 1231 backend tests pass
9. ✅ All 11 frontend tests pass
10. ✅ `cd frontend && npx tsc --noEmit` compiles clean, zero errors

---

## Swarm Prompt

### Objective
Implement automatic corps staffing initialization with real-time frontend progress visibility. When a corps is created via POST, trigger background agent recruitment across all 16 roles; expose progress via a dedicated endpoint and polling UI component.

### Deliverables
1. **Backend**: Auto-init corps on POST; staffing-status endpoint; staff_count in corps list
2. **Frontend**: HiringProgress component (polls every 2s), updated CorpsCreateModal, CorpsList badges
3. **Tests**: 1231 backend + 11 frontend tests passing; new tests for staffing flow
4. **Types**: StaffingStatusResponse + CorpsResponse.staff_count in v1.ts

### Constraints
- Auto-init must happen immediately after corps creation in DB
- Staffing-status response time < 500ms
- No breaking API changes (new fields must be additive)
- HiringProgress polling interval: 2 seconds (no less, to avoid server load)
- All existing tests must pass unchanged
- TypeScript must compile clean

### Acceptance Criteria
- POST corps triggers auto-initialization; staffing-status endpoint returns accurate counts
- Frontend component polls every 2s and displays real-time progress with role names
- CorpsList badges reflect staff_count; all UI updates without console errors
- 1231 backend + 11 frontend tests pass; `tsc --noEmit` clean
- User sees hiring progress immediately after form submission (no closing modal)
