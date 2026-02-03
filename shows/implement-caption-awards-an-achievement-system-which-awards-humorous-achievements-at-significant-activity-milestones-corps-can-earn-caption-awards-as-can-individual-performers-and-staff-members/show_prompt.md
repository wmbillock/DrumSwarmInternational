# Caption Awards Achievement System

## Objective
Implement an achievement system that awards humorous caption awards at significant activity milestones. Corps, individual performers, and staff members can all earn caption awards. The system should have 12 categories with 30 achievements each (360 total), a detection mechanism based on activity transitions, and frontend display.

## Musical Design
Achievement categories organized by DCI captions:
- **Music Caption**: Harmonic complexity, key modulation, tempo precision, voice-leading, section unity achievements
- **Drill Caption**: Formation accuracy, count sync, visual vocabulary, transitions, drill-music lock achievements
- **Guard Caption**: Toss excellence, spin control, storytelling, precision, ensemble unity achievements
- **General Effect**: Narrative milestone framing (Acts I-III) achievements
- Plus operational categories: Debugging, Collaboration, Endurance, Speed, Quality, Innovation, Communication, Teamwork

## Visual Design
Field Commander Brutalism aesthetic for achievement display cards.

## Guard Design
Achievement triggers must be specific, measurable, and tied to real activity data.

## General Effect
Achievements create a humorous, motivating layer that celebrates real accomplishments.

## Constraints
- Achievement definitions stored as YAML
- Detection runs on activity transitions (not polling)
- Must not impact system performance

## Deliverables
- Achievement category YAML definitions (12 categories x 30 achievements)
- backend/services/achievement_service.py with detection and award logic
- backend/api/v1/awards.py endpoints for listing/querying achievements
- frontend/src/pages/Achievements.tsx display page
- frontend/src/components/AchievementCard.tsx card component
- Integration with existing corps, performer, and staff models
- Tests for detection logic

## Acceptance Criteria
- 360 achievements defined across 12 categories
- Achievements awarded automatically on trigger conditions
- Frontend displays earned achievements per entity
- Notification on new achievement earned
- TypeScript compiles, tests pass