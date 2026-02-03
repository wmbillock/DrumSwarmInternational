# Acceptance Checklist — Asynchronous Messaging System

- [x] messaging_threads + thread_messages + archived_threads tables with UUIDs, timestamps, and cascade delete
- [x] Messaging API endpoints (threads, messages, unread count, archive, bulk archive)
- [x] Messaging service methods for create/add/complete/search/archive
- [x] LLM summary generation for archives (with fallback)
- [x] Archive search ranking with BM25+recency+tags+decision weighting
- [x] WebSocket events: message:new, thread:created, thread:status_changed, thread:archived, unread_count:updated
- [x] Message Inbox UI with thread list, detail view, reply, mark complete
- [x] Message Archive UI with search and filters
- [x] Message Admin UI with bulk archive (admin only)
- [x] Nav unread badge
