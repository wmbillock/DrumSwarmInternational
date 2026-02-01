---
show_slug: asynchronous-messaging-system
version: 1
created_at: '2026-02-01T06:40:41.636949+00:00'
approved_at: '2026-02-01T07:09:10.029339+00:00'
approved_by: user
roles_consulted: []
---

# Asynchronous messaging system

## Show Concept

A threaded inbox system enabling Executive Directors, Program Coordinators, and other creative staff to manage asynchronous collaboration without cognitive overload. Agents (Caption Heads, Techs, Music Writers) escalate questions and design decisions through a clear hierarchy; users triage, respond, and manually mark threads complete. Completed threads are bulk-archived by admins as summarized records for long-term institutional memory.

**Core Metaphor**: Each message is a *section on the field*. Threads are *drill formations* that users direct to completion. Archive is the *permanent record*—corps history.

**Core Behaviors**:
- Users receive messages in a threaded inbox (threaded by originator + subject)
- Users explicitly mark threads complete when resolved
- Admins bulk-archive completed threads as summarized records
- Archive is searchable, preserving decisions and context for future reference

---

## General Effect

**Persistence**: All messages (active and archived) persist indefinitely; nothing is deleted.

**Read-Completion Decoupling**: Messages are read separately from completion. A user can read a message, act on it, but only mark the entire thread complete once fully resolved.

**Archive as Long-Term Memory**: Archived summaries serve as institutional knowledge—future corps can reference past decisions, design patterns, and leadership choices without re-reading raw messages.

---

## Visual Design

**Layout**: Sidebar + Thread Detail + Archive Search UX.

**Left Sidebar** (Threaded Inbox):
- List of active threads grouped by originator and subject
- Each thread shows: sender name, subject line, timestamp of most recent message, unread count
- Status indicator: "pending" (waiting for user action) or "completed" (marked done, awaiting archive)
- Quick filter: "Assigned to Me", "Awaiting My Response", "In Progress", "Ready to Archive"

**Center/Right Pane** (Thread Detail):
- Full conversation thread (all messages chronologically)
- Originator role, subject, creation date at top
- "Mark Complete" button (visible only if user has authority; changes thread status to "completed")
- Reply box for user to respond or add context

**Archive Search Pane** (Secondary Tab):
- Full-text search over archived summaries
- Filters by originator, date range, tags/keywords
- Results ranked by relevance + recency
- Each result links to archived summary (read-only view)

---

## Musical Design

**Notification Cadence**: Immediate notification on message arrival (not batched). Users are notified once per new message thread; additional messages in an existing thread do not trigger new notifications (only visual badge update in sidebar).

**Thread Lifecycle Timing**:
- **Auto-Archive Suggestion**: After 14 days of thread inactivity (no new messages), system suggests the thread for archival with a soft nudge in the UI.
- **Auto-Archive Enforcement**: After 30 days of inactivity, completed threads are eligible for bulk-archive; uncompleted threads remain active indefinitely (user must explicitly mark complete).
- **Bulk-Archive Window**: Admins review and execute bulk-archive operations weekly (or as-needed), archiving 20–50 threads per operation.

---

## Guard Design

**Permission Hierarchy**:
```
Agents escalate question → ED/PC creates thread → User triages/responds → User marks complete → Admin bulk-archives
```

**Mark Thread Complete**:
- ✅ **User (human admin)** who received the message — primary authority
- ✅ **Original sender (agent/ED)** can suggest completion but cannot force it
- ❌ Other agents cannot mark threads complete

**Bulk Archive**:
- ✅ **Admin role only** (human users with system-wide permissions)
- ❌ Agents cannot archive — prevents accidental data loss or premature cleanup

**Search Archived Records**:
- ✅ **Admin users** — full access to all archived summaries
- ✅ **Executive Directors** — read-only access (can reference past decisions for context)
- ❌ Other agents cannot search archive — reduces cognitive load and prevents distraction

**Thread Initiation**:
- ✅ **Executive Directors** — can escalate questions to user
- ✅ **Program Coordinators** — can escalate design decisions requiring user input
- ⚠️ **Caption Heads and Techs** must route requests through their ED or PC (maintains hierarchy)

---

## Deliverables

### Thread Schema

```yaml
Thread:
  id: string (UUID)
  originator_role: enum (executive_director | program_coordinator | caption_head | tech | music_writer)
  subject: string
  status: enum (pending | completed)
  created_at: timestamp
  updated_at: timestamp
  completed_at: timestamp (nullable)
  completed_by: string (user ID, nullable)
  messages: Message[] (ordered by created_at)
  archive_candidate_at: timestamp (nullable, 14-day mark for UI suggestion)

Message:
  id: string (UUID)
  thread_id: string (FK)
  sender_type: enum (user | agent)
  sender_role: string (enum of roles)
  sender_name: string
  body: string
  created_at: timestamp
```

### Archive Schema

```yaml
ArchivedThread:
  id: string (UUID)
  original_thread_id: string (reference to Thread)
  originator_role: string
  subject: string
  summary: string (LLM-synthesized 2–3 sentence summary of decision/context)
  message_count: integer
  created_at: timestamp (original thread creation)
  archived_at: timestamp
  archived_by: string (user ID)
  full_text: string (concatenated message bodies for search indexing)
  tags: string[] (auto-extracted keywords: "design", "schedule", "personnel", etc.)
  decision: string (nullable, LLM-extracted core decision if present)
```

### API Endpoints

