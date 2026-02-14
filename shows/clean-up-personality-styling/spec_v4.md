```markdown
show_slug: clean-up-personality-styling
version: 4
created_at: "2026-02-01T04:34:15.390640+00:00"
approved_at: null
approved_by: null
roles_consulted: []
model: null
run_id: null
```

# Clean up personality styling

## Show Concept

Corps color themes are applied directly to corps detail page contexts without forcing global theme agent switching. When viewing a corps detail page at `/corps/:corpsId`, the UI applies that corps' custom color paletteâ€”generated during corps initialization using proper color representation, the corps' own colors, and the corps' own naming conventions. Everywhere else (Command Center, Shows directory, competitions, logistics, swarm-level operations), the UI respects the user's selected theme from the dropdown (Command Center or Shows context). The visual context shift via corps-specific colors helps users immediately recognize they're viewing a specific operational environment rather than the global DCI Command Center or Shows directory. Navigation away from corps detail pages automatically restores the user's previously selected theme without manual intervention.

## Musical Design

Syncopated brass hits punctuate theme changesâ€”one sharp stab per context shift. These rhythmic punctuations reinforce the visual context transitions when users move between Command Center (blue), Shows (red), and individual corps contexts (corps-specific colors). The brass accent serves as an auditory marker of operational context change, creating a clear multi-sensory distinction between swarm-level operations and corps-specific operations.

## Visual Design

### Command Center Context
- **Background**: Blue-tinted gradient background with operational styling
- **Title Treatment**: Uppercase with "â–¸" prefix (play/operational indicator)
- **Typography**: Professional, command-oriented
- **Color Scheme**: Cool blues representing systematic, administrative operations
- **Purpose**: Users recognize this as the DCI administrative/operational hub
- **Application**: Used throughout the UI except when viewing corps detail pages

### Shows Context
- **Background**: Red-tinted gradient background with creative styling
- **Title Treatment**: Italic with "â™ª" prefix (musical indicator)
- **Typography**: Creative, performance-oriented
- **Color Scheme**: Warm reds representing creative, performance-focused operations
- **Purpose**: Users recognize this as the creative/performance workspace
- **Visual Distinction**: Clear differentiation from Command Center through contrasting color temperature and title treatment
- **Application**: Used throughout the UI except when viewing corps detail pages

### Corps Detail Page Context
- **Corps Color Application**: When viewing `/corps/:corpsId`, the UI applies that specific corps' color palette (generated during corps initialization)
- **Color Palette Representation**: Corps colors use their own naming and proper palette structureâ€”not mapped to generic UI theme names
- **Visual Distinction**: Corps context is visually distinct from both Command Center and Shows through corps-specific colors and corps-specific visual branding
- **Scope**: Corps colors apply only to the corps detail page and its nested routes (`/corps/:corpsId/*`); does NOT propagate to other sections of the application
- **Theme Restoration**: When navigating away from corps detail pages, the previously selected theme (Command Center or Shows) is automatically restored
- **Automatic Context Switching**: No user interaction required for theme application or restorationâ€”determined entirely by route pattern

### Theme Persistence
- User's preferred theme (Command Center or Shows) is persisted in `localStorage` as `user_theme_preference`
- Corps color palette is applied at the page/layout level only for `/corps/:corpsId` routes
- User preference is automatically restored when exiting corps detail context without manual user action required
- Theme selection dropdown remains functional and allows users to switch between Command Center and Shows at any time (except while viewing corps details, which use corps colors)
- Corps color application is automatic and non-intrusive, occurring at the layout level

## Guard Design

Silk sabre silhouettes form stark, geometric staging that mirrors corps color shifts. Guards frame visual context transitions, moving between color zones as users navigate between Command Center (blue), Shows (red), and corps contexts (corps-specific colors). Guard formations create living frames for each context transition, with sabre work emphasizing the geometric staging of color zone boundaries. The guard's visual positioning and sabre lines reinforce the three operational contexts through spatial arrangement and color-responsive blocking.

## General Effect

The visual and auditory hierarchy provides immediate contextual awareness:

