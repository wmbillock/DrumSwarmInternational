# UI Interaction Patterns

## Goal
Standardize interactive patterns (creation flows, tables, tabs) across the frontend.

## Deliverables

### 1. Creation Flows
- Decide: modal vs inline form for each entity type
  - Corps: Modal (already done via CorpsCreateModal)
  - Season: Inline form (already done)
  - Show: Should match one pattern
- All creation flows: loading state, error display, redirect to new entity on success

### 2. DataTable Everywhere
- Replace all hand-rolled `<table>` and `<div>` list layouts with the `<DataTable>` component
- DataTable already supports: columns, onRowClick, emptyMessage, sorting
- Pages still using raw tables: CorpsDetailV2 overview (styled-table), some admin pages

### 3. Tabs URL Sync
- All tabbed pages sync the active tab to the URL (e.g., `/corps/:id/:tab`)
- Already done: CorpsDetailV2
- Needs URL sync: SeasonWorkshop tabs, CompetitionLive tabs, TourDashboard tabs
- Use `useSearchParams` or route params consistently

### 4. Loading & Error States
- Every page: loading spinner → content or error banner
- Consistent `<div className="page-loading">` and `<div className="error-banner">`
- AbortController usage on all fetch calls for cleanup

## Acceptance Criteria
- No raw `<table>` elements outside of DataTable (except truly custom layouts like key-value info)
- All tabbed interfaces sync to URL
- All creation flows show loading, handle errors, redirect on success
