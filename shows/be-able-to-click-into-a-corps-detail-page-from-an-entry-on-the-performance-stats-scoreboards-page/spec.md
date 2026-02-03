# Show Spec: Clickable Corps Entries on Scoreboards

## Show Concept

**Problem:** Corps entries in the scoreboards table are not navigable — inline detail toggles obscure the dedicated corps detail page with its full context (Overview, Roster, Runs, Shows, History tabs).

**Goal:** Replace inline detail toggles with **clickable navigation** to the corps detail page (`/corps/{corps_id}/overview`), providing users clear visual feedback and immediate access to full corps context.

**Impact:** Eliminates redundant UI, improves discoverability, and establishes scoreboards as a true gateway to corps information rather than a shallow read-only view.

---

## Musical Design

N/A — This is a UI navigation feature with no musical arrangement or tempo component.

---

## Visual Design

**Link Styling for Corps Names:**
- Corps name cell displays as a clickable link (underline, color change, `cursor: pointer` on hover)
- Primary target for navigation is the **bolded corps name text** — styled as a hyperlink
- Hover state: text color shifts to link color (typically primary blue or accent color)
- Active/visited state: name may appear in visited link color

**Row-Level Hover Behavior:**
- Entire row receives secondary hover effect: subtle background highlight or border
- Indicates row is clickable without competing with the primary link styling
- Reinforces discoverability for users who might not notice the underlined name alone

**Cursor Feedback:**
- `cursor: pointer` on corps name cell
- `cursor: pointer` on entire row (secondary affordance)

---

## Guard Design

N/A — This is a UI navigation feature with no movement vocabulary or visual design for performers.

---

## General Effect

Scoreboards shift from a shallow detail-toggle interface into a true navigation hub — users click corps names to instantly access full context (Overview, Roster, Runs, Shows, History tabs) with clear visual affordances (link styling, hover states) guiding discovery. The detail page loads without errors, and navigation is fluid with no page refresh delay.

---

## Constraints

- Corps name link must be the primary affordance (not competing with other row interactions)
- Navigation must work from any scoreboard view (season standings, competition results, etc.)
- Hover state must not interfere with row selection or other table interactions
- Link styling must meet accessibility standards (sufficient color contrast — WCAG AA minimum)
- Scoreboards table structure and sorting remain unchanged
- Corps detail page route (`/corps/{corps_id}/overview`) already exists and works
- No inline detail toggle removal — toggles will be hidden, not deleted (preserves state safety)
- No changes to scoreboards data fetching or filtering
- Frontend-only implementation (no backend API changes required)
- No data model changes — scoreboards endpoint (`GET /api/v1/scoreboards/corps`) already returns `corps_id`
- React Router navigation via `useNavigate()` hook — client-side routing only

---

## Deliverables

**File Modified:** `frontend/src/pages/ScoreboardsPage.tsx`

**Specific Changes:**
1. Remove state management:
   - Delete `selectedCorps` state variable initialization (~line 20)
   - Delete `setSelectedCorps` setter calls (~line 89)

2. Remove UI markup:
   - Delete detail panel expansion/collapse JSX (~30 lines, conditional expansion at lines ~108–139)

3. Add navigation:
   - Import `useNavigate` from `react-router-dom`
   - Create `navigate` hook instance in component body
   - Add `onClick` handler to corps name cell: `() => navigate(/corps/${corps_id}/overview)`
   - Make entire row clickable with same navigation target as secondary affordance

4. Add styling:
   - Apply link styling to corps name cell:
     - `color: primary-blue` (or design system link color)
     - `text-decoration: underline`
     - `cursor: pointer`
   - Apply row-level hover effect:
     - Subtle background highlight (2–5% opacity increase) or light border
     - `cursor: pointer` on entire row

**Test Coverage:**
- ✓ Clicking a corps name navigates to `/corps/{corps_id}/overview`
- ✓ Clicking anywhere on the row also navigates to the same URL
- ✓ Hover states display correctly (color change on name, highlight on row, cursor pointer)
- ✓ CorpsDetailV2 loads with all tabs functional (Overview, Roster, Runs, Shows, History)
- ✓ No console errors or TypeScript compilation errors
- ✓ No API calls made beyond existing scoreboards endpoint
- ✓ Page renders without visual regressions across all scoreboard views

---

## Swarm Prompt

You are building clickable corps entries on the scoreboards page. Replace inline detail toggles with direct navigation to the corps detail page (`/corps/{corps_id}/overview`). Style corps names as hyperlinks (underline, primary color, `cursor: pointer`), add row-level hover feedback (subtle background highlight), and wire click handlers to navigate. Ensure the primary affordance is the corps name itself — not competing with other row interactions. No changes to table structure, data fetching, or existing toggle markup (hide visually, don't remove). All scoreboards should navigate consistently to the same corps detail route.

---