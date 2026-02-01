# Design Room

The Design Room is a two-pane page where users collaborate with creative staff roles to produce a show spec. On approval, the spec becomes a commissioned show artifact.

## URL

- `/design` — Create a new show or select existing
- `/design/:showSlug` — Design room for a specific show

## Layout

Left pane: **Design Chat** — conversation with auto-routed role attribution based on message keywords (music, visual, guard, GE, admin).

Right pane: **Spec Viewer** — displays the current `spec.md` with edit and approve controls.

## Spec Format

Specs live at `shows/<slug>/spec.md` with YAML front matter containing metadata and provenance fields. On approval, a frozen copy is written to `shows/<slug>/spec_v<N>.md`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/design/shows` | Create show + empty spec |
| GET | `/api/design/shows/{slug}/spec` | Read current spec |
| PUT | `/api/design/shows/{slug}/spec` | Update spec content |
| POST | `/api/design/shows/{slug}/conversation` | Send message, get routed response |
| POST | `/api/design/shows/{slug}/approve` | Freeze spec, commission show |
| GET | `/api/design/shows/{slug}/versions` | List approved versions |

## Approval Flow

1. User clicks "Approve Show" in the spec viewer
2. Backend validates spec is non-empty
3. Copies `spec.md` to `spec_v<N>.md` with provenance in front matter
4. Updates `status.yaml` to `approved`
5. Show becomes field-ready (`check_field_ready()` returns True)
