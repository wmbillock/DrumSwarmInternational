# Systemic Display Formatting — Show Specification

**Show Slug:** `systemic-display-formatting`
**Status:** Draft → Needs Review
**Created:** 2026-02-01
**Director:** Program Coordinator (Design Lead)

---

## Show Concept

A meta-theatrical exploration of clarity under operational chaos. The show visualizes the invisible system that governs performance: how raw data transforms into legible command language under pressure.

The central thesis: **The system thinks in machines; the field speaks in humans.** This show is about the translation layer—the formatters that convert `snake_case_status_values` into readable commands that keep the corps unified during competition.

Conceptually, the show's progression mirrors a corps' journey from registration to contest readiness:
- **INITIALIZING** → raw, unmapped identity data
- **WINTER_CAMPS** → foundational formatting applied (status, role labels emerge)
- **ON_TOUR** → full formatting language in motion (captions, rehearsal modes, live display)
- **READY_FOR_CONTEST** → flawless legibility; zero ambiguity in field command

This is not a show *about* the DCI system—it's a show *that demonstrates* the DCI system's commitment to clarity. Every formatted value on every page is a small act of respect for the field staff and performers who depend on instant comprehension.

---

## Musical Design

TBD — awaiting design input from Music Writer and Drum Master.

**Placeholder directions:**
- Consider a minimalist approach: single-voice narration or sparse instrumentation reflecting "signal clarity from noise"
- Visual cues (melodic motifs) sync with formatting transformations on-screen (status changes, role assignments)
- Sonic palette should match Field Commander Brutalism aesthetic: clean, precise, unambiguous

---

## Visual Design

The show uses **Field Commander Brutalism** aesthetic with strict font hierarchy:

**Typography:**
- **Technical/Code values** (slugs, raw data): **JetBrains Mono** (monospace, 11-13px)
- **Formatted display values** (user-facing): **IBM Plex Sans** (sans-serif, 14-16px)
- **Hierarchy labels** (headers, roles): **IBM Plex Sans Bold** (16-20px)

**Color Palette:**
- **Stage Backdrop**: Deep navy (`#0a0e27`) — field at dusk
- **Active Elements**: Bright stage white (`#ffffff`) or corps primary color
- **Status States**:
  - `on_tour` / active: Lime green (`#00ff41`)
  - `winter_camps` / planning: Gold (`#ffd700`)
  - `ready_for_contest` / locked: Ice blue (`#4da6ff`)
  - `completed` / archived: Dim gray (`#666666`)
- **Warnings/Errors**: Coral red (`#ff6b6b`)

**Layout:**
- Cards and panels with high contrast borders
- Monospace values left-aligned for rapid scanning
- Formatted titles centered above tables/lists
- Minimal decoration; maximum clarity

**Animated Transitions:**
- Formatting occurs instantly (no fade-in/out of values)
- Status badge color shifts are immediate
- Page transitions use subtle slide/fade; never distract from data legibility

---

## Guard Design

The visual representation of the formatting system as a corps-in-motion:

**Formation 1 (Registration Phase):**
- 16-person "data block" enters in random order, holding cards with `snake_case_values`
- Chaos: collision, misalignment, unreadable positioning

**Formation 2 (Formatting Applied):**
- Guard marches through a series of "translator stations" (physical setups on field)
- Each station applies one formatter (role, status, caption, mode, slug-to-title)
- By the end of the block, every performer is aligned, positioned legibly, holding formatted display values
- Watch: random → organized, chaos → clarity

**Formation 3 (Live System):**
- 8 pages of the DCI system appear as projection overlays or LED displays
- Guard's positions correspond to field commander viewing angles—what looks clear from each position
- Final pose: Guard frozen in a formation that spells "FORMATTED" or shows key values legibly positioned

**Guard Equipment:**
- White or silver unis with navy trim (brutalism-aligned)
- Props: oversized cards, stage placards, or LED panels showing raw vs. formatted values
- Flags: simple navy/white; low visual clutter
- Sabers: minimal; this is not a saber-heavy show

