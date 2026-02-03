# Clickable Corps Entries on Scoreboards

## Objective
Replace inline detail toggles on the scoreboards page with direct navigation to the corps detail page (/corps/{corps_id}/overview). Style corps names as hyperlinks with row-level hover feedback.

## Deliverables
- Modified frontend/src/pages/ScoreboardsPage.tsx:
  - Remove selectedCorps state and inline detail panel
  - Add useNavigate hook from react-router-dom
  - Add onClick to corps name cell navigating to /corps/{corps_id}/overview
  - Make entire row clickable as secondary affordance
  - Link styling: underline, primary color, cursor pointer
  - Row hover: subtle background highlight
- No backend changes required

## Constraints
- Corps name link is primary affordance
- Navigation works from all scoreboard views
- No changes to table structure, data fetching, or sorting
- Inline toggles hidden, not deleted
- Frontend-only implementation
- WCAG AA color contrast for link styling

## Acceptance Criteria
- Clicking corps name navigates to /corps/{corps_id}/overview
- Clicking anywhere on row navigates to same URL
- Hover states display correctly
- CorpsDetailV2 loads with all tabs functional
- No console errors or TypeScript compilation errors
- No visual regressions across scoreboard views