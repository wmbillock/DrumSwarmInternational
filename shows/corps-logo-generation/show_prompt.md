## Objective
Implement a frontend "Generate Logo" feature on the corps detail page that calls an existing backend API endpoint and displays the generated SVG with graceful animation. The feature includes a button trigger, loading/error states, a floating animated card display, and refresh/download/delete controls.

## Deliverables
- **GenerateLogoButton.tsx**: Button component with loading/error states and keyboard accessibility
- **LogoCard.tsx**: Floating card with SVG display, silk-like reveal animation, and control buttons
- **CorpsDetailV2.tsx**: Integration of button and card into existing corps detail page layout
- **v1.ts API client**: Three new methods â€” `generateCorpsLogo()`, `getCorpsLogo()`, `deleteCorpsLogo()`
- **Frontend tests**: Vitest coverage for all new components (button render, animation, accessibility, API calls)
- **Documentation**: Workflow guide for logo generation feature

## Constraints
- **Endpoint**: Use ONLY the existing `POST /api/v1/corps/{corps_id}/generate-logo` endpoint (do NOT create new endpoint)
- **No backend changes**: All work is frontend-only; backend handles storage, fallback logic, and persistence
- **Animation**: Graceful reveal with silk-like unfold effect; must respect `prefers-reduced-motion`
- **SVG format**: Display SVG natively in DOM; no raster conversion
- **Scope**: Button + API call + animated card display only; no versioning, no batch generation, no export formats
- **Accessibility**: Keyboard-accessible button, alt text on SVG, clear error messaging

## Acceptance Criteria
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