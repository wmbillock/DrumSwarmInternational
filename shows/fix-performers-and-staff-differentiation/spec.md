# Fix Performers and Staff Differentiation

## Show Concept

Ensure that the distinction between staff and performers is clear to the audience. Staff should be visually distinct from performers, reflecting their trusted status. The "Performers" tab in talent should only show performers and not include staff. Role assignments are permanent during a session. Performers are unverified until auditioned or deemed good enough by staff. The system uses a single-versioned API (v1 only) with a data migration to backfill role information on all existing performers. Critical blocker: before backfill, audit must determine where staff currently live in the database.

## Architecture

### Backend Design

**Models:**
- Add `Performer.role` (ENUM: STAFF, PERFORMER) field to talent schema
- Add `Performer.is_verified` boolean field to track verified status
- Track `updated_at` timestamp on role transitions

**Services:**
- Implement services to manage role assignments
- Promote endpoint is idempotent (called twice with same performer ID returns 200 both times)
- `updated_at` frozen after first promotion (second call does not change timestamp)

**APIs (v1 — Single Version):**
- `GET /api/v1/performers`: Existing endpoint, updated with role filtering
  - Returns only performers (role=PERFORMER); excludes staff (role=STAFF)
  - No authorization required
  - Response: array of performers with role=PERFORMER only
  - No breaking changes to existing contract; filtering happens at query time
- `POST /api/v1/talent/{id}/promote`: Staff-only endpoint to promote performer to staff
  - Authorization: Staff-only (returns 403 Unauthorized if caller is not staff)
  - Error response: Always returns `{"error": "Unauthorized"}` for consistency (no existence hints)
  - Response on success: `{"role": "STAFF", "is_verified": true, "updated_at": <timestamp>}` (same response both calls, idempotent)
  - Idempotent: Calling twice with same role returns 200 both times; second call does not modify `updated_at` or `is_verified`

**Data Flow:**
- **BLOCKER — DB Audit Required**: Before migration, determine where staff currently live:
  - Are staff already in the `Performer` table (e.g., with `agent_category='STAFF'`)?
  - Or stored in a separate `Staff` table?
  - Can staff_ids be sourced from config, constants, audit logs, or must they be extracted from data?
  - Result unlocks conditional backfill strategy
- Conditional migration script backfills:
  - If staff exist in `Performer` table: `UPDATE Performer SET role='STAFF' WHERE id IN (staff_ids)`, then remainder `UPDATE Performer SET role='PERFORMER', is_verified=false`
  - If staff in separate table: JOIN on staff_ids to assign role='STAFF', remainder role='PERFORMER'
  - All new performers created after migration default to role=PERFORMER, is_verified=false
- Staff promote performers via `POST /api/v1/talent/{id}/promote` (staff-only, idempotent)
- `/api/v1/performers` filters by role at query time (no caching layer)
- Performers Tab refreshes on mount, not real-time (avoids instant vanishing UX)
- Single API version (v1) with no deprecation period or v2 coexistence

### Backend Implementation
- **Critical audit phase**: Query `Performer` table schema and existing data:
  - `DESCRIBE Performer` / `PRAGMA table_info(Performer)` — does `agent_category` column exist?
  - `SELECT DISTINCT agent_category FROM Performer` — what values exist?
  - Check for separate `Staff` table or role mapping in config
  - Extract staff_ids source (config constant, migration seed, audit logs)
  - Document findings and commit audit report
- Update database schema with `role` (ENUM: STAFF, PERFORMER) and `is_verified` (BOOLEAN) on Performer model
- Implement conditional migration script based on audit findings:
  - If staff in `Performer` table: conditional UPDATE (staff first, then performers)
  - If staff in separate table: JOIN-based backfill
  - Include rollback support (verify all rows assigned role, fail if any NULL role)
  - Include idempotency check (safe to run multiple times)
  - Include verification step (log count of rows updated, verify 100% backfill)
  - **Test:** `test_backfill_staff_vs_performers_split` — verify staff marked STAFF, performers marked PERFORMER, no data corruption
- Update `GET /api/v1/performers` query logic to filter by `role == PERFORMER` and exclude `role == STAFF`
  - Verify staff do NOT appear in response after backfill
  - No endpoint changes; filtering happens at query time
  - Response contract unchanged (same fields, same structure)
- Implement `POST /api/v1/talent/{id}/promote` endpoint (staff-only, idempotent, 403 Unauthorized if unauthorized)
  - Response on success: `{"role": "STAFF", "is_verified": true, "updated_at": <timestamp>}`
  - Error response: `{"error": "Unauthorized"}` (consistent, no existence hints)
