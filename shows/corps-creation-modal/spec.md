---
show_slug: corps-creation-modal
version: 1
created_at: "2026-02-01T00:00:00Z"
approved_at: "2026-02-01T00:00:00Z"
approved_by: user
roles_consulted: [executive_director, drill_writer, program_coordinator]
---

# Corps Creation Modal

## Summary
Replace the inline "Create Corps" text input with a modal that auto-generates a corps identity (name, color scheme, mascot, iconography theme) and presents it to the user for approval or customization.

## Requirements

1. **Backend endpoint** `POST /api/v1/corps/generate-identity` returns a generated identity:
   - `name` — from nickname_generator.generate_corps_name()
   - `mascot` — from nickname_generator.generate_mascot()
   - `color_scheme` — object with `primary`, `secondary`, `accent` hex colors
   - `uniform_concept` — short text description
   - `icon_prompt` — a ChatGPT/DALL-E prompt for generating corps iconography

2. **Backend endpoint** `POST /api/v1/corps/generate-icon` accepts an icon_prompt and uses ChatGPT CLI to generate a description or image URL for the corps icon.

3. **Frontend modal** replaces the inline form:
   - On "Create Corps" click, call generate-identity, show modal with preview
   - User can regenerate individual fields or edit them
   - "Approve & Create" button calls POST /api/v1/corps with full identity
   - Color scheme shown as swatches
   - Mascot and uniform concept displayed

4. **Corps model** — already has `mascot`, `theme_id`, `uniform_concept` columns. Store color scheme in `theme_id` as JSON or add to uniform_concept.

## Decisions
- Color schemes are generated deterministically from the corps name hash
- Icon generation uses ChatGPT CLI if available, falls back to text description
- Theme stored as JSON in uniform_concept field

## Constraints
- 18-corps cap enforced on creation
- Must work without ChatGPT CLI (graceful fallback)