---

## General Effect

**Visual Effect:**
Raw data chaos resolves into perfect legibility. The field becomes a live UI demonstrating the formatter's impact. By show end, every value on screen is readable from 200 yards away (simulating field commander viewing distance).

**Emotional Effect:**
Respect for clarity. Admiration for systems that serve performers and staff. The show communicates: "This system was built with you in mind. Every label, every status, every role name has been crafted for your success."

**Audience Takeaway:**
The DCI swarm is not just powerful—it is *thoughtful*. Behind every performance, every decision, every page view is a system that treats clarity as a core value.

**Integration with Swarm Narrative:**
This show proves that the swarm's infrastructure is human-centered. Formatters are not decoration; they're essential. Every page that uses `formatStatus()` or `formatRole()` is announcing: "The system respects you."

---

## Constraints

1. **Zero raw values on any public page** — every status, role, caption, and mode must be formatted before display
2. **Centralized utility** — all formatting logic lives in `frontend/src/utils/formatters.ts`; no scattered formatting across components
3. **Graceful fallback** — unknown/unmapped values return input as-is with console warning; system stays operational even if backend introduces new enum values before frontend updates
4. **Consistency across seven target pages**: CommandCenter, CorpsDetailV2, CompetitionLive, Scoreboards, SeasonWorkshop, SystemHealth, DesignRoom
5. **No breaking changes** — formatters must work with existing V1 API shapes; no backend schema changes required
6. **Font compliance** — JetBrains Mono for technical values, IBM Plex Sans for body; no deviation for readability
7. **Performance** — formatters are synchronous, sub-millisecond; no async lookups or API calls
8. **Accessibility** — formatted values must be screen-reader compatible; no abbreviations without full text equivalents

---

## Deliverables

### 1. **Core Utility Library** (`frontend/src/utils/formatters.ts`)

Five formatter functions with full test coverage:

```typescript
export function formatStatus(status: string): string
// Converts snake_case status values to Title Case with spaces
// Examples:
//   "on_tour" → "On Tour"
//   "winter_camps" → "Winter Camps"
//   "ready_for_contest" → "Ready for Contest"
//   "initializing" → "Initializing"
//   "unknown_status" → "unknown_status" (with console warning)

export function formatRole(role: string): string
// Converts role slugs to readable staff names
// Examples:
//   "music_writer" → "Music Writer"
//   "drill_writer" → "Drill Writer"
//   "percussion_caption_head" → "Percussion Caption Head"
//   "visual_designer" → "Visual Designer"
//   "unknown_role" → "unknown_role" (with console warning)

export function formatCaption(caption: string): string
// Converts caption identifiers to display names
// Examples:
//   "brass" → "Brass"
//   "percussion" → "Percussion"
//   "guard" → "Visual Guard"
//   "visual" → "Visual"
//   "unknown_caption" → "unknown_caption" (with console warning)

export function slugToTitle(slug: string): string
// Converts URL slugs/machine names to readable display titles
// Examples:
//   "percussion-assignment" → "Percussion Assignment"
//   "design_room" → "Design Room"
//   "competition_live" → "Competition Live"
//   "command_center" → "Command Center"
//   "unknown_slug" → "unknown_slug" (with console warning)

export function formatMode(mode: string): string
// Converts rehearsal mode values to display names
// Examples:
//   "basics" → "Basics"
//   "sectionals" → "Sectionals"
//   "full_ensemble" → "Full Ensemble"
//   "run_through" → "Run Through"
//   "unknown_mode" → "unknown_mode" (with console warning)
```

**Error Handling Strategy:**
- Unknown values return input as-is (graceful degradation)
- Console warning logged for unmapped values
- System remains operational; page doesn't crash
- Enables forward compatibility if backend adds new enum values

---

### 2. **Page Integration** (Seven Target Pages)

Each page fully updated to use formatters, with zero raw values displayed to users:

