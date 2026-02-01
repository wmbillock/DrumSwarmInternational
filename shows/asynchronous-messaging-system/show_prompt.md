# Asynchronous Messaging System — Implementation Prompt

You are implementing a **threaded inbox system** for the DCI Swarm that enables asynchronous collaboration between agents and human users (EDs, PCs, and admins) without cognitive overload.

## Core Requirements

### 1. Thread & Message Persistence

- **Database Schema**:
  - `message_threads` table: `id (UUID)`, `originator_role`, `subject`, `status (pending|completed)`, `created_at`, `updated_at`, `completed_at`, `completed_by`
  - `messages` table: `id (UUID)`, `thread_id (FK)`, `sender_type (user|agent)`, `sender_role`, `sender_name`, `body`, `created_at`
  - Indexes on `thread_id`, `status`, `created_at` for fast queries
  - Cascade delete: archived threads → archived messages

- **Archive Schema**:
  - `archived_threads` table: `id (UUID)`, `original_thread_id`, `originator_role`, `subject`, `summary`, `message_count`, `created_at`, `archived_at`, `archived_by`, `full_text`, `tags` (JSONB), `decision` (nullable)
  - Full-text search index on `full_text` column

### 2. API Endpoints (V1)

#### Active Threads
- `GET /api/v1/messaging/threads` — List with filters (status, originator_role, sort)
- `POST /api/v1/messaging/threads` — Create thread (agent initiates, user receives)
- `GET /api/v1/messaging/threads/{thread_id}` — Thread detail + full message history
- `POST /api/v1/messaging/threads/{thread_id}/messages` — Add message (user or agent)
- `PATCH /api/v1/messaging/threads/{thread_id}` — Mark complete (user only, with role check)
- `GET /api/v1/messaging/unread-count` — Badge count for nav bar

#### Archive
- `GET /api/v1/messaging/archive` — Search archived threads (params: search, originator_role, date_range, sort=relevance|date)
- `POST /api/v1/messaging/archive/bulk-archive` — Admin bulk-archive (takes thread_ids list, triggers LLM summaries)
- `GET /api/v1/messaging/archive/{archived_thread_id}` — Archived thread read-only view

### 3. Services Layer

**New file: `backend/services/message_service.py`**

Core functions:
- `create_thread(corps_id, originator_role, subject, initial_message)` — Create thread + first message
- `add_message(thread_id, sender_type, sender_role, sender_name, body)` — Append message
- `mark_complete(thread_id, completed_by_user_id)` — Set status=completed, record timestamp
- `get_unread_count(user_id)` — Count threads user has not viewed
- `mark_viewed(thread_id)` — Set viewed_at timestamp
- `search_archive(query, corps_id, date_range, limit=20)` — Full-text search with ranking
- `bulk_archive(thread_ids, archived_by_user_id)` — Archive threads + generate LLM summaries async

**Summary Generation (async background task)**:
```python
async def generate_archive_summary(thread_id: str) -> str:
    # Fetch all messages for thread
    # Concatenate in chronological order
    # Call LLM: "Summarize this conversation in 2-3 sentences, including the core decision:"
    # Extract tags from summary (design, schedule, personnel, etc.)
    # Update archived_thread record
```

### 4. WebSocket Events (Real-Time Sync)

Emit from backend when:
- **`message:new`** — New message arrives in thread (update unread badge, thread list)
- **`thread:created`** — Thread created in user's inbox (new thread appears in list, badge increments)
- **`thread:status_changed`** — Thread marked complete (thread moves to "completed" visual state)
- **`thread:archived`** — Thread bulk-archived (removed from active list, added to archive)
- **`unread_count:updated`** — Unread count changed (badge updates in nav bar)

### 5. Frontend Components

**Pages:**
- **`frontend/src/pages/MessageInbox.tsx`**
  - Left sidebar: Active thread list with filters (status, originator_role)
  - Center pane: Thread detail view (conversation, originator info, creation date)
  - "Mark Complete" button (visible only for authorized users)
  - Reply box for user responses
  - Real-time WebSocket sync (threads appear immediately, badges update)

- **`frontend/src/pages/MessageArchive.tsx`**
  - Search interface with query input
  - Filters: originator_role, date_range, tags
  - Results ranked by relevance (BM25 + recency + tags)
  - Click result → read-only archived thread view with summary and metadata

- **`frontend/src/pages/MessageAdmin.tsx`**
  - Bulk-archive interface: multi-select completed threads
  - Confirmation modal showing summary previews
  - Execute bulk-archive button (admin only)
  - Archive operation status / log

**Components:**
- **`TopNav.tsx` update**: Add notification badge showing unread count; click → navigate to inbox
- **`ThreadListItem.tsx`**: Render thread row with sender, subject, timestamp, unread count, status badge
- **`ThreadDetail.tsx`**: Display full conversation, originator info, reply box
- **`ArchiveResultCard.tsx`**: Display archived thread summary with tags, metadata, decision highlight

**Service:**
- **`frontend/src/services/messageService.ts`**
  - Typed V1 API client with methods:
    - `listThreads(filters)`, `createThread()`, `getThread(id)`, `addMessage()`, `markComplete()`
    - `getUnreadCount()`, `searchArchive(query, filters)`, `bulkArchive(thread_ids)`

### 6. Permission Guards

- **Create Thread**: Agents only (ED/PC/Caption Heads/Techs escalate)
- **Mark Complete**: Thread receiver (human user) + original sender with authority
- **Bulk Archive**: Admin role only
- **Search Archive**: Admin + ED (read-only); others forbidden (403)

### 7. Ranking Logic (Archive Search)

BM25 full-text match (0.5 weight) + recency boost within 6 months (0.3) + exact tag match (0.15) + decision prominence (0.05)

```
score = (bm25 × 0.5) + (recency_boost × 0.3) + (tag_match × 0.15) + (decision_exists × 0.05)
```

### 8. Acceptance Criteria

- ✅ Thread creation → immediate notification, inbox appears in sidebar
- ✅ User marks thread complete → status changes, completion timestamp recorded
- ✅ Admin bulk-archives 50 threads → <2 minutes, LLM summaries generated, removed from active list
- ✅ Archive search → <1 second response, results ranked by relevance
- ✅ Role-based guards enforce permissions (unauthorized actions → 403)
- ✅ All messages persist (no deletions); archive as long-term memory
- ✅ Subsequent messages in thread update badge only (no new notification)

## Implementation Order

1. **Database migrations**: Create `message_threads`, `messages`, `archived_threads` tables with indexes
2. **Backend services**: `message_service.py` with CRUD + search + summary generation
3. **API endpoints**: All 8 routes in `backend/api/v1/router.py`
4. **WebSocket events**: Emit from service layer when threads/messages change
5. **Frontend pages**: MessageInbox + MessageArchive + MessageAdmin
6. **TopNav integration**: Add notification badge + link to inbox
7. **Testing**: E2E tests for thread creation → completion → archive flow

## Notes

- Notifications are sent once per thread (not batched); subsequent messages update badge only
- 14-day threshold for "Ready to Archive" UI suggestion; 30-day threshold for bulk-archive eligibility
- LLM summaries may require human review for accuracy
- All messages persist forever; nothing is deleted—archive is the permanent record
