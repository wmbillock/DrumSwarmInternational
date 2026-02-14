### Objective
Build a frontend progress monitoring interface (TourSchedule component + DivisionStandings display) that allows program coordinators to track corps advancement through active DCI tour seasons, displaying real-time standings during active rounds and historical cumulative standings snapshots after rounds complete.

### Deliverables
- `TourSchedule.tsx` — Visual timeline showing round sequence with current/completed/upcoming states, division color coding, and round metadata (date, location)
- `DivisionStandings.tsx` — Corps ranked by accumulated scores, grouped by division, with score deltas between rounds, division color headers, and live/final standings toggle
- Integration hooks in `SeasonWorkshop.tsx` for conditional on-tour rendering with toggle between live and final views
- TypeScript interfaces: `ScheduleRound`, `StandingsEntry`, `DivisionData`, `RealTimeScoreUpdate`
- Responsive CSS grid layout (desktop → tablet → mobile, minimum 320px width)
- WebSocket polling service for real-time score updates during active rounds
- Jest unit tests for: round status classification, standings sort order, division filtering, score delta calculation, and live/final toggle logic

### Constraints
- **Data source**: `GET /seasons/{id}/schedule` and `GET /seasons/{id}/standings` endpoints only
- **Standings model**: Historical cumulative scores per corps per division (snapshot post-round completion); round deltas calculated from consecutive standings records
- **Real-time updates**: WebSocket polling only active when current round status is detected; cease polling when round closes
- **Activation**: SeasonWorkshop renders TourSchedule + DivisionStandings only when `season.status === "on_tour"`
- **TypeScript**: Must compile with zero errors, no implicit `any`
- **Accessibility**: WCAG AA color contrast minimum for all division color codes
- **Read-only display**: No mutations to tour data; all updates display-only
- **Responsive support**: 320px (mobile), 768px (tablet), 1024px+ (desktop)

### Acceptance Criteria
1. TourSchedule renders a timeline with all rounds from schedule endpoint; current round visually distinct (accent color, icon, or border)
2. Round status correctly calculated: completed (score recorded + past end date), current (today within round date window), upcoming (future start date)
3. DivisionStandings displays corps sorted by cumulative score descending, grouped by division, with color-coded division headers matching API division colors
4. Score delta shown between adjacent rounds (e.g., "+5 pts this round") and during active round (e.g., "+12 (live)")
5. Live/final toggle visible and functional: live view polls real-time updates during active round; final view shows locked standings post-round
6. SeasonWorkshop conditional logic: schedule + standings appear ↔ `status === "on_tour"`; hidden otherwise
7. WebSocket polling: starts when active round detected, updates standings in real-time, stops when round closes
8. Responsive layout passes mobile (320px), tablet (768px), desktop (1024px+) viewports with readable standings and timeline
9. All TypeScript compiles clean; no implicit `any`, all interfaces properly exported
10. Unit tests pass: round status classification, standings sort, division filtering, score delta calculation, live/final toggle