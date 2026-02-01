# Show Prompt: Systemic Display Formatting

## Objective
Create a centralized display formatting utility at `frontend/src/utils/formatters.ts` and apply it across all frontend pages to eliminate raw snake_case, slug, and enum values from the UI.

## Deliverable 1: formatters.ts

Create `frontend/src/utils/formatters.ts` with these exported functions:

### formatStatus(status: string): string
Converts backend status/state values to human-readable Title Case.
- `on_tour` -> `On Tour`
- `winter_camps` -> `Winter Camps`
- `ready_for_contest` -> `Ready for Contest`
- `in_progress` -> `In Progress`
- `completed` -> `Completed`
- `active` -> `Active`
- `disbanded` -> `Disbanded`
- `draft` -> `Draft`
- `needs_review` -> `Needs Review`
- `approved` -> `Approved`
- `published` -> `Published`
- **Fallback**: Unknown values -> convert snake_case to Title Case (replace underscores with spaces, capitalize each word), log `console.warn` with the unmapped value.

### formatRole(role: string): string
Converts role slugs to readable display names.
- `music_writer` -> `Music Arranger`
- `drill_writer` -> `Drill Designer`
- `choreographer` -> `Choreographer`
- `program_coordinator` -> `Program Coordinator`
- `percussion_caption_head` -> `Percussion Caption Head`
- `brass_caption_head` -> `Brass Caption Head`
- `color_guard_caption_head` -> `Color Guard Caption Head`
- `executive_director` -> `Executive Director`
- **Fallback**: snake_case to Title Case + console.warn.

### formatCaption(caption: string): string
Converts caption identifiers to display names.
- `brass` -> `Brass`
- `percussion` -> `Percussion`
- `color_guard` -> `Color Guard`
- `visual` -> `Visual`
- `general_effect` -> `General Effect`
- **Fallback**: snake_case to Title Case + console.warn.

### slugToTitle(slug: string): string
Converts URL-style slugs to readable titles.
- Replace hyphens with spaces, capitalize each word.
- `systemic-display-formatting` -> `Systemic Display Formatting`

### formatMode(mode: string): string
Converts rehearsal mode values to display names.
- `BASICS` -> `Basics`
- `SECTIONALS` -> `Sectionals`
- `FULL_ENSEMBLE` -> `Full Ensemble`
- `RUN_THROUGH` -> `Run-Through`
- **Fallback**: Title Case + console.warn.

## Deliverable 2: Apply Formatters to All Pages

Update these pages to import and use formatters wherever raw values are displayed:

1. **CommandCenter.tsx** (`frontend/src/pages/CommandCenter.tsx`) - Corps status badges, mode displays
2. **CorpsDetailV2.tsx** (`frontend/src/pages/CorpsDetailV2.tsx`) - Status, role names, caption names, mode
3. **CompetitionLive.tsx** (`frontend/src/pages/CompetitionLive.tsx`) - Status values, show slugs (use slugToTitle)
4. **Scoreboards.tsx** or **ScoreboardsPage.tsx** - Status/role display in rankings
5. **SeasonWorkshop.tsx** (`frontend/src/pages/SeasonWorkshop.tsx`) - Season/show status, show slugs
6. **SystemHealth.tsx** (`frontend/src/pages/SystemHealth.tsx`) - Corps status, system state values
7. **DesignRoom.tsx** (`frontend/src/pages/DesignRoom.tsx`) - Show status, role attribution on messages

For each page:
- Find every place a raw snake_case or slug value is rendered in JSX
- Replace with the appropriate formatter call
- Import only the formatters actually used

## Design Aesthetic
- Follow Field Commander Brutalism: JetBrains Mono for technical/code values, IBM Plex Sans for body text
- Formatted values are body text (IBM Plex Sans), NOT code
- Status badges should use formatted text

## Constraints
- Use the existing `frontend/src/services/v1.ts` API client (do not create new API calls)
- Do NOT modify backend code
- TypeScript strict mode must pass: `cd frontend && npx tsc --noEmit`
- Zero raw snake_case or slug values should appear in the rendered UI after this change

## Verification Checklist
- [ ] `frontend/src/utils/formatters.ts` exists with all 5 functions exported
- [ ] All 7 target pages import and use formatters
- [ ] `cd frontend && npx tsc --noEmit` passes with zero errors
- [ ] No raw snake_case values visible in any page component JSX
- [ ] Unknown values fall back gracefully (no crashes)
