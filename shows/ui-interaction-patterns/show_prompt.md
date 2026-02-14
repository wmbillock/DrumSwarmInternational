## Show Concept
Standardize interactive patterns across the frontend — creation flows, data tables, tab URL sync, and loading/error states.

## Deliverables
- All creation flows use consistent modal or inline form pattern with loading/error/redirect
- All list layouts use the DataTable component (no raw `<table>` elements)
- All tabbed interfaces sync active tab to URL via useSearchParams
- Every page has consistent loading spinner and error banner patterns

## Constraints
- Use existing DataTable component from frontend/src/ui/
- Follow CorpsDetailV2 as the reference pattern for tab URL sync
- Use AbortController for fetch cleanup
