## Objective

Implement role-based differentiation between staff and performers in the talent system. Staff are trusted individuals with demonstrated expertise; performers are unverified until auditioned or deemed good enough. Provide public-facing talent filtering, staff-only promotion endpoints, and clear visual badge differentiation.

## Deliverables

- Database schema update: Add `Performer.role` (STAFF | PERFORMER) and `Performer.is_verified` (BOOLEAN) fields with migration
- `GET /talent/performers-only`: Public endpoint that returns only performers, excluding staff (no auth required)
- `POST /talent/{id}/promote`: Staff-only endpoint to promote performer to staff (403 Unauthor
ized if non-staff); idempotent with frozen `updated_at` after first call
- StaffBadge component: 50x20px green background, gold text, tooltip "Staff — Trusted individual with demonstrated expertise"
- PerformerBadge component: 16x16px red exclamation mark, tooltip "Performer — Unverified until auditioned or deemed good enough"
- PromoteButton component: Staff-only, shows lock icon, calls `POST /talent/{id}/promote`, surfaces inline toast on success/error
- PerformersTab component: Fetches `GET /talent/performers-only` on mount, displays filtered performers only
- API tests: Verify idempotence (two promote calls return 200, `updated_at` frozen), authorization (403 if non-staff), error consistency
- User interaction tests: Verify badge display, tooltips, promote button visibility, inline toast notification, Performers Tab filtering
- Edge case tests: Empty performer list, multiple staff members, concurrent promotions, invalid IDs, unauthorized callers

## Constraints

- `/talent/performers-only` is public-readable; no authorization required
- `/talent/{id}/promote` is staff-only; non-staff receives 403 with `{"error": "Unauthorized"}` (no existence hints)
- Idempotent: `POST /talent/{id}/promote` called twice returns 200 both times; second call does not change `updated_at` or `is_verified`
- Performers Tab refreshes on mount, not real-time (prevents instant vanishing of promoted performers)
- Badge dimensions: Staff 50x20px (green/gold), Performer 16x16px (red exclamation)
- Error responses must not leak staff existence or other sensitive information
- All role data persisted to database; no in-memory state

## Acceptance Criteria

- `GET /talent/performers-only` returns only performers; staff are filtered out
- `POST /talent/{id}/promote` requires staff authorization (403 for non-staff)
- Promote endpoint is idempotent: calling twice with same ID returns 200 both times; `updated_at` frozen after first call
- Staff badges (50x20px, green/gold) display correctly on staff member cards
- Performer badges (16x16px, red exclamation) display correctly on performer cards
- Tooltips explain role and verification status when hovered
- Promote button is staff-only; hidden for non-staff
- Inline toast notification appears on promote success or error (not modal)
- Performers Tab shows only performers (fetches from `GET /talent/performers-only`)
- All API tests pass: idempotence, authorization, filtering, error consistency
- All user interaction tests pass: badge display, tooltips, promote flow, tab filtering
- Edge cases handled: empty performer list, multiple staff, concurrent promotions, invalid IDs, unauthorized access