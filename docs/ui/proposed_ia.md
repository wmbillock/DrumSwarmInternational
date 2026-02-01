# Proposed Information Architecture

> Preserves the drum corps metaphor. Maps existing backend capabilities to a coherent UI surface.

---

## Navigation Structure

```
┌─────────────────────────────────────────────────────────┐
│  DCI Swarm                              [Health] [Theme]│
├───────┬─────────────────────────────────────────────────┤
│ CMD   │                                                 │
│ DSN   │  ← Current page content                        │
│ SHW   │                                                 │
│ CRP   │                                                 │
│ JDG   │                                                 │
│ EVO   │                                                 │
│ HST   │                                                 │
│ RUN   │                                                 │
│ TPL   │                                                 │
│ PFM   │                                                 │
└───────┴─────────────────────────────────────────────────┘
```

### Primary Sections

| Icon | Label | Route | Metaphor | Purpose |
|------|-------|-------|----------|---------|
| CMD | Command Center | `/` | DCI HQ Operations Room | System vitals, corps status, recent activity |
| DSN | Design Room | `/design`, `/design/:slug` | Winter design sessions | Collaborate on show spec, approve for production |
| SHW | Shows | `/shows` | Show catalog | Create, activate, complete, delete shows |
| CRP | Corps | `/corps`, `/corps/:id`, `/corps/:id/:tab` | Corps deep dive | 12-tab view: command room, roster, sheets, field, reps, tape, banquet, stand, chart, books, season, history |
| JDG | Judging | `/judging`, `/judging/:corpsId` | Judge's booth | Tapes, critiques, action items |
| EVO | Evolution | `/evolution` | Talent development | Performer genomes, selection events, mutations |
| HST | Corps History | `/history`, `/history/:corpsId` | Hall of fame / film room | Season placements, seance sessions (retrospective) |
| RUN | Runs | `/runs`, `/runs/:runId` | Performance recordings | Run manifests, output logs |
| TPL | Templates | `/templates` | Playbooks | Show template browser + instantiation |
| PFM | Performers | `/performers` | Talent roster | Trust scores, capability ledger, retirement |

### Secondary Surfaces

| Route | Purpose | Access |
|-------|---------|--------|
| `/admin` | Admin corps / "The Bar" chat | Header nav |
| `/seance-session/:seanceId` | Active seance session | Launched from Corps History |
| `/seance` | Legacy memory query | Nav (labeled "Legacy", candidate for removal) |

---

## Information Architecture Map

### 1. Design Room (pre-production)

The show's lifecycle begins here. A user collaborates with creative staff roles to produce a spec. On approval, the spec freezes and the show is field-ready.

```
/design                    → Create new show or pick existing
/design/:showSlug          → Two-pane: DesignChat + SpecViewer
```

**Data flow:** User messages → note_router tags → role attribution → design_notes.md → spec.md → approve → spec_v{N}.md + status "approved"

**Existing endpoints (all implemented):**

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/design/shows` | Create show + empty spec |
| GET | `/api/design/shows/{slug}/spec` | Read current spec |
| PUT | `/api/design/shows/{slug}/spec` | Update spec |
| POST | `/api/design/shows/{slug}/conversation` | Routed message |
| POST | `/api/design/shows/{slug}/approve` | Freeze + approve |
| GET | `/api/design/shows/{slug}/versions` | Version list |

### 2. Shows (production management)

Shows move through `draft → active → completed → archived`. Activation spawns a corps with agent roster.

```
/shows                     → Show grid with status badges, create form
```

**Existing endpoints (all implemented):**

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/shows` | Create show |
| GET | `/api/shows` | List shows |
| GET | `/api/shows/{id}` | Get show |
| POST | `/api/shows/{id}/activate` | Activate (spawn corps) |
| POST | `/api/shows/{id}/complete` | Complete |
| POST | `/api/shows/{id}/tour` | Toggle tour mode |
| DELETE | `/api/shows/{id}` | Delete |
| GET | `/api/shows-overview` | Dashboard summary |
| GET | `/api/show-templates` | List templates |
| GET | `/api/show-templates/{name}` | Get template |
| POST | `/api/show-templates/instantiate` | Instantiate |

### 3. Corps (execution)

The corps is the primary execution context — a group of agents working a show through rehearsal phases.

```
/corps                     → Corps list (filesystem workspaces)
/corps/:corpsId            → 12-tab deep dive
/corps/:corpsId/:tab       → Direct tab link
```

Tabs map to DCI metaphor:

| Tab | Metaphor | Content |
|-----|----------|---------|
| command | Command Room | Chat with agents, mode controls, swarm commands |
| roster | Roster | Agent sessions with roles, model tiers, classification |
| sheets | Sheets | Competition scoresheet (captions, composite, penalties) |
| field | The Field | Segment tree visualization (movements/sets/segments) |
| reps | Reps | Rep (task) list with status tracking |
| tape | The Tape | Work log / activity feed |
| banquet | Banquet | Season retrospective report |
| stand | The Stand | Metrics and standings |
| chart | Chart | Show structure visualization |
| books | Books | Agent memories and documentation |
| season | Season | Season transitions, ageouts, self-improvement |
| history | History | Corps competition history |

