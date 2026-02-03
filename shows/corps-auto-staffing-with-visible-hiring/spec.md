# Corps Auto-Staffing with Visible Hiring

## Goal
When a corps is created via the API, it should automatically begin the staffing process (initialize_corps). The frontend should show real-time hiring progress.

## Acceptance Criteria
1. POST /api/v1/corps now auto-calls initialize_corps() after creating the corps record
2. New GET /api/v1/corps/{id}/staffing-status endpoint returns {total_roles: 16, hired: N, current_role: "..."}
3. Corps list endpoint includes staff_count field per corps
4. New HiringProgress.tsx component polls staffing-status every 2s, shows progress bar and role names
5. CorpsList.tsx shows staff count badge on each card
6. CorpsCreateModal.tsx shows hiring progress after creation instead of closing
7. All existing tests still pass
8. cd frontend && npx tsc --noEmit compiles clean