#### a. **CommandCenter** (`frontend/src/pages/CommandCenter.tsx`)
- **Before**: Raw status badges show `on_tour`, `winter_camps`
- **After**: All status displays use `formatStatus()`
- **Scope**: Status displays, lifecycle indicators, mode badges

#### b. **CorpsDetailV2** (`frontend/src/pages/CorpsDetailV2.tsx`)
- **Before**: Role lists show `music_writer`, `drill_writer`; status shows raw enum
- **After**: Use `formatRole()` for all staff listings, `formatStatus()` for corps state
- **Scope**: Staff roster, lifecycle controls, status panel, captions display

#### c. **CompetitionLive** (`frontend/src/pages/CompetitionLive.tsx`)
- **Before**: Raw mode values and status in live competition display
- **After**: Use `formatMode()` for rehearsal stage, `formatStatus()` for corps status
- **Scope**: Live scoreboard, mode indicator, real-time status updates

#### d. **Scoreboards** (`frontend/src/pages/Scoreboards.tsx`)
- **Before**: Raw status in leaderboard, role names in ranking detail
- **After**: Format all displayed values; clean, scannable leaderboard
- **Scope**: Status badges, role listings, filtered views

#### e. **SeasonWorkshop** (`frontend/src/pages/SeasonWorkshop.tsx`)
- **Before**: Raw page slugs, status values in season planning UI
- **After**: Use `slugToTitle()` for page labels, `formatStatus()` for corp/show state
- **Scope**: Season overview, show listings, corp status cards

#### f. **SystemHealth** (`frontend/src/pages/SystemHealth.tsx`)
- **Before**: Raw agent role names, mode indicators, status strings
- **After**: All agent roles formatted, mode names legible, status colors correct
- **Scope**: Agent overview, mode readiness, system status panel

#### g. **DesignRoom** (`frontend/src/pages/DesignRoom.tsx`)
- **Before**: Raw role names in routing hints, caption labels in context
- **After**: Use `formatRole()` and `formatCaption()` in UI hints and artifact panels
- **Scope**: Role indicators, caption selection dropdowns, response meta tags

---

### 3. **Test Suite** (`frontend/src/utils/formatters.test.ts`)

Comprehensive test coverage (50+ test cases):

```typescript
describe('formatStatus', () => {
  it('converts on_tour to On Tour', () => { /* ... */ })
  it('converts winter_camps to Winter Camps', () => { /* ... */ })
  it('converts ready_for_contest to Ready for Contest', () => { /* ... */ })
  it('returns unknown values as-is with warning', () => { /* ... */ })
  it('handles null/undefined gracefully', () => { /* ... */ })
  // ... more cases
})

describe('formatRole', () => {
  it('converts music_writer to Music Writer', () => { /* ... */ })
  it('converts drill_writer to Drill Writer', () => { /* ... */ })
  it('converts percussion_caption_head to Percussion Caption Head', () => { /* ... */ })
  it('returns unknown roles as-is with warning', () => { /* ... */ })
  // ... more cases
})

// Similar comprehensive coverage for formatCaption, slugToTitle, formatMode
```

---

### 4. **Documentation** (`frontend/src/utils/FORMATTERS.md`)

Quick reference guide:

```markdown
# Display Formatters

One-stop reference for all formatting functions. Includes:
- Function signatures and examples
- Complete enum mappings (status, role, caption, mode)
- Error handling strategy
- Integration checklist for new pages
- Performance notes (synchronous, <1ms per call)
```

---

### 5. **Integration Verification Checklist**

Before show completion, verify:

- [ ] **Zero raw values visible** on all seven target pages (manual inspection + screenshot audit)
- [ ] **All formatter functions** present in `formatters.ts` with no duplicate logic
- [ ] **Test suite** passes (50+ cases, all edge cases covered)
- [ ] **Console has zero "unmapped value" warnings** when browsing all pages with typical data
- [ ] **Fonts match aesthetic** — monospace for raw values, sans-serif for display
- [ ] **Color-coded status badges** align with Visual Design constraints
- [ ] **Accessibility audit** — formatted values are screen-reader compatible
- [ ] **Performance baseline** — no measurable rendering slowdown on any page