- Write API tests for promote endpoint (idempotence, authorization, error responses)
- Write API tests for performers endpoint (filtering, public access, staff exclusion)
- Write integration tests for migration backfill (idempotency, all rows backfilled, staff vs. performers split, rollback on NULL)
- Full codebase audit for v1 `/performers` call sites — verify all internal callers (FE, agents) ready for role filtering

### FE Authorization Question
**Awaiting design input**: How does FE determine if current user is staff (to show promote button)?
- Does `/api/v1/system/whoami` return `current_user.role` (STAFF | PERFORMER)?
- Or does FE client read user role from `/api/v1/performers` response or other endpoint?
- Does FE track staff status in localStorage, auth context, or fetch on demand?

## Interface Design

### Pages and Components

**Talent System:**
- **Staff Badge**: 50x20px, green background with gold text; positioned on user card
- **Performer Badge**: 16x16px red exclamation mark; positioned on user card
- **User Cards**: Include clickable tooltips explaining roles:
  - Staff: "Staff — Trusted individual with demonstrated expertise"
  - Performer: "Performer — Unverified until auditioned or deemed good enough"
- **Performers Tab**: Filtered display showing only performers (fetched via `GET /api/v1/performers`), excludes staff
- **Promote Button**: Staff-only view shows "Promote" button with lock icon on performer cards

### UX Flow

1. Staff members are displayed with a 50x20px green badge and gold text
2. Performers display a 16x16px red exclamation mark badge
3. Hovering over badges shows tooltips explaining role and verification status
4. When staff clicks "Promote" button on a performer card:
   - Inline toast notification appears on the card (not modal, not full-page)
   - Awaiting design input (badge animate on success or silent refresh?)
5. On successful promotion, performer role transitions from PERFORMER to STAFF
6. If non-staff clicks promote (403 Unauthorized), inline toast surfaces error: "You do not have permission to promote"
7. Performers Tab refreshes on open (not real-time), preventing instant vanishing of promoted staff
8. `/api/v1/performers` endpoint is public-readable; promote endpoint requires authorization header

## Quality Plan

### Testing Strategy

**DB Audit Tests (Pre-Migration):**
- Verify staff location: Are staff in `Performer` table or separate table?
- Extract all staff_ids: From config, audit logs, or existing `agent_category='STAFF'` data?
- Verify no data corruption: Staff and performers clearly differentiated before backfill

**API Tests (v1 — Promote Endpoint):**
- `POST /api/v1/talent/{id}/promote` (idempotence):
  - Test: Call `POST /api/v1/talent/{id}/promote` twice with same performer ID
  - Expected: Both calls return 200, `is_verified` unchanged on second call, `updated_at` frozen after first call
  - Test: Unauthorized non-staff caller receives 403 with `{"error": "Unauthorized"}`
  - Verify error response consistency (no existence hints; always "Unauthorized")
- Verify promote endpoint persists role change to database

**API Tests (v1 — Performers Endpoint):**
- `GET /api/v1/performers`: Verify endpoint returns only performers (role=PERFORMER), excludes staff (role=STAFF)
- Verify endpoint is public-readable (no authorization required)
- Verify filtering happens at query time (no caching layer)
- **Critical test:** `test_performers_endpoint_excludes_staff` — after backfill, verify staff do NOT appear in response

**Migration Tests (Data Backfill):**
- `test_backfill_idempotency`: Run migration twice with same data; verify no duplicate inserts or state changes
- `test_backfill_staff_vs_performers_split`: Verify staff marked role='STAFF', performers marked role='PERFORMER', v1 `/performers` returns only performers
- `test_backfill_all_rows`: Verify all existing `Performer` rows backfilled with appropriate role
- `test_backfill_rollback_on_null_role`: Verify rollback if any row has NULL role after backfill
- `test_promote_twice_returns_same_timestamp`: Verify second promote call does not change `updated_at`

**User Interaction Tests:**
- Verify staff badges (50x20px, green/gold) display correctly on staff member cards
- Verify performer badges (16x16px, red exclamation) display correctly on performer cards
- Verify tooltips appear on hover and contain correct role descriptions
- Verify inline toast notification appears on promote success or 403 error (not modal)
- Verify Performers Tab fetches `/api/v1/performers` and excludes staff
- Verify promote button is staff-only (hidden for non-staff)
- Verify lock icon visible on promote button for staff

