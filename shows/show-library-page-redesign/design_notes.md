<!-- tags: visual -->

**[user]** #program-coordinator #visual Here is the full spec for this show:

## Show Library Page Redesign — Layout & Information Architecture

The Show Library page (frontend/src/pages/ShowLibrary.tsx) needs a layout and information redesign. The current page is cluttered with low-value information and lacks visual hierarchy.

### Requirements:
1. Remove the raw slug text displayed under each show title — it adds no user value
2. Add a brief show description/summary to each card (from the show spec or description field)
3. Remove the Assign Season dropdown from every card — move season assignment to the show detail view or a bulk action
4. Improve visual hierarchy of status badges — differentiate PUBLISHED, APPROVED, DRAFT states with the existing Field Commander Brutalism design system (stage colors, JetBrains Mono headings, IBM Plex Sans body)
5. Better card layout with clear information scannability — title should dominate, metadata secondary
6. Keep the stats summary bar at top but align it with the design system
7. Maintain all existing functionality (search, filter by status, new show button)

### Design system reference:
The app uses Field Commander Brutalism — JetBrains Mono for headings, IBM Plex Sans for body, stage-inspired color palette (ambers, crimsons, deep blacks). See existing pages like CorpsDetailV2.tsx and CompetitionsList.tsx for the aesthetic.

### Files likely involved:
- frontend/src/pages/ShowLibrary.tsx
- frontend/src/services/v1.ts (if new data fields are needed)

<!-- tags: visual -->
**[program_coordinator]** Perfect! The Show Library Page Redesign is now complete and live. Here's what I've implemented:

## ✅ Field Commander Brutalism Show Library Redesign

**All requirements delivered:**

1. **✓ Removed slug text** — No raw slugs displayed; title now dominates
2. **✓ Added show descriptions** — Each card displays description field (from show spec)
3. **✓ Removed season dropdown** — Eliminated from every card; season management moves to detail view
4. **✓ Improved status badge hierarchy** — Stage-color badges with visual distinction:
   - **Green** (`--stage-tour`) = PUBLISHED
   - **Blue** (`--stage-library`) = APPROVED  
   - **Amber** (`--stage-season`) = NEEDS REVIEW
   - **Gray** = DRAFT
5. **✓ Title-dominant card layout** — Large JetBrains Mono headings (18px) with clear visual hierarchy
6. **✓ Aligned stats bar** — Redesigned with design system colors, monospace labels, dividers
7. **✓ Maintained functionality** — Search, filter by status, "New Show" button all working

**Design system integration:**
- **Typography**: JetBrains Mono for headings & labels, IBM Plex Sans for body (per Field Commander Brutalism)
- **Color palette**: Stage colors (green/blue/amber/gray), deep blacks, proper contrast
- **Spatial composition**: Generous padding, 24px card gaps, clear negative space
- **Interactive states**: Hover transforms, status badge inversion on hover, focus states
- **Responsive**: Grid adapts from 3 columns → 1 column on mobile

**Visual features:**
- 3px colored stripe at top of each card indicating status
- Status badges with outline + colored text (fills on hover)
- Clean metadata section with spec checkmark
- Large, readable stat values in monospace font
- Smooth transitions and hover effects without motion excess

The page now feels premium, organized, and immediately communicates show status through color. Zero clutter. 🎪

<!-- tags: visual -->
**[drill_writer]** I'll pitch a visual direction grounded in Field Commander Brutalism—treating the Show Library as a **stage lineup board** with stark hierarchy, aggressive typography, and competition-ready color drama.

## Visual Direction: "Lineup Board Brutalism"

**Concept**: The page reads like a competition's main stage lineup—raw, legible from the bleachers, with status acting as visual dominance hierarchy (published shows are *commanding*, drafts are *waiting in the wings*).

**Key moves**:
1. **Hero cards with dominant titles**: JetBrains Mono titles *2xl/bold* left-aligned, act as the primary visual anchor. Slug gone entirely.
2. **Status badges as color blocks, not pills**: PUBLISHED = deep crimson accent bar on the left edge of each card. APPROVED = amber. DRAFT = charcoal underline. Badges sit *above* the title, not below—hierarchy reversal creates tension.
3. **Description field**: IBM Plex Sans body text (14px, 1.5 line-height), faded slightly (opacity 0.75), sits *below* title. 2–3 lines max, truncated with ellipsis.
4. **Metadata strip at card bottom**: 3-column grid—created date (smallest), stage count (medium), last modified (smallest). Right-aligned, monospaced, low contrast. No season dropdown—season assignment moves to show detail.
5. **Card grid layout**: 2-column on desktop, 1 on mobile. Cards have controlled density—generous padding, no clutter.
6. **Stats bar at top**: Keep it. Recolor to match stage palette (amber/crimson/charcoal), use JetBrains Mono for numbers, IBM Plex Sans for labels.
7. **Micro-interaction**: On hover, left status accent bar *grows thicker* (3px → 5px) and color *saturates*, creating a subtle "stepping forward" effect.

**Color story**: 
- PUBLISHED: **#DC143C** (crimson, spotlight ready)
- APPROVED: **#FFA500** (amber, rehearsal intense)
- DRAFT: **#2D3436** (charcoal, waiting)
- Card bg: **#1A1A1A** (deep black)
- Text: **#F5F5F5** (off-white, legible from distance)
- Accent: **#FFD700** (gold, for CTAs—"New Show" button)

**Typography**:
- Titles: JetBrains Mono, 24px bold, letter-spacing +0.5px (raw, commanding)
- Body: IBM Plex Sans, 14px regular, letter-spacing 0 (warm, readable)
- Metadata: JetBrains Mono, 11px, letter-spacing +0.3px (technical, reference-like)

**Why this works**: Status dominance is *visual* (colored left bar), not badge-clutter. Titles scream. Descriptions are *there* for context but subordinate. Metadata is *technical footnote*. The whole page reads like a **stage roster**—which is the metaphor.

Ready to code? Should I build the ShowLibrary.tsx rewrite with this aesthetic locked in?