---

## Swarm Prompt

### Context & Thesis

You are implementing a **formatting standardization show** that eliminates raw, machine-readable values from the frontend. This show proves the DCI swarm is human-centered: every label, role, status, and caption is crafted for instant comprehension under performance pressure.

**Core Task:** Build a centralized formatter utility (`frontend/src/utils/formatters.ts`) with five functions, then integrate these formatters across seven pages, achieving **zero raw values visible to users**.

### Functional Requirements

1. **Create `frontend/src/utils/formatters.ts`** with these five functions:
   - `formatStatus(status: string): string` — converts `on_tour`, `winter_camps`, `ready_for_contest`, `initializing`, `completed` to Title Case
   - `formatRole(role: string): string` — converts `music_writer`, `drill_writer`, `percussion_caption_head`, etc. to readable staff names
   - `formatCaption(caption: string): string` — converts `brass`, `percussion`, `guard`, `visual` to display names
   - `slugToTitle(slug: string): string` — converts page slugs like `command-center`, `design_room` to "Command Center", "Design Room"
   - `formatMode(mode: string): string` — converts `basics`, `sectionals`, `full_ensemble`, `run_through` to display names

2. **Error Handling:** Unmapped values return input as-is with `console.warn()` — graceful degradation, forward-compatible

3. **Update seven target pages** (no raw values on any):
   - CommandCenter
   - CorpsDetailV2
   - CompetitionLive
   - Scoreboards
   - SeasonWorkshop
   - SystemHealth
   - DesignRoom

4. **Create test suite** (`formatters.test.ts`) with 50+ test cases covering all mappings, edge cases, unknown values

5. **Document** in `frontend/src/utils/FORMATTERS.md` with quick reference and integration checklist

### Design Aesthetic (Non-Negotiable)

- **JetBrains Mono** for raw/technical values; **IBM Plex Sans** for formatted display
- **Stage colors**: Navy backdrop, white/gold/green/blue status indicators per Visual Design
- **Zero clutter**: Formatting is for clarity, not decoration
- **Accessibility**: Screen-reader compatible, no abbreviations without full text

### Verification Checklist (Before Swarm Completion)

- [ ] `formatters.ts` exists and exports all five functions
- [ ] Each function has TypeDoc comments with examples
- [ ] Test suite passes (50+ tests, all mappings verified)
- [ ] All seven target pages integrate formatters; manual page audit finds zero raw values
- [ ] Console warnings do not appear on normal browsing (indicates good baseline coverage)
- [ ] Font CSS respects hierarchy (monospace → technical, sans-serif → display)
- [ ] Status colors align with Visual Design (green for on_tour, gold for winter_camps, blue for ready_for_contest, gray for completed)
- [ ] No API changes required (works with existing V1 shapes)

### Definition of Done

Show is complete when:
1. **`formatters.ts` is production-ready** — all functions tested, no unmapped common values, graceful fallback working
2. **All seven pages are verified formatter-compliant** — manual audit shows zero raw values in UI
3. **Test suite is comprehensive** — 50+ cases, all edge cases covered, 100% pass rate
4. **Documentation is complete** — FORMATTERS.md guides future integration
5. **Performance is confirmed** — <1ms per formatter call, zero perceptible UI impact
6. **Accessibility is verified** — WCAG 2.1 AA compliance, screen readers work correctly

---

## Notes for Designers

- **This show is about infrastructure, not spectacle.** Its success is measured in the absence of confusion, not in applause lines.
- **Every formatted value is a promise** — that the system respects the field staff and performers depending on it.
- **Guard choreography** should visualize the transformation: chaos → order. Use space, levels, and geometric formations.
- **Music should be sparse and precise** — signal clarity from noise, like a drill sergeant calling counts.
- **No technical jargon visible to audience** — even the guards' props should show before/after (raw value ↔ formatted value).

---
