# UI Data Display

## Goal
Improve how data is presented — eliminate raw UUIDs, add consistent badges, and provide helpful empty states.

## Deliverables

### 1. No Raw UUIDs
- Corps IDs: Show display_name everywhere, truncated ID only as secondary info
- Run IDs: Show `run_id.slice(0, 8)` with tooltip for full ID
- Session IDs: Never shown to users unless in admin/debug views
- Season IDs: Show season name, fall back to ID

### 2. Consistent Badge Colors
- Define a badge color mapping in a shared constant:
  - Status: `on_tour` → success (green), `winter_camps` → warning (yellow), `completed` → info (blue), `disbanded` → danger (red), `initializing` → default (gray)
  - Show status: `draft` → default, `needs_review` → warning, `approved` → success, `published` → info
  - Run status: `running` → warning, `completed` → success, `failed` → danger
- All pages use the same mapping — no inline badge color decisions

### 3. Empty States
- Every list/table has a helpful empty state message:
  - Not just "No items found" but contextual: "No corps created yet. Create one to get started."
  - Include a call-to-action button where appropriate (e.g., "Create Corps" button in empty corps list)
- Error states: include retry button

### 4. Timestamps
- All timestamps displayed as relative time ("2 hours ago") with full datetime on hover
- Use a shared `formatTimestamp(iso: string)` utility

## Pages to Update
- All pages that display IDs, badges, timestamps, or lists

## Acceptance Criteria
- Zero raw UUIDs visible in normal user flows
- Badge colors consistent across all pages
- Every empty list has a contextual message
- Timestamps are human-readable
