# Corps Logo Generation

## Show Concept

A dynamic feature that empowers corps to generate thematically-aligned logos through an integrated "Generate Logo" button on each corps detail page. The system synthesizes the corps' strategic identityâ€”including strategy, history, philosophy, iconography, mascots, and color schemesâ€”into a cohesive visual mark. Logos are rendered as SVG artifacts, persisted in storage, and displayed prominently on the corps page as a centerpiece of visual identity.

**Scope**: Frontend implementation only. Backend endpoint (`POST /api/v1/corps/{corps_id}/generate-logo`) already exists and is fully functional.

---

## Musical Design

N/A â€” This is a UI feature, not a musical show.

---

## Visual Design

The "Generate Logo" button is a primary action element on the corps detail page, positioned above or adjacent to the corps profile information. Upon click, it:
1. Shows a loading state (spinner/progress indicator)
2. Calls the existing `generate-logo` API endpoint with corps metadata
3. Displays the generated logo in a floating card with graceful reveal animation
4. Persists the SVG artifact to backend storage (backend handles all I/O)
5. Provides refresh/download controls for the SVG artifact

**Visual hierarchy**: Logo display card (floating, silk-like unfold animation) â†’ Corps name/info â†’ Metadata panels.
**Responsiveness**: Logo scales gracefully on mobile; button remains accessible.
**Animation**: Silk-inspired unfold effect on logo reveal; subtle entrance on card appearance.

---

## Guard Design

**Floating logo card with subtle reveal animation.** Button triggers a silk-like unfold effect; SVG materializes with a graceful entrance. Clean, confident, no clutter.

**Visual anchor**: Corps colors inform the card styling; logo display area is centered and prominent.
**Motion**: Smooth fade-in for card container, graceful SVG reveal on load, subtle shadow/depth effects.

---

## General Effect

- **User Experience**: One-click logo generation with instant visual feedback and graceful animation
- **Backend Integration**: Leverage existing `POST /api/v1/corps/{corps_id}/generate-logo` API endpoint
- **Persistence**: Backend handles all storage (SVG saved to corps workspace); frontend displays cached result
- **Performance**: Asynchronous generation to avoid blocking the UI; loading state provides clear feedback
- **Accessibility**: Alt text for logo, keyboard-accessible button, clear error states, animated entrance respects `prefers-reduced-motion`

---

## Constraints

1. **Endpoint Only**: Must call existing `POST /api/v1/corps/{corps_id}/generate-logo` endpoint only
2. **Fallback Handling**: Backend automatically falls back to SVG generation if ComfyUI unavailable (no frontend error handling needed for fallback logic)
3. **Storage Format**: SVG only; all persistence handled by backend
4. **Frontend Scope**: Button + API call + floating card display with animation; no backend modifications
5. **Idempotency**: Regenerating a logo replaces the previous version (handled by backend)
6. **Scope Boundaries**: This feature does NOT include:
   - Backend modifications
   - API endpoint creation
   - Multi-format export
   - Historical logo versioning
   - Batch logo generation

---

## Deliverables

### Frontend
- [ ] Add "Generate Logo" button component (`frontend/src/components/GenerateLogoButton.tsx`)
  - Loading state with spinner
  - Error state with user-friendly message
  - Success callback to refresh logo display
  - Keyboard accessible (Enter/Space to trigger)

- [ ] Add floating logo card component (`frontend/src/components/LogoCard.tsx`)
  - Displays generated SVG with graceful reveal animation
  - Silk-like unfold effect on entrance
  - Respects `prefers-reduced-motion` preference
  - Download/refresh/delete controls
  - Fallback message if no logo exists

- [ ] Update Corps detail page (`frontend/src/pages/CorpsDetailV2.tsx`)
  - Integrate GenerateLogoButton above corps profile section
  - Integrate LogoCard as hero/centerpiece element
  - Load existing logo on page mount (GET call to backend)
  - Refresh logo display on successful generation

- [ ] Update API client (`frontend/src/services/v1.ts`)
  - Add `generateCorpsLogo(corpId)` method (POST)
  - Add `getCorpsLogo(corpId)` method (GET, returns SVG content or null)
  - Add `deleteCorpsLogo(corpId)` method (DELETE)

- [ ] Write frontend tests (`frontend/src/__tests__/GenerateLogoButton.test.tsx`, `frontend/src/__tests__/LogoCard.test.tsx`)
  - Button renders and is keyboard accessible
  - Loading state appears during API call
  - Error message displays on failure
  - Logo card animates on successful generation
  - Download/refresh/delete controls are functional

### Documentation
- [ ] Add logo generation workflow to `docs/shows/` or `docs/frontend/`

---

## Swarm Prompt

### Objective
Implement a frontend "Generate Logo" feature on the corps detail page that calls an existing backend API endpoint and displays the generated SVG with graceful animation. The feature includes a button trigger, loading/error states, a floating animated card display, and refresh/download/delete controls.

### Deliverables
- **GenerateLogoButton.tsx**: Button component with loading/error states and keyboard accessibility
- **LogoCard.tsx**: Floating card with SVG display, silk-like reveal animation, and control buttons
- **CorpsDetailV2.tsx**: Integration of button and card into existing corps detail page layout
- **v1.ts API client**: Three new methods â€” `generateCorpsLogo()`, `getCorpsLogo()`, `deleteCorpsLogo()`
- **Frontend tests**: Vitest coverage for all new components (button render, animation, accessibility, API calls)
- **Documentation**: Workflow guide for logo generation feature

### Constraints
- **Endpoint**: Use ONLY the existing `POST /api/v1/corps/{corps_id}/generate-logo` endpoint (do NOT create new endpoint)
- **No backend changes**: All work is frontend-only; backend handles storage, fallback logic, and persistence
- **Animation**: Graceful reveal with silk-like unfold effect; must respect `prefers-reduced-motion`
- **SVG format**: Display SVG natively in DOM; no raster conversion
- **Scope**: Button + API call + animated card display only; no versioning, no batch generation, no export formats
- **Accessibility**: Keyboard-accessible button, alt text on SVG, clear error messaging

### Acceptance Criteria
1. "Generate Logo" button renders on corps detail page above profile section âœ“
2. Button click calls `POST /api/v1/corps/{corps_id}/generate-logo` with loading spinner âœ“
3. Generated SVG displays in floating card with graceful animation (silk-like unfold) âœ“
4. Existing logos load on page mount via `GET /api/v1/corps/{corps_id}/logo` âœ“
5. Download control saves SVG file to user's device âœ“
6. Refresh control calls generate endpoint again âœ“
7. Delete control removes logo and hides card âœ“
8. Error states display user-friendly messages (API failure, network error, etc.) âœ“
9. All new components have > 80% test coverage in vitest âœ“
10. Animation respects `prefers-reduced-motion` media query âœ“
11. No console errors or accessibility violations (a11y audit) âœ“
12. Mobile responsive and keyboard fully accessible âœ“