**Edge Cases:**
- Test when no performers are available in the system (empty Performers Tab)
- Test with multiple staff members (all display correctly with staff badges)
- Test promotion race condition: two concurrent `POST /api/v1/talent/{id}/promote` calls (idempotence should prevent double-processing)
- Test permission enforcement: non-staff user attempts to call `POST /api/v1/talent/{id}/promote` (expect 403)
- Test invalid performer ID (expect 404)
- Test migration with staff mixed in `Performer` table (some role='STAFF', some role='PERFORMER', some NULL)
- Test that promoted staff no longer appear in `/api/v1/performers` endpoint after refresh

### Integration Points

- Ensure migration script correctly identifies staff location and conditionally backfills (no blanket role='PERFORMER')
- Ensure `POST /api/v1/talent/{id}/promote` persists role change to database
- Ensure `GET /api/v1/performers` queries database role filter and returns only role='PERFORMER' subset, excludes role='STAFF'
- Ensure Performers Tab component calls `GET /api/v1/performers` on mount and re-renders
- Ensure badge styling is consistent across all pages using talent data
- Verify v1 `/performers` endpoint works identically to current (filtered subset, no breaking API changes)
- Verify staff do NOT appear in `/api/v1/performers` after backfill and promotion
- Verify no v1/v2 coexistence or deprecation headers needed
- Full codebase audit: all v1 `/performers` call sites ready for role filtering
- FE authorization flow: current user role accessible for promote button visibility

## General Effect

Clear visual and semantic differentiation between staff and performers improves audience trust and transparency. Staff are recognized as verified, trusted individuals with demonstrated expertise. Performers are shown as unverified until auditioned or deemed good enough. A conditional data migration backfills role information across all historical performers, correctly separating staff from performers based on DB audit findings, eliminating API versioning tax and simplifying the system. The promote endpoint prevents accidental race conditions through idempotent state transitions. Performers Tab refreshes on open rather than real-time, avoiding confusing instant vanishing of promoted performers. Critical: backfill must not mark staff as performers, requiring audit-driven conditional logic.

## Constraints

- Performers are unverified until auditioned or deemed good enough
- Performers can join with or without an audition
- The "Performers" tab in talent should only show performers, not staff
- Staff must NOT appear in `/api/v1/performers` response after backfill (verified by tests)
- `/api/v1/performers` is public-readable (no auth required)
- `/api/v1/talent/{id}/promote` is staff-only (403 Unauthorized if not staff)
- `updated_at` is immutable after first promotion (idempotent state)
- Performers Tab refreshes on mount, not real-time (avoids instant vanishing)
- Error responses for `/api/v1/talent/{id}/promote` must not leak staff existence (always "Unauthorized")
- Single v1 API with no versioning overhead; no v2 endpoints needed
- All v1 clients are internal-only (FE + agents); no external webhooks or backward compatibility burden
- Migration script is idempotent and can be run multiple times safely
- Migration includes rollback support (verify all rows backfilled, fail if any NULL role)
- **Critical blocker:** DB audit required before migration to determine staff location and source staff_ids
- Migration backfill must be conditional (not blanket `role='PERFORMER'`) to prevent marking staff as performers

## Deliverables

### Database & Backend

**Phase 1: DB Audit (BLOCKER)**
- Query `Performer` table schema: does `agent_category` column exist?
- Extract existing staff data: staff_ids source (config, audit logs, or data)
- Determine backfill strategy: conditional UPDATE or JOIN-based (depends on audit)
- Commit audit report documenting staff location and backfill approach

**Phase 2: Schema & Migration (Unlock after Phase 1)**
- Add `role` (ENUM: STAFF, PERFORMER) column to `Performer` model
- Add `is_verified` (BOOLEAN) column to `Performer` model
- Update `Performer.updated_at` to track promotion timestamp (frozen after first call)
- Create database migration for schema changes
- Create conditional migration script based on audit findings:
  - If staff in `Performer` table: `UPDATE Performer SET role='STAFF' WHERE id IN (staff_ids)`, then remainder `role='PERFORMER'`
  - If staff in separate table: JOIN-based backfill
  - Include rollback support (fail if any row has NULL role after backfill)
  - Include idempotency check (safe to run multiple times)
  - Include verification step (log count of rows updated, verify 100% backfill)

**Phase 3: API Updates**
- Update `GET /api/v1/performers` query logic to filter by `role == PERFORMER` and exclude `role == STAFF`
  - No endpoint changes; filtering happens at query time
  - Response contract unchanged (same fields, same structure)