1. **Command Center** â†’ operational/administrative context (blue) â€” swarm-level operations, logistics, system administration
2. **Shows** â†’ creative/performance context (red) â€” show design, creative direction, performance tracking
3. **Corps Detail** â†’ individual corps operational context (corps' own colors) â€” corps-specific performance, history, operations

Users can navigate between these contexts and see clear visual feedback about where they are in the system. Theme selection is under user control via dropdown (Command Center or Shows), while corps detail pages always use their assigned corps colors. Theme switching is automatic and non-intrusive, occurring at the page/layout level rather than requiring individual page implementations. Syncopated brass hits provide auditory punctuation for context transitions, while guard formations frame the visual shift between color zones.

## Constraints

- Corps detail page context is restricted to `/corps/:corpsId` and its nested routes only
- Corps must have a `theme_id` field in their data pointing to their generated color palette
- Corps color palettes must be generated during corps initialization with proper color representation
- Fallback to default theme if corps `theme_id` is invalid or unavailable
- User theme preference (Command Center/Shows) persists in `localStorage` separately from active page theme
- localStorage keys used: `user_theme_preference` (persists Command Center/Shows choice)
- Theme persistence: user preference is restored when navigating away from `/corps/:corpsId` routes (not on refresh within corps context)
- Theme dropdown remains accessible and functional outside corps context; user can change preference at any time (applies on next page load outside corps context)
- Corps color application is automatic based on route pattern and does not require user action
- Visual distinction between Command Center (blue) and Shows (red) must be immediately apparent and not require examination
- Command Center and Shows contexts must have distinct title treatments (`â–¸` vs. `â™ª`) and typography styles
- Corps contexts must be visually distinct from both Command Center and Shows through corps-specific branding and color application

## Deliverables

1. **Theme Context Hook** (`frontend/src/hooks/useThemeContext.ts`)
   - Detects current route to determine active context (Command Center, Shows, or Corps)
   - Applies appropriate theme based on context and user preference
   - Manages localStorage persistence of user theme preference (`user_theme_preference`)
   - Returns current theme, user preference, and theme switching function for non-corps contexts
   - Auto-restores user preference when exiting `/corps/:corpsId` routes

2. **Layout Integration** (`frontend/src/layouts/AppLayout.tsx`)
   - Integrate `useThemeContext()` hook for app-wide automatic theme management
   - Apply theme to document root and UI container based on route context
   - Ensure corps detail pages always use corps colors; elsewhere use user preference
   - Handle theme restoration on route change away from corps context

3. **Styling** (`frontend/src/App.css`)
   - `.command-center` class with blue gradient background and operational styling
   - `.shows` class with red gradient background and creative styling
   - Title treatment styles: `.command-center-title` (uppercase with â–¸), `.shows-title` (italic with â™ª)
   - Corps color application via CSS variables or inline styles based on corps data
   - Ensure visual distinction between all three contexts with clear color temperature and typography differences

4. **Theme Dropdown Component** (`frontend/src/components/ThemeSelector.tsx`)
   - Allow users to select between Command Center and Shows themes
   - Persist selection to `localStorage`
   - Disable or hide while viewing corps detail pages (display current corps color indication instead)
   - Automatically apply selected theme when exiting corps context

5. **Corps Detail Route Integration** (`frontend/src/pages/CorpsDetailV2.tsx`)
   - Ensure corps color palette is loaded and applied when component mounts
   - Verify theme restoration occurs when component unmounts or when navigating away
   - Display corps-specific visual branding and context indicators

6. **Corps Theme Support** (Backend: `backend/services/corps_service.py`)
   - Ensure corps have properly generated color palettes during initialization
   - Validate `theme_id` field on corps objects
   - Provide color palette data structure via API (colors, names, palette representation)
   - Generate corps palettes using corps' own colors and naming conventions

7. **API Endpoint Enhancement** (`backend/api/v1/corps.py`)
   - Add corps color palette data to corps detail response
   - Include color palette metadata for UI consumption (palette structure, color names, hex values)
   - Ensure `theme_id` and palette data are present for all corps
   - Provide fallback color palette if corps `theme_id` is invalid

## Swarm Prompt

### Objective

Implement context-aware theming for the DCI UI where corps detail pages always use their assigned color palettes (with corps' own colors and naming conventions), while all other areas of the application respect the user's selected theme preference (Command Center or Shows). Automatic theme restoration occurs when navigating away from corps detail pages. Provide clear visual distinction between swarm-level operations (blue Command Center), creative operations (red Shows), and individual corps contexts (corps-specific colors) through background gradients, title treatments, and typography. Guard formations frame visual context transitions with geometric staging of color zones. Syncopated brass hits provide auditory punctuation for context shifts.

### Deliverables

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

### Constraints

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

### Acceptance Criteria

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