# Asynchronous Messaging System — Design Brief

## Show Concept
A threaded inbox interface enabling asynchronous collaboration between AI agents and human users, eliminating cognitive overload through organized message threads, automatic archival with searchable summaries, and real-time notification updates. Users experience frictionless async workflows where focused threads reduce inbox sprawl, searchable archives with AI-generated summaries enable rapid knowledge retrieval, and role-based permissions (agents create, users reply/complete, admins archive) ensure structured governance.

## Musical Design
TBD — awaiting design input

## Visual Design
**MessageInbox.tsx** — two-column layout: thread list (left) with status badges, unread indicators, and 14+ day "Ready to Archive" visual cue; thread detail view (right) with chronological messages, reply box, message timestamps, and "Mark Complete" action button.

**MessageArchive.tsx** — search bar with tag filters and decision-label toggles; relevance-ranked results (top 10 by default) with collapsible thread previews showing LLM-generated summaries, decision tags, archive date, and full-text search highlighting.

**MessageAdmin.tsx** — admin-only bulk-archive interface with thread selection checkboxes (filtered to 30+ days old), batch action buttons (Archive Selected, Cancel), and confirmation dialog showing count of eligible threads.

**TopNav** — notification badge displaying unread message count with visual pulse animation on new thread creation; clicking badge navigates to MessageInbox.

## Guard Design
**Permission Model:**
- **Agents** — `create_thread` permission only; can only create new threads, cannot reply or archive
- **Users** — `add_message` and `mark_complete` permissions; can reply to open threads and transition to "ready_for_archive"
- **Admins** — `bulk_archive` permission; can transition 30+ day old threads to archived status

**Data Guards:**
- All messages persist forever; no deletion allowed; archive is immutable permanent record
- Thread status transitions: `open` → `ready_for_archive` (user marks complete OR 14+ days elapsed) → `archived` (eligible at 30+ days; admin bulk-archive)
- WebSocket events authenticated via user context; unauthenticated connections rejected
- Full-text search (BM25 + recency + tags + decision ranking) available on archived threads only
- API endpoints enforce permission checks via middleware; 403 Forbidden returned on violation

## General Effect
Users experience frictionless async collaboration: focused threads reduce email-like inbox sprawl; automatic 14-day readiness suggestion surfaces stale conversations for closure; 30-day bulk-archive eligibility prevents thread accumulation; searchable archive with AI summaries enables rapid knowledge retrieval months later; role-based operations prevent permission creep while maintaining clear audit trail via permanent message record.

## Constraints
- All messages persist forever (archive is permanent, immutable record)
- Use `v1.ts` client utilities for all API calls
- Thread status transitions: `open` → `ready_for_archive` (14+ days) → `archived` (30+ days eligible)
- 14-day threshold for displaying "Ready to Archive" suggestion in UI
- 30-day threshold for bulk-archive eligibility filter in admin panel
- Archive search ranking formula: BM25(0.5) + recency_decay(0.3) + tag_match(0.15) + decision_label(0.05)
- WebSocket events fire synchronously with database state changes
- Unread count badge updates in real-time via WebSocket `unread_count:updated` event
- LLM summary generation happens asynchronously without blocking API response (background task)
- All database primary keys are UUID v4; cascade delete enforced on thread deletion

## Deliverables

### Database
- `message_threads` table (id UUID PK, created_at, status [open/ready_for_archive/archived], archived_at, creator_id FK)
- `messages` table (id UUID PK, thread_id FK, sender_id FK, content TEXT, created_at, constraint: no deletion)
- `archived_threads` table (id UUID PK, original_thread_id FK, summary TEXT, tags JSONB, full_text_index TSVECTOR, decision_labels JSONB, archived_at)
- Cascade delete: message_threads deletion cascades to messages; no cascade for archived_threads (permanent record)
- Full-text search index on archived_threads.full_text_index using PostgreSQL tsvector

