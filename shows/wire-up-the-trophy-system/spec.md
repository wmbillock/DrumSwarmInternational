```markdown
---
show_slug: wire-up-the-trophy-system
version: 4
created_at: "2026-02-14T06:39:32.165121+00:00"
approved_at: "2026-02-14T06:45:00.000000+00:00"
approved_by: "user"
roles_consulted: ["program_coordinator"]
---

# Wire up the trophy system

## Show Concept

The trophy system is a recognition and achievement framework that awards corps with digital trophies across 12 achievement categories and 5 tier levels (bronze through diamond). This show focuses on completing the infrastructure wiringâ€”from achievement detection through UI presentationâ€”so that trophy awards are fully functional and visible to users in a new "Results and Rankings" tab with separate subtabs for trophies and competition standings, alongside corps rankings.

Trophies are awarded at multiple moments across the season:
- **During rehearsals**: Real-time recognition for exceptional performance moments
- **After competitions**: Formal awards following regular competition performances
- **After finals**: High-tier, significant awards following championship performances

## Musical Design

TBD â€” awaiting design input

## Visual Design

The trophy showcase will be displayed in a new "Results and Rankings" tab (relocated from "Swarm Health") with separate trophy and standings subtabs:

**Trophy Subtab:**
- Achievement category (e.g., "Best Brass," "Visual Excellence")
- Tier level (bronze, silver, gold, platinum, diamond)
- Achievement timestamp
- Organized by category and tier for easy scanning
- Uses `TrophyShowcase` UI component
- Read-only display of awarded trophies

**Standings Subtab:**
- Competition standings and corps rankings
- Integrated seamlessly with trophy display
- Shows current season performance rankings and placement

## Guard Design

TBD â€” awaiting design input

## General Effect

When corps complete performances, rehearsals, and sessions, the system automatically detects achievements at appropriate moments, awards trophies, and displays them prominently in the "Results and Rankings" tab (trophy subtab) alongside their rankings and standings (standings subtab), providing real-time recognition for rehearsal excellence and formal recognition after competitions and finals, maintaining visibility and motivation for excellence across multiple performance dimensions.

## Constraints

1. **Achievement detection endpoints exist**: `/awards` and `/awards/summary` endpoints are available but not wired into agent sessions
2. **DB model complete**: Full trophy infrastructure in place (model, 5 tiers, 12 categories, achievement catalog, detector)
3. **Frontend component exists**: `TrophyShowcase` UI component exists but has no data integration
4. **Achievement catalog**: 12 categories defined; detection logic exists but must be called at appropriate lifecycle points
5. **Tab location confirmed**: Trophies relocated from "Swarm Health" to new "Results and Rankings" tab
6. **Separate subtabs required**: Trophy and standings sections must be distinct subtabs within "Results and Rankings" tab
7. **Multiple trigger points**: Achievement checks triggered during rehearsals (for exceptional events) and after competitions/finals (for formal recognition)
8. **Non-blocking**: Achievement detection must not block session completion or performance scoring
9. **Read-only display**: Trophy display is read-only in this iteration (no manual award/revocation)
10. **No new categories/tiers**: Work within existing 5 tier levels and 12 achievement categories

## Deliverables

1. **Wire achievement detection into agent session lifecycle**
   - Identify exceptional event trigger criteria for rehearsal-time awards
   - Call `/awards` endpoint at rehearsal wrap-up, post-competition, and post-finals moments
   - Persist returned awards to database
   - Ensure non-blocking, asynchronous execution

2. **Create "Results and Rankings" tab structure**
   - New tab section replacing trophy display from "Swarm Health"
   - Implement navigation/routing for trophy and standings subtabs
   - Ensure both subtabs are accessible and clearly separated

3. **Implement trophy subtab display**
   - Query `/awards/summary` endpoint for corps trophies
   - Bind returned awards to `TrophyShowcase` component
   - Organize display by category and tier level
   - Ensure all 5 tier levels and 12 categories render without errors

4. **Implement standings subtab display**
   - Display competition standings and corps rankings
   - Integrate with existing standings/ranking UI patterns
   - Maintain consistency with competition results view

5. **End-to-end testing**
   - Session completion â†’ achievement detection â†’ award stored â†’ UI renders trophy
   - Verify all 12 categories and 5 tiers are accessible via UI
   - Test both rehearsal-time and post-competition award triggers
   - Confirm "Results and Rankings" tab displays both subtabs correctly

## Decisions

- **Trigger points**: Achievement checks wired into rehearsal wrap-up, post-competition performance completion, and post-finals moments
- **Rehearsal awards**: Triggered on exceptional event detection during rehearsals for real-time feedback
- **Competition/Finals awards**: Triggered after performance scoring is finalized and recorded
- **Existing infrastructure**: Leverage robust DB model, detector, and API endpoints already in place
- **UI location**: "Results and Rankings" tab (new) with separate trophy and standings subtabs
- **Subtab architecture**: Trophy and standings displayed as distinct subtabs for clear separation of concerns
- **Async execution**: Achievement detection runs asynchronously to avoid blocking session workflows

## Open Questions

1. **Retroactive awards**: Should trophies be retroactively awarded for existing completed sessions/performances?
2. **Competition-specific trophies**: Do certain trophies only award after regular competitions vs. finals?

## Swarm Prompt

### Objective

Complete the trophy system by wiring achievement detection into the agent session lifecycle at appropriate moments (rehearsal wrap-up, post-competition, post-finals), creating a new "Results and Rankings" tab with separate trophy and standings subtabs, and connecting awarded trophies to the frontend UI so corps see real-time recognition of their accomplishments alongside competition standings.

### Deliverables

- [ ] Define exceptional event criteria for rehearsal-time trophy awards
- [ ] Wire `/awards` endpoint calls into agent session completion handlers at rehearsal, post-competition, and post-finals moments
- [ ] Implement async/non-blocking award persistence to database
- [ ] Create "Results and Rankings" tab UI structure with routing
- [ ] Implement trophy subtab with `TrophyShowcase` component integration and `/awards/summary` data binding
- [ ] Implement standings subtab with competition standings/rankings display
- [ ] Organize trophy display by category and tier level
- [ ] Display standings/rankings in standings subtab
- [ ] End-to-end test: rehearsal â†’ award detection â†’ UI render in trophy subtab (within 2 seconds)
- [ ] End-to-end test: competition â†’ award detection â†’ UI render in trophy subtab (within 2 seconds)
- [ ] Verify all 5 tier levels and 12 categories render without errors
- [ ] Verify no regression in existing session/performance/scoring workflows

### Constraints

- Must use existing DB model, detector, and API endpoints (`/awards`, `/awards/summary`)
- No new trophy tier levels or categoriesâ€”work within current 5 tiers and 12 categories
- Achievement detection must not block session completion or performance scoring (async execution required)
- Trophy display must be read-only in this iteration (no manual award/revocation)
- "Results and Rankings" tab must not interfere with existing competition/standings UI
- Subtabs must be distinct and clearly separated (not merged or nested confusingly)
- Rehearsal awards must not interfere with regular session workflow completion
- Achievement detection must be idempotent (no duplicate awards for same achievement)

### Acceptance Criteria

- [ ] At least one achievement category awards a trophy during rehearsal wrap-up in a test session
- [ ] At least one achievement category awards a trophy after a test competition
- [ ] Trophy appears in "Results and Rankings" trophy subtab within 2 seconds of session completion
- [ ] `/awards/summary` correctly returns all awarded trophies for a corps
- [ ] All 5 tier levels render without styling errors in TrophyShowcase
- [ ] All 12 achievement categories are discoverable/visible in the UI
- [ ] "Results and Rankings" tab loads with both trophy and standings subtabs accessible
- [ ] Trophy subtab displays trophies organized by category and tier
- [ ] Standings subtab displays current competition standings correctly
- [ ] No regression in existing session completion workflows
- [ ] No regression in existing performance scoring workflows
- [ ] Achievement detection is truly non-blocking (no observable delay in session UI responsiveness)
```