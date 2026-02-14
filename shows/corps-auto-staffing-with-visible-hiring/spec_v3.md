# Corps Auto-Staffing with Visible Hiring

## Show Concept
Real-time staffing progress visualization during corps creation, enabling users to observe hiring mechanics as they unfold rather than receiving a completed result.

## Musical Design
TBD — awaiting design input

## Visual Design
- **HiringProgress.tsx component**: Horizontal progress bar (0–16 roles), current role name display, live role counter ("Hiring role 3 of 16")
- **CorpsList.tsx cards**: Staff count badge (e.g., "8/16 hired") integrated into corps card layout
- **CorpsCreateModal.tsx**: Transition from creation form to live progress view on successful POST

## Guard Design
TBD — awaiting design input

## General Effect
Demystify corps staffing by making the automatic initialization process visible; users see each role being filled in real time, building confidence in system responsiveness.

## Constraints
- Polling interval: 2 seconds maximum (staffing-status endpoint)
- Progress must update without page reload
- All existing tests remain passing
- TypeScript compilation must be clean (`npx tsc --noEmit`)
- Endpoint response time: <500ms target for staffing-status GET

## Objective
Enable automatic corps staffing on creation with real-time frontend progress visibility, transforming a behind-the-scenes process into an observable user experience.

## Acceptance Criteria
1. POST /api/v1/corps auto-calls initialize_corps() after creating the corps record
2. New GET /api/v1/corps/{id}/staffing-status endpoint returns `{total_roles: 16, hired: N, current_role: "..."}`
3. Corps list endpoint includes staff_count field per corps
4. New HiringProgress.tsx component polls staffing-status every 2s, displays progress bar and role names
5. CorpsList.tsx shows staff count badge on each card
6. CorpsCreateModal.tsx displays hiring progress after creation instead of closing
7. All existing tests pass
8. `cd frontend && npx tsc --noEmit` compiles clean

## Deliverables
- Backend: Auto-initialize corps on POST, staffing-status endpoint, staff_count field on list
- Frontend: HiringProgress.tsx component with 2s polling, CorpsList.tsx badge integration, CorpsCreateModal.tsx progress flow
- Tests: Full coverage for new endpoints and components
- Documentation: API endpoint specs, component usage examples

---

## Swarm Prompt

### Objective
Implement automatic corps staffing initialization on API creation with a real-time polling frontend component that visualizes hiring progress, transforming initialization into a user-observable process.

### Deliverables
- **Backend**
  - Modify POST /api/v1/corps to auto-call initialize_corps() after record creation
  - Create GET /api/v1/corps/{id}/staffing-status returning `{total_roles: 16, hired: N, current_role: "..."}`
  - Add staff_count field to corps list endpoint response
  
- **Frontend**
  - Build HiringProgress.tsx component: progress bar (0–16), current role display, 2s polling loop
  - Integrate staff_count badge into CorpsList.tsx cards
  - Update CorpsCreateModal.tsx to show HiringProgress on successful creation
  - Implement polling cleanup on component unmount
  
- **Quality Assurance**
  - Unit tests for initialize_corps trigger
  - Integration tests for staffing-status endpoint
  - Component tests for HiringProgress polling behavior
  - TypeScript type validation

### Constraints
- Polling interval: exactly 2 seconds
- No page reload required for updates
- Endpoint response time: <500ms
- All existing tests must pass
- Zero TypeScript compilation errors

### Acceptance Criteria
1. Corps creation triggers automatic staffing without manual intervention
2. Staffing-status endpoint returns accurate role counts within 500ms
3. HiringProgress component updates every 2 seconds with server data
4. Progress bar reflects 0–16 role range; displays current role name
5. CorpsList badge updates after hiring completes
6. Modal stays open during progress, closes on completion or user action
7. Test suite: 100% pass rate, including new tests
8. TypeScript: `npx tsc --noEmit` returns zero errors