### API Endpoints (v1.ts)
- `GET /api/v1/messaging/threads` — list open threads with unread count (200 OK, pagination)
- `POST /api/v1/messaging/threads` — create thread (agents only, 201 Created, 403 if user lacks permission)
- `GET /api/v1/messaging/threads/{id}` — fetch thread with all messages (200 OK, 404 if not found)
- `POST /api/v1/messaging/threads/{id}/messages` — add message (users only, 201 Created, 403 if agent/admin)
- `PATCH /api/v1/messaging/threads/{id}` — mark complete (users only, updates status to ready_for_archive, 200 OK)
- `GET /api/v1/messaging/unread-count` — return integer unread count (200 OK, authenticated only)
- `GET /api/v1/messaging/archive/search` — search archived threads with filters (query, tags, decision_labels), returns top 10 ranked by algorithm (200 OK)
- `POST /api/v1/messaging/archive/bulk-archive` — transition 30+ day threads to archived (admins only, 200 OK with count, 403 if user not admin)

### Backend Service (message_service.py)
- `create_thread(creator_id, title, description) → thread_id` — create new open thread
- `add_message(thread_id, sender_id, content) → message_id` — append message to thread (no reply threading; linear chronological)
- `mark_complete(thread_id) → status` — transition thread to ready_for_archive
- `search_archive(query, tags=[], decision_labels=[]) → List[ArchivedThread]` — full-text search with BM25+recency+tags+decision ranking, return top 10
- `bulk_archive(eligible_only=True) → int` — transition all 30+ day threads to archived, return count affected
- `generate_summary_async(thread_id)` — background task: fetch all messages, call LLM, store summary in archived_threads, run non-blocking
- `calculate_thread_age(created_at) → int` — return days since thread creation

### Frontend Components (React/TypeScript)
- `MessageInbox.tsx` — two-column layout: thread list with unread badges and 14-day "Ready" indicator; detail view with chronological messages, reply input, Mark Complete button
- `MessageArchive.tsx` — search bar, tag filter chips, decision label toggles; paginated results ranked by algorithm with LLM summary preview and decision tags
- `MessageAdmin.tsx` — checkbox list of 30+ day old threads; "Archive Selected" button with confirmation dialog
- TopNav notification badge component — displays unread count, pulse animation on new thread, click navigates to inbox

### Real-time Layer (WebSocket)
- `message:new` — fired when message added to thread; payload: {thread_id, message_id, sender_id, content, created_at}
- `thread:created` — fired on new thread creation; payload: {thread_id, creator_id, title, created_at}
- `thread:status_changed` — fired when thread transitions state; payload: {thread_id, old_status, new_status, changed_at}
- `thread:archived` — fired when thread moved to archived; payload: {thread_id, summary, tags, archived_at}
- `unread_count:updated` — fired on inbox state change; payload: {user_id, unread_count}
- All events authenticated via user context; unauthenticated subscriptions closed with 401

### Tests & Documentation
- TypeScript compilation: zero errors, strict mode enabled
- Unit tests: message_service.py functions (thread lifecycle, search ranking, date thresholds)
- Integration tests: all 8 API endpoints with permission checks (200, 201, 403, 404 scenarios)
- WebSocket tests: event emission, authentication, payload schema validation
- API contract documentation: request/response schemas for each endpoint
- Permission matrix: agents/users/admins × operations (create/reply/complete/archive)
- Archive search algorithm specification: BM25 implementation, recency decay function, tag matching logic

## Swarm Prompt

### Objective
Build a production-ready asynchronous messaging system with threaded conversations, AI-powered archival with searchable summaries, and real-time notification updates. The system must support role-based operations (agents create threads, users reply and mark complete, admins bulk-archive) and serve as a permanent knowledge record with audit trail.

