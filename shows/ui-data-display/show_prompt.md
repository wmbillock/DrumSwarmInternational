## Show Concept
Improve data presentation across the frontend — no raw UUIDs, consistent badges, helpful empty states, and human-readable timestamps.

## Deliverables
- Shared badge color mapping constant used across all pages
- formatTimestamp utility for relative time with full datetime on hover
- Contextual empty state messages with call-to-action buttons
- Zero raw UUIDs visible in normal user flows

## Constraints
- Use existing shared UI primitives (Badge, DataTable)
- Shared utilities go in frontend/src/utils/formatters.ts
- All pages must use the same color mapping — no inline badge color decisions
