# Tour Status View and TourSchedule Component

## Goal
Frontend tour visualization when season status is on_tour.

## Acceptance Criteria
1. SeasonWorkshop when status=on_tour shows: schedule timeline, division standings, overall rankings, current round, history
2. New TourSchedule.tsx component with visual timeline and division color coding
3. Uses GET /seasons/{id}/schedule and GET /seasons/{id}/standings endpoints
4. Shows which round is current, which are complete, which are upcoming
5. Division standings show corps ranked by accumulated scores
6. TypeScript compiles clean