### Deliverables
- **Database schema** (PostgreSQL): `message_threads` (UUID PK, status enum, created_at, archived_at, creator_id FK), `messages` (UUID PK, thread_id FK, sender_id FK, content TEXT, created_at, immutable), `archived_threads` (UUID PK, original_thread_id FK, summary TEXT, tags JSONB, full_text_index TSVECTOR, decision_labels JSONB, archived_at); cascade delete on threads only; full-text search index on archived_threads.full_text_index
- **REST API (v1.ts)**: 8 endpoints (GET/POST /threads, GET /threads/{id}, POST /threads/{id}/messages, PATCH /threads/{id}, GET /unread-count, GET /archive/search, POST /archive/bulk-archive); permission checks via middleware (403 Forbidden on violation); correct status codes (200, 201, 404, 403)
- **Backend service** (message_service.py): `create_thread()`, `add_message()`, `mark_complete()`, `search_archive()` with BM25(0.5)+recency_decay(0.3)+tag_match(0.15)+decision_label(0.05) ranking returning top 10, `bulk_archive()` filtering 30+ day threads, `generate_summary_async()` background task (non-blocking), `calculate_thread_age()`
- **React components**: `MessageInbox.tsx` (two-column list+detail, unread badges, 14-day readiness indicator), `MessageArchive.tsx` (search bar, tag/decision filters, ranked results with LLM summaries), `MessageAdmin.tsx` (30+ day thread selection, bulk-archive confirmation), TopNav badge (unread count display, pulse animation on new thread, click-to-inbox navigation)
- **WebSocket integration**: 5 event types (message:new, thread:created, thread:status_changed, thread:archived, unread_count:updated) emitting synchronously with database commits; user context authentication; unauthenticated connections rejected (401); payload validation
- **Tests**: unit tests for service layer (thread lifecycle, search ranking algorithm, date threshold calculations); integration tests for all 8 endpoints (200/201/404/403 scenarios, permission enforcement); WebSocket event tests (emission, authentication, schema validation); >80% coverage
- **Documentation**: API contract (request/response schemas, HTTP status codes), permission matrix (agents/users/admins × create/reply/complete/archive operations), archive search algorithm specification (BM25 formula, recency decay implementation, tag matching logic), deployment guide

### Constraints
- All messages are immutable and permanent (no deletion allowed; archive is permanent, read-only record)
- Thread status transitions: `open` → `ready_for_archive` (14+ days elapsed OR user marks complete) → `archived` (eligible at 30+ days; requires admin bulk-archive)
- Permissions: agents=`create_thread` only; users=`add_message` + `mark_complete`; admins=`bulk_archive` only; enforce via middleware; return 403 Forbidden on permission violation
- Archive search ranking formula: **0.5 × BM25(query) + 0.3 × recency_decay(archived_at) + 0.15 × tag_match(tags) + 0.05 × decision_label_match(decision_labels)**; return top 10 results by default
- Use `v1.ts` client utilities exclusively for all API calls
- WebSocket events fire synchronously with database state changes; no asynchronous drift between events and persisted state
- LLM summary generation runs as background task without blocking API response (fire-and-forget pattern)
- All database primary keys are UUID v4; cascade delete enforced only on message_threads deletion (not on archived_threads)
- 14-day server-side threshold enforced for "Ready to Archive" UI suggestion; 30-day server-side threshold enforced for bulk-archive eligibility filter

### Acceptance Criteria
1. ✅ All 3 database tables created with UUID primary keys, correct foreign keys, cascade delete on message_threads only, full-text index on archived_threads.full_text_index
2. ✅ All 8 API endpoints implemented, tested, returning correct status codes (200, 201, 404, 403); response schemas match documentation
3. ✅ Permission checks enforced via middleware on all endpoints; agents cannot reply/archive (403), users cannot create/archive (403), admins cannot create/reply (403)
4. ✅ WebSocket events emit for all 5 scenarios (message:new, thread:created, thread:status_changed, thread:archived, unread_count:updated) with correct payloads; unauthenticated connections rejected (401)
5. ✅ Archive search returns results ranked by algorithm formula; top 10 default; tag and decision_label filters functional
6. ✅ MessageInbox, MessageArchive, MessageAdmin components render correctly; navigation between views functional; 14-day readiness indicator displays on eligible threads
7. ✅ Unread count badge displays correct count, updates in real-time via WebSocket, pulse animation triggers on new thread creation
8. ✅ TypeScript compilation zero errors (strict mode); test suite >80% coverage (unit + integration); all tests passing
9. ✅ 14-day "Ready to Archive" threshold enforced server-side; threads 14+ days old display ready indicator; 30-day bulk-archive eligibility enforced server-side
10. ✅ LLM summary generation runs asynchronously without blocking API response; summary appears in archive within 30 seconds of archival
11. ✅ All messages persist forever; archive records immutable; no deletion endpoints; audit trail complete
12. ✅ Backend starts on port 4224 with `uvicorn backend.api.app:app --host 0.0.0.0 --port 4224 --reload`; frontend builds without errors; WebSocket connections established and authenticated from browser