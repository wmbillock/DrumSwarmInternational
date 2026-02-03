## Show Concept
When a user creates a corps, the system should automatically begin staffing (spawning the 16-role agent hierarchy). The frontend should show real-time hiring progress rather than closing the modal immediately. The corps list should display staff counts.

## Musical Design
The backend corps creation flow needs three changes:
1. In backend/api/v1/corps.py, the v1_create_corps endpoint must call initialize_corps(db, corps_id) after creating the Corps record, running it in a background thread so the HTTP response returns immediately.
2. Add a new GET /api/v1/corps/{id}/staffing-status endpoint that queries AgentSession count for the corps and returns {total_roles: 16, hired: N, current_role: string, complete: bool}.
3. The corps list endpoint must include a staff_count field by counting AgentSessions per corps.

Key implementation detail: initialize_corps is synchronous and spawns 16 agent sessions (see CORPS_HIERARCHY in corps_service.py). Run it in a background thread using asyncio or threading so the create endpoint returns fast. The staffing-status endpoint just counts sessions.

## Visual Design
Frontend changes in 3 files:
1. New frontend/src/components/HiringProgress.tsx - a component that accepts corpsId, polls GET /corps/{id}/staffing-status every 2 seconds, shows a progress bar (hired/16) and the name of the current role being hired. Uses Field Commander Brutalism styling.
2. frontend/src/pages/CorpsList.tsx - add staff_count display on each corps card (e.g. "16/16 staff" badge).
3. frontend/src/components/CorpsCreateModal.tsx - after successful creation, instead of calling onCreated() immediately, show the HiringProgress component. Only call onCreated() when staffing is complete (hired === 16).

Add the staffing-status API call to frontend/src/services/v1.ts.

## Guard Design
Error handling: if initialize_corps fails, the corps should still exist but show 0/16 staff. The staffing-status endpoint should handle missing corps gracefully (404). The HiringProgress component should show an error state if polling fails 3 times consecutively.

## General Effect
This creates a satisfying onboarding experience - users see their corps being built in real-time rather than a blank slate. The progress visualization makes the system feel alive.

## Constraints
- Do not change the CORPS_HIERARCHY or initialize_corps logic itself - only wire it into the create flow.
- Use threading.Thread for background execution, not asyncio (since initialize_corps is sync).
- The staffing-status endpoint must work even during active hiring (partial results).
- Do not break any existing tests.
- Use v1.ts for all API calls, not api.ts.

## Deliverables
- Modified backend/api/v1/corps.py with auto-staffing and staffing-status endpoint
- Modified backend/api/v1/schemas.py if new request models needed
- New frontend/src/components/HiringProgress.tsx
- Modified frontend/src/pages/CorpsList.tsx with staff count
- Modified frontend/src/components/CorpsCreateModal.tsx with hiring progress flow
- Modified frontend/src/services/v1.ts with new API call

## Evaluation Rubric
- POST /api/v1/corps returns immediately (< 1s) and staffing begins in background: 25 points
- GET /api/v1/corps/{id}/staffing-status returns correct counts: 25 points
- HiringProgress.tsx polls and renders progress: 20 points
- CorpsCreateModal shows progress after creation: 15 points
- CorpsList shows staff count: 10 points
- TypeScript compiles clean: 5 points