- Implement `POST /api/v1/talent/{id}/promote` endpoint (staff-only, idempotent, 403 Unauthorized if unauthorized)
  - Response on success: `{"role": "STAFF", "is_verified": true, "updated_at": <timestamp>}`
  - Error response: `{"error": "Unauthorized"}` (consistent, no existence hints)

**Phase 4: Testing**
- Write API tests for promote endpoint (idempotence, authorization, error responses)
- Write API tests for performers endpoint (filtering, public access, staff exclusion)
- Write integration tests for migration backfill (idempotency, staff vs. performers split, all rows backfilled, rollback on NULL)
- Full codebase audit for v1 `/performers` call sites — verify all internal callers ready for role filtering

### Frontend Components

- **StaffBadge**: 50x20px green badge component with gold text + tooltip
- **PerformerBadge**: 16x16px red exclamation mark component + tooltip
- **PromoteButton**: Staff-only button with lock icon, calls `POST /api/v1/talent/{id}/promote`
- **PerformersTab**: Calls `GET /api/v1/performers`, refreshes on mount
- **UserCard**: Integrates badges, tooltips, and promote button based on user role
- **InlineToast**: Toast notification for promote success/error (not modal)
- Write user interaction tests for badge display, tooltips, and promote flow
- Write integration tests for Performers Tab v1 endpoint consumption
- **Awaiting design input**: How FE determines current user role (is staff) for promote button visibility

### Documentation

- Update API docs with `POST /api/v1/talent/{id}/promote` schema
- Document idempotence guarantee and `updated_at` immutability behavior
- Document permission model and error response format
- Document DB audit findings and conditional migration strategy
- Document migration deployment: migrate DB → code → FE queries same URL, now filtered
- Document rollback procedure if migration fails
- Document acceptance criteria: staff must not appear in `/api/v1/performers` after backfill

## Swarm Prompt

### Objective

Implement role-based differentiation between staff and performers in the talent system using a single-version API (v1 only) with conditional data migration to correctly backfill role information. Staff are trusted individuals with demonstrated expertise; performers are unverified until auditioned or deemed good enough. Critical blocker: DB audit must determine staff location before migration proceeds. Provide filtering on existing v1 talent endpoints, staff-only promotion (v1 only), clear visual badge differentiation, and idempotent role transitions with frozen timestamps.

### Deliverables

**Phase 1: DB Audit (REQUIRED FIRST)**
- Query `Performer` table schema and existing data to determine where staff live
- Extract staff_ids source (config, audit logs, or data extraction)
- Document audit findings and backfill strategy (conditional UPDATE or JOIN-based)
- Write audit report committing to Phase 2 approach

**Phase 2: Database Schema & Conditional Migration (Unlock after Phase 1)**
- Add `role` (ENUM: STAFF | PERFORMER) and `is_verified` (BOOLEAN) columns to `Performer` model
- Create database migration for schema changes
- Implement conditional migration script based on audit:
  - If staff in `Performer` table: `UPDATE Performer SET role='STAFF' WHERE id IN (staff_ids)`, then remainder `role='PERFORMER', is_verified=false`
  - If staff in separate table: JOIN-based backfill
  - Include rollback support (fail if any row has NULL role)
  - Include idempotency check (safe to run multiple times)
  - Include verification step (log row counts)
  - **Test:** `test_backfill_staff_vs_performers_split`, `test_backfill_idempotency`, `test_backfill_rollback_on_null_role`

**Phase 3: API Endpoints**
- Update `GET /api/v1/performers`: Filter logic to return only performers (role=PERFORMER), exclude staff (role=STAFF)
  - No endpoint changes; same contract, updated guts
  - **Test:** `test_performers_endpoint_excludes_staff`
- Implement `POST /api/v1/talent/{id}/promote`: Staff-only endpoint to promote performer to staff (v1 only, no versioning)
  - Authorization: Staff-only; returns 403 with `{"error": "Unauthorized"}` if non-staff (no existence hints)
  - Idempotent: Calling twice returns 200 both times; second call does not change `updated_at` or `is_verified`
  - Response on success: `{"role": "STAFF", "is_verified": true, "updated_at": <timestamp>}`
  - **Tests:** `test_promote_idempotence`, `test_promote_authorization`, `test_promote_twice_returns_same_timestamp`, `test_promote_persistence`

