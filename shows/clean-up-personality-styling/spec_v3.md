---
show_slug: clean-up-personality-styling
version: 3
created_at: '2026-02-01T04:34:15.390640+00:00'
approved_at: '2026-02-01T09:20:09.932334+00:00'
approved_by: user
roles_consulted: []
model: null
run_id: null
---

# Clean up personality styling

## Decisions

### 1. Automatic Corps Theme Switching via Hook
- Created new `useCorpsContext` hook in `frontend/src/hooks/useCorpsContext.ts`
- Hook automatically detects route changes and applies corps themes when entering `/corps/:corpsId` routes
- Automatically restores user's original theme when leaving corps context
- User theme preference is persisted in localStorage separately from active theme

### 2. Centralized Theme Management
- Theme switching logic moved from individual pages to the AppLayout component
- All pages benefit from automatic theme management without individual implementations
- Corps-specific pages no longer need manual theme management code

### 3. Visual Distinction Between Command Center and Shows
- Command Center: Blue-tinted background with operational styling, uppercase title with "▸" prefix
- Shows: Red-tinted background with creative styling, italic title with "♪" prefix
- Different visual treatments help users immediately recognize which context they're in

## Implementation Details

### Files Created
1. `frontend/src/hooks/useCorpsContext.ts`
   - New hook that manages automatic theme switching based on route context
   - Tracks current route and applies appropriate corps theme
   - Saves and restores user theme preference when entering/leaving corps context

### Files Modified
1. `frontend/src/layouts/AppLayout.tsx`
   - Added `useCorpsContext()` hook call to enable automatic theme management app-wide
   - Theme switching now happens at the layout level

2. `frontend/src/pages/CorpsDeepDive.tsx`
   - Removed manual theme switching logic (lines with `setCorpsTheme`, `userThemeRef`)
   - Removed import of `useCorpsTheme` as it's no longer needed
   - Simplified back button to not manually restore theme

3. `frontend/src/pages/SwarmOverview.tsx`
   - Added page title "Shows" for consistency with Command Center

4. `frontend/src/App.css`
   - Added `.command-center` styles with blue gradient background and operational styling
   - Added `.dashboard` (Shows) styles with red gradient background and creative styling
   - Visual distinction through color, typography, and iconography

## Open Questions

None - all requirements from design notes addressed.

## Constraints

- Theme switching relies on route patterns (`/corps/:id`)
- Corps must have a `theme_id` field in their data
- Fallback to default theme if corps theme_id is invalid
