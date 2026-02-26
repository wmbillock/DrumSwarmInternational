## Objective
Build a production-ready asynchronous messaging system with threaded conversations, AI-powered archival with searchable summaries, and real-time notification updates. The system must support role-based operations (agents create threads, users reply and mark complete, admins bulk-archive) and serve as a permanent knowledge record with audit trail.

## Deliverables
- **Database schema**:
  - `message_threads` table: UUID PK, status enum, created_at, archived_at, creator_id FK.
  - `messages` table: UUID PK, thread_id FK, sender_id FK, content TEXT, created_at (immutable).
  - `archived_threads` table: UUID PK, original_thread_id FK, summary TEXT, tags JSONB, full_text_index TSVECTOR, decision_labels JSONB, archived_at.
- **REST API**:
  - GET /api/v1/messaging/threads
  - POST /api/v1/messaging/threads
  - GET /api/v1/messaging/threads/{id}
  - POST /api/v1/messaging/threads/{id}/messages
  - PATCH /api/v1/messaging/threads/{id}
  - GET /api/v1/messaging/unread-count
  - GET /api/v1/messaging/archive/search
  - POST /api/v1/messaging/archive/bulk-archive.
- **Backend service**:
  - `create_thread()`
  - `add_message()`
  - `mark_complete()`
  - `search_archive()` with ranking formula: BM25(0.5) + recency_decay(0.3) + tag_match(0.15) + decision_label(0.05).
  - `bulk_archive()` filtering 30+ day threads.
  - `generate_summary_async()`: background task (non-blocking).
  - `calculate_thread_age()`.
- **React components**:
  - `MessageInbox.tsx`
  - `MessageArchive.tsx`
  - `MessageAdmin.tsx`
  - TopNav badge component.
- **WebSocket integration**:
  - Event types: message:new, thread:created, thread:status_changed, thread:archived, unread_count:updated.
- **Tests and documentation**:
  - Unit tests for service layer functions (thread lifecycle, search ranking algorithm, date threshold calculations).
  - Integration tests for all API endpoints with permission checks.
  - WebSocket event tests (emission, authentication, schema validation).
  - API contract documentation.
  - Permission matrix.
  - Archive search algorithm specification.

## Constraints
- All messages are immutable and permanent (no deletion allowed; archive is permanent, read-only record).
- Thread status transitions: `open` → `ready_for_archive` (14+ days elapsed OR user marks complete) → `archived` (eligible at 30+ days; requires admin bulk-archive).
- Permissions: agents=`create_thread` only; users=`add_message` + `mark_complete`; admins=`bulk_archive` only.
- Archive search ranking formula: **0.5 × BM25(query) + 0.3 × recency_decay(archived_at) + 0.15 × tag_match(tags) + 0.05 × decision_label_match(decision_labels)**; return top 10 results by default.
- Use `v1.ts` client utilities exclusively for all API calls.
- WebSocket events fire synchronously with database state changes.
- LLM summary generation runs as background task without blocking API response (fire-and-forget pattern).
- All database primary keys are UUID v4; cascade delete enforced only on message_threads deletion (not on archived_threads).
- 14-day server-side threshold enforced for "Ready to Archive" UI suggestion; 30-day server-side threshold enforced for bulk-archive eligibility filter.

## Acceptance Criteria
1. ✅ All 3 database tables created with UUID primary keys, correct foreign keys, cascade delete on message_threads only, full-text index on archived_threads.full_text_index.
2. ✅ All 8 API endpoints implemented, tested, returning correct status codes (200, 201, 404, 403); response schemas match documentation.
3. ✅ Permission checks enforced via middleware on all endpoints; agents cannot reply/archive (403), users cannot create/archive (403), admins cannot create/reply (403).
4. ✅ WebSocket events emit for all 5 scenarios (message:new, thread:created, thread:status_changed, thread:archived, unread_count:updated) with correct payloads; unauthenticated connections rejected (401).
5. ✅ Archive search returns results ranked by algorithm formula; top 10 default; tag and decision_label filters functional.
6. ✅ MessageInbox, MessageArchive, MessageAdmin components render correctly; navigation between views functional; 14-day readiness indicator displays on eligible threads.
7. ✅ Unread count badge displays correct count, updates in real-time via WebSocket, pulse animation triggers on new thread creation.
8. ✅ TypeScript compilation zero errors (strict mode); test suite >80% coverage (unit + integration); all tests passing.
9. ✅ 14-day "Ready to Archive" threshold enforced server-side; threads 14+ days old display ready indicator; 30-day bulk-archive eligibility enforced server-side.
10. ✅ LLM summary generation runs asynchronously without blocking API response; summary appears in archive within 30 seconds of archival.
11. ✅ All messages persist forever; archive records immutable; no deletion endpoints; audit trail complete.
12. ✅ Backend starts on port 4224 with `uvicorn backend.api.app:app --host 0.0.0.0 --port 4224 --reload`; frontend builds without errors; WebSocket connections established and authenticated from browser.
```