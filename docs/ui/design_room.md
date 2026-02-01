# Design Room

The Design Room is a two-pane page where users collaborate with creative staff roles to produce a show spec and prompt. On approval, the spec becomes a commissioned show artifact. On publish, the prompt passes through a Devil's Advocate review gate.

## URL

- `/design` — Thread selector: list existing threads or create new
- `/design/:showSlug` — Design room for a specific show

## Layout

### Thread Selector (`/design`)
- Lists all design threads via `GET /api/v1/design/threads`
- Shows slug, status badge, and has_spec indicator
- "New Thread" form creates via `POST /api/v1/design/threads`

### Thread Detail (`/design/:showSlug`)
- **Header**: Back button, slug, status badge, Publish button (when approved)
- **Left pane**: Design Chat — loads history on mount via `GET .../messages`, sends via POST
- **Right pane**: Artifact Panel with tabbed views (Brief / Prompt / Versions)

## Artifact Panel Tabs

| Tab | Read Endpoint | Write Endpoint |
|-----|--------------|----------------|
| Brief | `GET /api/v1/design/threads/{slug}/artifacts/brief` | `PUT .../artifacts/brief` |
| Prompt | `GET /api/v1/design/threads/{slug}/artifacts/prompt` | `PUT .../artifacts/prompt` |
| Versions | `GET /api/v1/design/threads/{slug}/versions` | — (read-only) |

## API Endpoints (v1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/design/threads` | Create thread |
| GET | `/api/v1/design/threads` | List threads |
| GET | `/api/v1/design/threads/{slug}/messages` | Get message history |
| POST | `/api/v1/design/threads/{slug}/messages` | Send message |
| GET | `/api/v1/design/threads/{slug}/artifacts/brief` | Read spec |
| PUT | `/api/v1/design/threads/{slug}/artifacts/brief` | Update spec |
| GET | `/api/v1/design/threads/{slug}/artifacts/prompt` | Read prompt |
| PUT | `/api/v1/design/threads/{slug}/artifacts/prompt` | Update prompt |
| POST | `/api/v1/design/threads/{slug}/lint` | Lint prompt |
| POST | `/api/v1/design/threads/{slug}/approve` | Approve spec |
| POST | `/api/v1/design/threads/{slug}/publish` | Publish thread |
| GET | `/api/v1/design/threads/{slug}/versions` | List approved versions |

## Prompt Linting (Judge Snare)

`POST .../lint` validates `show_prompt.md` against required sections, placeholder detection, content quality.

Returns three severity tiers:
- **required_fix** — must be resolved before publish
- **nice_to_have** — warnings
- **acceptable_risk** — informational

## Devil's Advocate Review Gate

Triggered by "Publish" button on approved threads. The gate persona is an opinionated DCI columnist — the kind who'd question a move from G to Bb-keyed instruments.

1. Auto-runs lint on open
2. Displays findings by severity (red/yellow/gray badges)
3. Manual checklist — all three items must be checked:
   - "I have reviewed the prompt for completeness"
   - "Edge cases and constraints are addressed"
   - "Evaluation rubric matches show goals"
4. "Confirm Publish" enabled only when: zero required_fix AND all checkboxes checked
5. Calls `POST .../publish`

## Status Lifecycle

```
draft → needs_review → approved → published
                     ↘ rejected
```

## Component Map

| Component | File | Purpose |
|-----------|------|---------|
| ThreadList | `components/ThreadList.tsx` | Thread selector + create form |
| DesignChat | `components/DesignChat.tsx` | Chat with history loading, role badges |
| ArtifactPanel | `components/ArtifactPanel.tsx` | Tabbed container (Brief/Prompt/Versions) |
| SpecViewer | `components/SpecViewer.tsx` | Brief view/edit + approve |
| PromptEditor | `components/PromptEditor.tsx` | Prompt view/edit + inline lint |
| VersionList | `components/VersionList.tsx` | Approved version list |
| DevilsAdvocate | `components/DevilsAdvocate.tsx` | Publish review gate modal |
| DesignRoom | `pages/DesignRoom.tsx` | Route orchestrator |
