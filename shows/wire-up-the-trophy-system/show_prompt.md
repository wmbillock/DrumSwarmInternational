## Objective

Complete the trophy system by wiring achievement detection into the agent session lifecycle at appropriate moments (rehearsal wrap-up, post-competition, post-finals), creating a new "Results and Rankings" tab with separate trophy and standings subtabs, and connecting awarded trophies to the frontend UI so corps see real-time recognition of their accomplishments alongside competition standings.

## Deliverables

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

## Constraints

- Must use existing DB model, detector, and API endpoints (`/awards`, `/awards/summary`)
- No new trophy tier levels or categoriesâ€”work within current 5 tiers and 12 categories
- Achievement detection must not block session completion or performance scoring (async execution required)
- Trophy display must be read-only in this iteration (no manual award/revocation)
- "Results and Rankings" tab must not interfere with existing competition/standings UI
- Subtabs must be distinct and clearly separated (not merged or nested confusingly)
- Rehearsal awards must not interfere with regular session workflow completion
- Achievement detection must be idempotent (no duplicate awards for same achievement)

## Acceptance Criteria

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