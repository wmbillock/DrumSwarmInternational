# Tour Status View and TourSchedule Component – Brief

## Show Concept
A real-time progress monitoring interface for active DCI tour seasons, enabling program coordinators and staff to track corps advancement through competitive rounds and score accumulation. The TourSchedule component visualizes the competition timeline with division color coding, while the Standings display provides both real-time score updates during active rounds and historical cumulative standings snapshots after competition closes. Users monitor corps progress dynamically without manual refresh cycles.

## Musical Design
Not applicable — this is a data visualization and monitoring tool, not a musical composition. The interface should follow temporal/rhythmic UI principles: clear beat structure in round sequencing, visual "cadence" as divisions progress through the tour calendar.

## Visual Design
- **TourSchedule Timeline Component**: Horizontal or vertical timeline visualization showing:
  - Round sequence (numbered, chronological)
  - Current round highlighted with accent color/icon
  - Completed rounds shown with checkmark/filled state
  - Upcoming rounds shown in muted/preview state
  - Division color coding applied consistently across all rounds
  
- **Division Standings Display**:
  - Corps ranked by accumulated scores with real-time updates during active rounds
  - Per-division score tracking (cumulative + round-specific deltas)
  - Each division presented in its brand color with accessible contrast
  - Live score refresh via WebSocket polling during current round
  - Score delta indicators showing movement between rounds and within current round
  - Toggle between "real-time live view" (if round is active) and "final standings" (if round complete)

- **Layout**: Responsive grid combining timeline (primary) + standings (secondary), adaptable for tablet/desktop viewing by program staff in logistics/admin roles

## Guard Design
Not applicable — this is an administrative frontend tool, not a performance design element.

## General Effect
The user (program coordinator, director, admin staff) should experience:
1. **Situational awareness**: Instant clarity on tour progress (which round is current, complete, upcoming)
2. **Live progress monitoring**: Real-time per-division score updates when rounds are active, with visible refresh indicators
3. **Trustworthy rankings**: Corps standings grouped by division, showing cumulative scores and round-by-round deltas
4. **Flexible viewing**: Seamless toggle between live-view (active round) and historical snapshots (completed rounds)

The component should feel responsive and dynamic—updates arrive without forcing manual refresh, building confidence in the system's real-time data delivery.

## Constraints
- Uses existing API endpoints: `GET /seasons/{id}/schedule` and `GET /seasons/{id}/standings`
- Displays standings as **historical cumulative snapshots after each completed round**, with cumulative score totals and round-specific deltas
- Real-time score updates only displayed during active rounds (live polling)
- Only active when season `status = "on_tour"`
- Must be embedded in SeasonWorkshop component
- TypeScript—zero compilation errors
- Responsive design (minimum 320px width support)
- Division color coding must be accessible (WCAG AA contrast minimum)

## Deliverables
1. **TourSchedule.tsx** — Timeline component with round status indicators (current/completed/upcoming), division color legend, and round metadata display
2. **DivisionStandings.tsx** — Ranked corps display grouped by division, showing cumulative scores, round-by-round deltas, and real-time/final toggle
3. **Integration into SeasonWorkshop.tsx** — Conditional render when `status === "on_tour"`, including:
   - Schedule timeline
   - Division standings grouped by color-coded division
   - Score delta indicators between rounds
   - Live/final standings toggle
4. **TypeScript types** — Interfaces for ScheduleRound, StandingsEntry, DivisionData, and real-time score update structures
5. **Responsive layout** — Desktop-first, tablet/mobile fallback using CSS grid
6. **Real-time data layer** — WebSocket polling logic for active round score updates
7. **Unit tests** — Coverage for round status logic, standings sort order, division filtering, and score delta calculation

## Swarm Prompt

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
1. **TourSchedule timeline** renders with all rounds from `GET /seasons/{id}/schedule`; current round highlighted with color/icon/border accent
2. **Round status** correctly calculated:
   - Completed: `end_date < today` OR final standings posted
   - Current: `today >= start_date AND today <= end_date`
   - Upcoming: `start_date > today`
3. **DivisionStandings** displays corps sorted by cumulative score (descending), grouped by division header, with brand color applied
4. **Score deltas** visible: between adjacent rounds (e.g., "+5 pts Round 2") and live updates (e.g., "+12 (live)" during current round)
5. **Live/Final toggle**:
   - Live: Polling enabled, refresh indicator animated, updates within 1 polling cycle (10-30s)
   - Final: Polling disabled, timestamp shown (e.g., "Final as of 2024-07-15 18:30")
6. **SeasonWorkshop integration**: TourSchedule + DivisionStandings render ↔ `season.status === "on_tour"`
7. **Polling lifecycle**: Starts auto-detect current round → begins polling → stops when round end-date passes
8. **Responsive layout**: Passes 320px (mobile), 768px (tablet), 1024px+ (desktop) with readable standings and timeline at all breakpoints
9. **TypeScript strict mode**: Zero compilation errors; all types exported; no implicit `any` except documented `@ts-ignore`
10. **Accessibility**: WCAG AA color contrast on divisions; live-update region marked `aria-live="polite"`; refresh indicator labeled
11. **Unit test coverage**:
    - Round status classification (3+ cases: past, current, future)
    - Standings sort order (cumulative score + tiebreaker)
    - Division filtering and grouping
    - Score delta calculation (round-to-round and live)
    - Polling start/stop on round transition
    - Live/final toggle state management