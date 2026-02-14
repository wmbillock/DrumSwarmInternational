## Objective

Implement context-aware theming for the DCI UI where corps detail pages always use their assigned color palettes (with corps' own colors and naming conventions), while all other areas of the application respect the user's selected theme preference (Command Center or Shows). Automatic theme restoration occurs when navigating away from corps detail pages. Provide clear visual distinction between swarm-level operations (blue Command Center), creative operations (red Shows), and individual corps contexts (corps-specific colors) through background gradients, title treatments, and typography. Guard formations frame visual context transitions with geometric staging of color zones. Syncopated brass hits provide auditory punctuation for context shifts.

## Deliverables

- [ ] Create `frontend/src/hooks/useThemeContext.ts` to detect route context and manage theme/preference state with automatic restoration
- [ ] Create `frontend/src/components/ThemeSelector.tsx` for user theme preference selection with localStorage persistence and corps context awareness
- [ ] Modify `frontend/src/layouts/AppLayout.tsx` to integrate `useThemeContext()` hook for app-wide automatic theme management and restoration
- [ ] Add `.command-center` (blue gradient, uppercase â–¸ title) and `.shows` (red gradient, italic â™ª title) styles to `frontend/src/App.css` with clear visual distinction
- [ ] Add title treatment styles (`.command-center-title`, `.shows-title`) with distinct typography and prefixes
- [ ] Modify `frontend/src/pages/CorpsDetailV2.tsx` to ensure corps colors are applied on mount and theme is restored on unmount or navigation away
- [ ] Enhance `backend/api/v1/corps.py` to return corps color palette data (colors, names, structure) in detail endpoint with fallback support
- [ ] Update `backend/services/corps_service.py` to ensure corps have generated color palettes during initialization using corps' own colors and naming conventions
- [ ] Test theme persistence: user selects theme â†’ persists to localStorage â†’ applies on next non-corps page load
- [ ] Test corps detail pages: entering `/corps/:id` applies corps colors, leaving or navigating away restores user preference without manual action
- [ ] Test theme dropdown: functional outside corps context, disabled/hidden inside corps context, restores preference on exit
- [ ] Verify visual distinction: Command Center (blue) immediately recognizable from Shows (red) through color temperature and title treatment
- [ ] Verify corps contexts are visually distinct from both Command Center and Shows through corps-specific branding
- [ ] Test automatic theme restoration when navigating between pages while not in corps context
- [ ] Verify no console errors related to theme switching, localStorage access, or route changes

## Constraints

- Route-based detection: corps colors apply only to `/corps/:corpsId` and `/corps/:corpsId/*` patterns; all other routes use user theme preference
- Corps must have valid `theme_id` and color palette data; fallback to default theme if invalid
- User theme preference stored in `localStorage` as `user_theme_preference` (values: `command-center` or `shows`)
- Theme switching happens at layout/hook level, not in individual pages
- Theme dropdown disabled or hidden while viewing corps detail pages; display corps color indication instead
- No manual theme-switching UI for corps contextsâ€”automatic only based on route
- Corps color palettes must represent corps' own colors and naming, not generic UI theme names
- Theme restoration occurs when navigating away from `/corps/:id` routes; refresh within corps context preserves corps colors
- Command Center and Shows contexts must be immediately visually distinct through color (blue vs. red), title treatment (`â–¸` vs. `â™ª`), and typography
- Corps context must be visually distinct from both Command Center and Shows through corps-specific colors and branding
- Automatic theme restoration should be seamless and non-intrusive; no layout shift or visual glitches

## Acceptance Criteria

- [ ] Navigating to `/corps/:id` automatically applies that corps' color palette with corps' own colors and naming
- [ ] Navigating away from `/corps/:id` (to any non-corps route) automatically restores the user's previously selected theme (Command Center or Shows)
- [ ] Command Center context is immediately visually distinct from Shows context through blue gradient, uppercase â–¸ title, and professional typography
- [ ] Shows context is immediately visually distinct from Command Center context through red gradient, italic â™ª title, and creative typography
- [ ] Corps context is visually distinct from both Command Center and Shows through corps-specific colors and branding
- [ ] User theme preference persists across page refreshes and sessions via localStorage
- [ ] Theme dropdown functions correctly outside corps context and updates preference
- [ ] Theme dropdown is disabled/hidden or displays corps color indication inside corps context
- [ ] Theme switching is smooth and does not cause layout shift or visual glitches
- [ ] Invalid or missing corps color data falls back to default theme gracefully
- [ ] No console errors related to theme switching, localStorage access, or route changes
- [ ] Corps detail pages load with correct corps colors immediately
- [ ] Automatic theme restoration on corps detail exit is seamless and requires no user action
- [ ] User can change theme preference while not in corps context; change applies on next navigation away from corps
```