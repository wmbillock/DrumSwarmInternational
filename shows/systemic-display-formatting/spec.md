✅ **Spec Updated Successfully**

I've updated `shows/systemic-display-formatting/spec.md` with a complete design specification that incorporates the design conversation. Key highlights:

**Decisions Made:**
- **Fallback Strategy**: Unknown/unmapped values return input as-is with console warning (graceful degradation, forward-compatible)
- **Single centralized utility** at `frontend/src/utils/formatters.ts`
- **Seven target pages** for comprehensive coverage
- **Field Commander Brutalism aesthetic** with font hierarchy (JetBrains Mono for technical, IBM Plex Sans for body)

**Deliverables:**
1. Five formatter functions (formatStatus, formatRole, formatCaption, slugToTitle, formatMode)
2. Updates to all seven pages: CommandCenter, CorpsDetailV2, CompetitionLive, Scoreboards, SeasonWorkshop, SystemHealth, DesignRoom
3. Comprehensive swarm prompt synthesizing all requirements

**Swarm Prompt** is now actionable and includes:
- Clear function signatures and behavior
- Specific page targets
- Error handling approach (graceful fallback)
- Design aesthetic requirements
- Verification checklist for zero-leakage of raw values

The spec is ready for swarm implementation. Once approved, this will standardize display formatting across the entire frontend and eliminate scattered formatting logic.