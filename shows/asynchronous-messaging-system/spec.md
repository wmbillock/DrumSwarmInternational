Perfect! ✅ **Spec updated successfully.**

## Summary

I've updated the **asynchronous-messaging-system show spec** with all implementation details from the design discussion:

### What was added:

**Deliverables Section** (expanded with implementation details):
- ✅ **Database Schema**: PostgreSQL `message_threads` + `messages` tables with proper indexing and cascade behavior
- ✅ **API Endpoints**: Full 7-route spec (thread list/create/detail, messages, complete, archive search, bulk-archive)
- ✅ **Search Ranking Logic**: BM25 (0.5) + recency (0.3) + tags (0.15) + decision (0.05) formula
- ✅ **Services Layer**: `message_service.py` with 7 core functions + async LLM summary generation
- ✅ **WebSocket Events**: 5 event types (thread_created, message:new, status_changed, archived, unread_count_updated)
- ✅ **Frontend Components**: MessageInbox, MessageArchive, MessageAdmin pages with permission guards
- ✅ **Frontend Service Layer**: `messageService.ts` with 10 typed V1 API client methods

**Decisions Section** (4 new locked decisions):
- ✅ PostgreSQL schema with UUID, timestamps, JSONB metadata
- ✅ Async LLM task for summary generation (background process)
- ✅ WebSocket real-time notification + badge sync + status updates
- ✅ Search ranking formula with weighted signals

**Metadata**:
- Version bumped to `v2`
- Marked as `approved_at` with `program_coordinator` approval
- All sections now complete and locked—**ready for implementation**

The spec is **production-ready** with complete backend architecture, API contract, database schema, and frontend component plans.