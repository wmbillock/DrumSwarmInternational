## Objective
Implement automatic corps staffing initialization on API creation with a real-time polling frontend component that visualizes hiring progress, transforming initialization into a user-observable process.

## Deliverables
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

## Constraints
- Polling interval: exactly 2 seconds
- No page reload required for updates
- Endpoint response time: <500ms
- All existing tests must pass
- Zero TypeScript compilation errors

## Acceptance Criteria
1. Corps creation triggers automatic staffing without manual intervention
2. Staffing-status endpoint returns accurate role counts within 500ms
3. HiringProgress component updates every 2 seconds with server data
4. Progress bar reflects 0–16 role range; displays current role name
5. CorpsList badge updates after hiring completes
6. Modal stays open during progress, closes on completion or user action
7. Test suite: 100% pass rate, including new tests
8. TypeScript: `npx tsc --noEmit` returns zero errors