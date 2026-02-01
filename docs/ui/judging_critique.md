# Judging & Critique

The Judging & Critique page provides post-run analysis of caption scores, structured critique feedback, and actionable routing to staff roles.

## URL

- `/judging` — Enter a corps ID to load
- `/judging/:corpsId` — Direct link to a corps' judge tapes

## Tabs

### Judge Tapes

Per-rep breakdown of caption scores with composite scoring. Each tape shows:

- Caption scores by judge type (brass, percussion, guard, visual, general effect, timing)
- Composite score with rework/escalation flags
- Detailed critique feedback with strengths, weaknesses, and action items
- **Export** button generates a consolidated markdown artifact (judge tape)

### Critique to Actions

Extracts actionable notes from all critiques and routes them to the responsible caption head or designer role:

| Caption | Target Role |
|---------|-------------|
| brass | brass_caption_head |
| percussion | percussion_caption_head |
| guard | guard_caption_head |
| visual | visual_caption_head |
| general_effect | program_coordinator |
| timing | timing_judge |

Actions are grouped by target role for triage.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/judging/corps/{corpsId}/tapes` | All judge tapes for a corps |
| GET | `/api/judging/corps/{corpsId}/tapes/{repId}` | Detailed critique for a rep |
| GET | `/api/judging/corps/{corpsId}/actions` | Critique-to-actions routing |
| GET | `/api/judging/corps/{corpsId}/tapes/{repId}/export` | Markdown export of judge tape |

## Score Thresholds

- **≥ 80**: Strong execution — strengths highlighted
- **60–79**: Acceptable with room for improvement
- **< 60**: Below standards — action items generated, rework flagged
- **< 40**: Escalation to executive director/user