**Phase 4: Frontend Components & Auth**
- Determine FE authorization flow: How does FE know current user is staff? (`/api/v1/system/whoami` or other endpoint?)
- StaffBadge component: 50x20px green background, gold text, tooltip "Staff — Trusted individual with demonstrated expertise"
- PerformerBadge component: 16x16px red exclamation mark, tooltip "Performer — Unverified until auditioned or deemed good enough"
- PromoteButton component: Staff-only, shows lock icon, calls `POST /api/v1/talent/{id}/promote`, surfaces inline toast on success or 403 error (not modal)
- PerformersTab component: Fetches `GET /api/v1/performers` on mount, displays filtered performers only (no staff)
- InlineToast component: Toast notification (not modal) for promote success or error messaging
- **Tests:** Badge display, tooltips, promote button visibility, inline toast notification, Performers Tab v1 endpoint usage

**Phase 5: Testing & Audit**
- Full codebase audit: v1 `/performers` call sites — verify all internal callers (FE, agents) ready for role filtering
- API tests (promote endpoint): Verify idempotence (two promote calls return 200, `updated_at` frozen), authorization (403 if non-staff), error consistency
- API tests (performers endpoint): Verify filtering (only role=PERFORMER, excludes staff), public access (no auth required), staff exclusion post-backfill
- Migration tests: Verify idempotency (can run twice), staff vs. performers split, all rows backfilled, rollback on NULL role, verify counts
- User interaction tests: Verify badge display, tooltips, promote button visibility, inline toast notification, Performers Tab v1 endpoint usage
- Edge case tests: Empty performer list, multiple staff members, concurrent promotions, invalid IDs, unauthorized callers, migration with staff mixed in data

### Constraints

- `/api/v1/performers` is public-readable; no authorization required
- `/api/v1/talent/{id}/promote` is staff-only; non-staff receives 403 with `{"error": "Unauthorized"}` (no existence hints)
- Idempotent: `POST /api/v1/talent/{id}/promote` called twice returns 200 both times; second call does not change `updated_at` or `is_verified`
- Performers Tab refreshes on mount, not real-time (prevents instant vanishing of promoted performers)
- Badge dimensions: Staff 50x20px (green/gold), Performer 16x16px (red exclamation)
- Error responses must not leak staff existence or other sensitive information
- All role data persisted to database; no in-memory state
- Single v1 API only; no v2 versioning, no deprecation headers, no coexistence period
- All v1 clients are internal-only (FE + agents); no external webhooks or backward compatibility burden
- Migration script is idempotent and includes rollback support
- **Critical blocker:** DB audit required before migration to determine staff location and conditionally backfill (no blanket `role='PERFORMER'`)
- Migration backfill must not mark staff as performers; conditional logic based on audit findings
- Staff must NOT appear in `/api/v1/performers` response after backfill (verified by tests)
- Badge animation on promote success: Awaiting design input (animate or silent refresh?)

### Acceptance Criteria

- DB audit completed and documented; audit report commits to backfill strategy
- `GET /api/v1/performers` returns only performers (role=PERFORMER); staff are filtered out and do NOT appear in response
- `POST /api/v1/talent/{id}/promote` requires staff authorization (403 for non-staff)
- Promote endpoint is idempotent: calling twice with same ID returns 200 both times; `updated_at` frozen after first call
- Promote endpoint error body is always `{"error": "Unauthorized"}` (no existence hints)
- Staff badges (50x20px, green/gold) display correctly on staff member cards
- Performer badges (16x16px, red exclamation) display correctly on performer cards
- Tooltips appear on badge hover and contain correct role descriptions
- Promote button is staff-only; hidden for non-staff
- Inline toast notification appears on promote success or 403 error (not modal, on card)
- Performers Tab shows only performers (fetches from `GET /api/v1/performers`); staff do NOT appear
- Migration script correctly identifies staff location (audit-based)
- Migration script conditionally backfills: staff marked role='STAFF', performers marked role='PERFORMER'
- Migration script is idempotent (can be run multiple times safely)
- Migration script includes rollback support (fails if any row has NULL role after backfill)
- Staff do NOT appear in `/api/v1/performers` after backfill and promotion (verified by test: `test_performers_endpoint_excludes_staff`)
- All API tests pass: idempotence, authorization, filtering, error consistency, migration conditional logic, staff vs. performers split
- All user interaction tests pass: badge display, tooltips, promote flow, tab filtering
- Full codebase audit confirms v1 `/performers` call sites ready for role filtering
- Edge cases handled: empty performer list, multiple staff, concurrent promotions, invalid IDs, unauthorized access, migration with staff mixed in data
- Implementation sequence: Phase 1 audit → Phase 2 migration → Phase 3 promote API → Phase 4 FE components → Phase 5 testing