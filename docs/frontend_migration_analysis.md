# Frontend Migration Analysis: api.ts → v1.ts

## Summary
25+ frontend files still use the legacy `api.ts` client. Migration to `v1.ts` requires creating missing v1 API endpoints first.

## Pages Using Legacy API (Priority Order)

### Tier 1: Critical (High Impact on Core Workflows)
1. **CommandCenter** - Dashboard, entrypoint page
   - Needs: Shows overview, corp status, metrics summary
   - API Calls: getShowsOverview(), getCorpsStatus()

2. **SwarmOverview** - Shows/agents/work logs view
   - Needs: Show CRUD, agent overview, work log queries
   - API Calls: getShowsOverview(), getAgentsOverview(), getGlobalWorkLog(), createShow(), deleteShow(), activateShow()

3. **CorpsDeepDive** - Legacy corps detail (replaced by CorpsDetailV2)
   - Needs: Corps history, agent sessions, performance data
   - API Calls: getCorpsHistory(), getAgentSessions()

### Tier 2: Important (Feature-Critical)
4. **AdminChat** - Admin messaging/commands
   - Needs: Message history, command execution
   - API Calls: getMessages(), sendMessage(), executeCommand()

5. **SystemHealth** - System monitoring
   - Needs: System health metrics, corps status
   - API Calls: getSystemHealth() — likely exists in v1, needs verification

6. **Performers** - Performer management
   - Needs: Performer list, audition data, assignment
   - API Calls: getPerformers(), auditionPerformer(), assignPerformer()

### Tier 3: Supportive (Feature-Specific)
7. **Templates** - Template/snippet management
   - Needs: Template CRUD
   - API Calls: getTemplates(), createTemplate(), updateTemplate()

8. **JudgingCritique** - Judging interface
   - Needs: Corps evaluation, scoring
   - API Calls: getJudgingData(), submitScore()

9. **EvolutionTalentPool** - Talent pool management
   - Needs: Performer auditions, draft picking
   - API Calls: getAuditionPool(), pickPerformer()

10. **Seance** - Historical seance data
    - Needs: Seance history, thread data
    - API Calls: getSeanceHistory(), getThread()

## Blocker Analysis

### Missing v1 Endpoints (Must Create First)
1. **Shows API**
   - GET /api/v1/shows (list shows with filters)
   - POST /api/v1/shows (create show)
   - PUT /api/v1/shows/{id} (update show)
   - DELETE /api/v1/shows/{id} (delete show)
   - GET /api/v1/shows/{id}/overview (detailed show info)

2. **Agents Overview API**
   - GET /api/v1/agents-overview — Currently exists in legacy, should move to v1

3. **System Health API**
   - GET /api/v1/system/health — Need to verify exists in v1

4. **Performers API**
   - GET /api/v1/performers (list with pagination)
   - POST /api/v1/performers/{id}/audition (audition performer)
   - POST /api/v1/performers/{id}/assign (assign to corps)

5. **Templates API**
   - GET /api/v1/templates
   - POST /api/v1/templates
   - PUT/DELETE endpoints

6. **Work Logs API**
   - GET /api/v1/work-logs (with limit, corps_id filter)

## Implementation Strategy

### Phase 1: Create Missing v1 Endpoints (Backend)
1. Extract shows endpoints from legacy to v1
2. Move agents-overview from legacy to v1
3. Add performers endpoints with audition/assignment logic
4. Add templates CRUD endpoints
5. Expose work-logs endpoint with filtering

### Phase 2: Migrate Frontend (Page by Page)
1. Update each page to use v1.ts types and endpoints
2. Add proper error handling
3. Update TypeScript types to match v1 responses
4. Test with actual v1 API

### Phase 3: Deprecate Legacy API (Optional)
1. Once all pages migrated, consider deprecating api.ts
2. Keep legacy routes in backend for backward compatibility

## Effort Estimate
- Phase 1 (Backend): ~4-6 hrs (endpoint creation + testing)
- Phase 2 (Frontend): ~8-10 hrs (careful per-page migration)
- Phase 3 (Cleanup): ~1-2 hrs (deprecation + testing)

## Current Status
- ✅ Scoreboards & metrics pages (PerformanceExplorer, ScoreboardsPage) — using v1
- ✅ Corps pages (CorpsList, CorpsDetailV2) — using v1
- ❌ 9 main pages still on legacy api.ts
- ❌ v1 endpoints for shows, performers, templates not yet created
