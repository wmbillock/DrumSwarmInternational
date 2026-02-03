# Acceptance Checklist — Corps Auto-Staffing with Visible Hiring

- [x] POST /api/v1/corps auto-calls initialize_corps
- [x] GET /api/v1/corps/{id}/staffing-status returns total_roles, hired, current_role
- [x] Corps list includes staff_count per corps
- [x] HiringProgress component polls staffing status and shows progress + current role
- [x] CorpsList shows staff count badge
- [x] CorpsCreateModal shows hiring progress after creation instead of closing