#### Thread Management

- **GET /api/v1/messaging/threads** — List active threads (query params: status, originator_role, filter, sort)
- **POST /api/v1/messaging/threads** — Create new thread (agent only; creates with initial message)
- **GET /api/v1/messaging/threads/{thread_id}** — Get thread detail + full message history
- **POST /api/v1/messaging/threads/{thread_id}/messages** — Add message to thread (user or agent)
- **PATCH /api/v1/messaging/threads/{thread_id}** — Mark thread complete (user only; requires role check)

#### Archive

- **GET /api/v1/messaging/archive** — List archived threads (query params: search, originator_role, date_range, sort=relevance|date)
- **POST /api/v1/messaging/archive/bulk-archive** — Bulk-archive completed threads (admin only; takes list of thread_ids)
  - Response includes: archive operation ID, count archived, summaries of archived threads
  - Side effect: Triggers async LLM task to generate summaries for each archived thread
- **GET /api/v1/messaging/archive/{archived_thread_id}** — Get archived thread summary + metadata (read-only view)

### Search Ranking Logic (Archive)

Relevance scoring combines:
1. **Text match** (BM25 on full_text): keyword matches in messages and summary
2. **Recency weight**: Recent archives (within 6 months) ranked higher
3. **Tag match**: Exact tag matches boost relevance
4. **Decision prominence**: Archives with extracted decisions (decision field populated) ranked higher

Final rank: `(BM25_score × 0.5) + (recency_boost × 0.3) + (tag_match × 0.15) + (decision_boost × 0.05)`

---

## Evaluation Rubric

### Acceptance Criteria (End-to-End)

1. **Thread Creation & Messaging**
   - ✅ Agent escalates question → thread created in inbox, user notified immediately
   - ✅ User replies to thread → message appended, originator notified
   - ✅ Multi-turn conversation completes without data loss

2. **Manual Completion**
   - ✅ User marks thread complete → status changes to "completed", completion timestamp recorded
   - ✅ Only authorized users (receiver or sender with authority) can mark complete
   - ✅ Completed threads remain visible but visually distinguished in sidebar

3. **Bulk Archive**
   - ✅ Admin selects 50 completed threads → bulk-archive executes in <2 minutes
   - ✅ Each thread generates LLM summary (2–3 sentences) including core decision
   - ✅ Archived threads removed from active inbox, visible in archive pane
   - ✅ Archive operation logged with timestamp and user who executed it

4. **Archive Search**
   - ✅ Search for archived threads by keyword → returns results in <1 second
   - ✅ Results ranked by relevance (BM25 + recency + tags)
   - ✅ ED can search archived threads; agents cannot
   - ✅ Full-text indexing includes messages and summaries

5. **User Behavior**
   - ✅ Users complete 80% of assigned threads (threads marked complete within 30 days of creation)
   - ✅ Average thread resolution time: <7 days from creation to completion
   - ✅ Users initiate searches in archive at least once per season (baseline engagement)

6. **System Reliability**
   - ✅ No message loss: all messages persist regardless of thread status
   - ✅ Archive integrity: archived summaries are immutable, reference original thread ID
   - ✅ Role permission enforcement: role-based guards prevent unauthorized actions (test with multiple roles)

### Test Matrix

| Behavior | Test Case | Expected Result |
|----------|-----------|-----------------|
| Message arrival | Agent creates thread | User notified immediately, thread appears in sidebar |
| Notification de-duplication | Multiple messages in one thread | Only first message triggers notification; subsequent messages update badge |
| Thread marking | User clicks "Mark Complete" | Thread status → "completed", timestamp recorded, thread visually dimmed |
| Unauthorized completion | Non-receiver tries to mark complete | Action rejected (403 Forbidden) |
| Bulk archive | Admin selects 50 threads → executes | All 50 archived, summaries generated, removed from active list, <2 min total time |
| Archive search | Search "design decision" | Results ranked by relevance, <1 sec response, no errors |
| Role-based archive access | ED vs. Tech searches archive | ED sees all results; Tech gets 403 Forbidden |
| 14-day suggestion | Thread inactive 14 days | UI shows "Ready to Archive" badge |
| 30-day enforcement | Thread completed, 30 days old | Eligible for bulk-archive; uncompleted thread remains active |
| Permission hierarchy | Tech tries to create thread | Thread creation rejected; routed through ED/PC instead |

---

## Decisions

✅ **Locked**: Threaded inbox with manual completion, bulk admin archive as summarized records
✅ **Locked**: Persistent, read-completion decoupled, archive as long-term memory
✅ **Locked**: Sidebar + thread detail + archive search UX
✅ **Locked**: Immediate notifications, 14-day suggestions, 30-day auto-archive eligibility
✅ **Locked**: Role-based permissions with hierarchy enforcement
✅ **Locked**: Bulk-archive <2 min for 50 threads, search <1 sec, 80% user completion target

---

## Open Questions

*None at present. All design sections locked.*

---

## Constraints

- **No message deletion**: All messages persist; only archival (summarization) is available
- **Read ≠ Completion**: Users must explicitly mark threads complete; reading a message does not auto-complete
- **Admin-only archival**: Agents cannot archive to prevent accidental data loss
- **LLM-generated summaries**: Archive summaries are synthesized by LLM; may require human review for accuracy
- **Notification once per thread**: Subsequent messages in an active thread do not trigger new notifications
- **Hierarchy enforcement**: Agents cannot escalate directly; must route through ED/PC
