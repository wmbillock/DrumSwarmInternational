# Asynchronous Messaging System

## Goal
Build a threaded inbox system for async collaboration between agents and human users without cognitive overload.

## Acceptance Criteria
1. message_threads and messages tables with UUID, status, timestamps, cascade behavior
2. archived_threads table with full-text search index, LLM-generated summaries, tags
3. GET/POST /api/v1/messaging/threads, GET/POST threads/{id}/messages, PATCH threads/{id}
4. GET /api/v1/messaging/unread-count for nav badge
5. GET /api/v1/messaging/archive with search, POST archive/bulk-archive
6. message_service.py with create_thread, add_message, mark_complete, search_archive, bulk_archive
7. Async LLM summary generation for archived threads
8. WebSocket events: message:new, thread:created, thread:status_changed, thread:archived, unread_count:updated
9. MessageInbox.tsx with thread list, detail view, reply box, mark complete button
10. MessageArchive.tsx with search, filters, relevance-ranked results
11. MessageAdmin.tsx with bulk-archive interface (admin only)
12. TopNav notification badge with unread count
13. Permission guards: agents create threads, users mark complete, admin bulk-archive
14. Archive search ranking: BM25(0.5) + recency(0.3) + tags(0.15) + decision(0.05)
15. TypeScript compiles, tests pass

## Constraints
- All messages persist forever (archive is permanent record)
- Use v1.ts for API calls
- 14-day threshold for Ready to Archive suggestion
- 30-day threshold for bulk-archive eligibility