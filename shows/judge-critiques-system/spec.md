# Judge Critiques System

## Goal
After each competition, store judge critique per corps. Provide clarification endpoint. Show in competition detail.

## Acceptance Criteria
1. After competition scoring, judge critique is stored per corps in performances/{corps_id}/critique_round_{N}.md
2. POST /api/v1/corps/{id}/critique/{round}/clarify endpoint for asking clarifying questions
3. Critique visible in CompetitionLive.tsx competition detail view
4. Critique includes per-caption feedback and overall assessment
5. TypeScript compiles, tests pass