**Existing endpoints (all implemented):** See inventory.md § 2 "Corps" section (15+ endpoints).

### 4. Judging & Critique (quality)

Judges score reps on DCI captions (brass, percussion, guard, visual, GE, timing). Critiques generate action items.

```
/judging                   → Select corps
/judging/:corpsId          → Tape browser, critique detail, action items
```

**Existing endpoints (all implemented):**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/judging/corps/{id}/tapes` | All scored reps |
| GET | `/api/judging/corps/{id}/tapes/{rep}` | Detailed critique |
| GET | `/api/judging/corps/{id}/actions` | Critique → action items |
| GET | `/api/judging/corps/{id}/tapes/{rep}/export` | Markdown export |

### 5. Evolution & Talent Pool (meta-optimization)

Performers are tracked across seasons. Trust scores, capability ledgers, and genome views drive selection.

```
/evolution                 → Genomes, selection events, mutations, simulation
```

**Existing endpoints (all implemented):**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/evolution/performers/{id}/genome` | Full genome |
| GET | `/api/evolution/events` | Selection events |
| GET | `/api/evolution/mutations` | Mutation log |
| POST | `/api/evolution/simulate-mutation` | Sandbox simulation |

### 6. Corps History & Seance (retrospective)

Corps history entries anchor seance sessions — grounded ED conversations about past shows.

```
/history                   → Select corps
/history/:corpsId          → History index, "Start Seance" per entry
/seance-session/:seanceId  → ED chat with binder + artifact preview
```

**Existing endpoints (all implemented):**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/corps/{id}/history-index` | Build/return history index |
| POST | `/api/seances` | Create seance session |
| GET | `/api/seances/{id}` | Session metadata |
| GET | `/api/seances/{id}/binder` | Context binder |
| GET | `/api/seances/{id}/transcript` | Read transcript |
| POST | `/api/seances/{id}/message` | Send message to ED |
| GET | `/api/seances/{id}/artifact-preview` | Preview artifact |

---

## Required API Endpoints — Gap Analysis

After reviewing all 88 existing endpoints against the proposed IA, **no new endpoints are required**. Every surface in the proposed architecture is already backed by implemented API routes.

### Possible Future Endpoints (not required now)

These are additive enhancements that could improve the IA without changing existing behavior:

| Method | Path | Purpose | Priority |
|--------|------|---------|----------|
| GET | `/api/design/shows` | List all design shows (currently no list endpoint — user must know slug) | Medium |
| DELETE | `/api/design/shows/{slug}` | Delete a design show workspace | Low |
| GET | `/api/seances` | List all seance sessions (currently no list endpoint) | Low |
| POST | `/api/seances/{id}/close` | Close a seance session via API (currently only via service) | Low |
| GET | `/api/corps/{id}/history-index/{entry_id}` | Get single history entry (currently must fetch full index) | Low |
| PATCH | `/api/design/shows/{slug}/spec` | Partial spec update (section-level) | Low |
| GET | `/api/shows/{id}/design-status` | Bridge show → design room (is spec approved?) | Low |

### Recommended Cleanup

| Item | Action |
|------|--------|
| `/seance` route + `Seance.tsx` | Remove or redirect to `/history`. The legacy memory-bank query is superseded by seance sessions. Already labeled "Legacy" in nav. |
| `/admin` route | Consider folding into Command Center or making it a corps tab. Currently orphaned in header nav. |
| SideNav ordering | Current order is reasonable. Rename "PFM" (Performers) from the header-only nav into the sidebar for discoverability. |

---

## Show Lifecycle Through the IA

```
Design Room         Shows              Corps                   History
───────────         ─────              ─────                   ───────
/design/:slug  →    /shows         →   /corps/:id          →  /history/:id
                    [Activate]         12 tabs                 [Start Seance]
spec.md         →   draft→active  →    agents work show   →   retrospective
approve         →   corps spawned      rehearse→tour→done      ED conversation
spec_v{N}.md        ↓                  scores, critiques       grounded in
                    [Complete]         banquet                  artifacts
                    active→completed
```

---

## Testing Notes

The repo has a mature pytest setup (77 test files, ~13K lines). All feature areas in this IA have existing test coverage:

- Design Room: `test_design_room.py` (20 tests)
- Seance: `test_seance_session.py` + `test_seance_routes.py` + `test_ed_chat.py` (~25 tests)
- Judging: `test_judging_routes.py`
- Evolution: `test_evolution_routes.py`
- Corps History: `test_corps_history.py`
- Workspace: `test_workspace_routes.py`

Any new endpoints from the "Possible Future Endpoints" table should follow the existing TestClient pattern in `conftest.py` (in-memory SQLite + `monkeypatch` for `DCI_PROJECT_ROOT`).
