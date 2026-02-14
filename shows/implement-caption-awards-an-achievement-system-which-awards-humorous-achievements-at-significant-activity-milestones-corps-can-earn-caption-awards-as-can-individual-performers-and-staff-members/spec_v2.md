# Caption Awards Achievement System

## Goal
Implement an achievement system awarding humorous achievements at significant activity milestones. Corps, performers, and staff can all earn caption awards.

## Acceptance Criteria
1. 12 achievement categories with 30 achievements each (360 total)
2. Humor-first tone with concrete, measurable triggers
3. Three award scopes: corps-level, performer-level, staff-level
4. Detection mechanism based on activity transitions (rep completion, season milestones, etc.)
5. Achievement catalog stored as YAML definitions
6. Backend detection service that checks trigger conditions
7. Frontend display of earned achievements per corps/performer/staff
8. Achievement notification on earn
9. TypeScript compiles, tests pass

## Constraints
- Movement 1 (active): Design principles for Music, Drill, Guard, General Effect categories
- Movement 2 (pending): Detection system implementation
- Movement 3 (pending): Frontend display
- Achievement definitions must be specific, humorous, measurable, and tied to trigger contexts