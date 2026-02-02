<!-- tags: admin -->

**[user]** Create a shared formatters.ts utility at frontend/src/utils/formatters.ts with these functions: formatStatus(status: string) converts snake_case status values like on_tour, winter_camps, ready_for_contest to Title Case with spaces. formatRole(role: string) converts role slugs like music_writer, drill_writer, percussion_caption_head to readable names. formatCaption(caption: string) converts caption identifiers to display names. slugToTitle(slug: string) converts URL slugs to readable titles. formatMode(mode: string) converts rehearsal mode values to display names. Apply these formatters across ALL page components: CommandCenter, CorpsDetailV2, CompetitionLive, Scoreboards, SeasonWorkshop, SystemHealth, DesignRoom. Every place that currently displays raw snake_case or slug values should use the appropriate formatter. Use the existing v1.ts API client. Follow Field Commander Brutalism design aesthetic with JetBrains Mono and IBM Plex Sans fonts.

<!-- tags: admin -->
**[program_coordinator]** Looking at your codebase context and the request, I can see this is straightforward implementation work with clear requirements. Let me ask one clarifying question:

**Should formatters handle fallback/unknown values gracefully (e.g., return the input as-is with a console warning), or should they throw errors for unmapped values?** This matters for robustness—if a new status gets added to the backend but frontend hasn't updated, do we display it as best we can or fail loudly?

Once I know that, I'll sketch the design.
<!-- tags: ge, guard, visual -->

**[user]** Required Fixes (6) Show Concept: Missing required section: ## Show Concept Musical Design: Missing required section: ## Musical Design Visual Design: Missing required section: ## Visual Design Guard Design: Missing required section: ## Guard Design General Effect: Missing required section: ## General Effect Deliverables: Missing required section: ## Deliverables

<!-- tags: ge, guard, visual -->
**[program_coordinator]** The six missing sections are DCI creative design sections that belong in a **show brief**, not the spec. **Brief update ready**: Create `shows/systemic-display-formatting/brief.md` with all six required sections (Show Concept, Musical Design, Visual Design, Guard Design, General Effect, Deliverables), or tell me which show the Director is asking about if this isn't the one. **If systemic-display-formatting, what specific creative direction should each section capture?** (e.g., is this a brutalist symphony showing format transformation, or a different creative theme?)

<!-- tags: ge, guard, visual -->
**[choreographer]** I'm reading the spec you've got. Those six sections are missing from the current show spec — they're the bones of what a design actually needs, not just the implementation details. What does "systemic-display-formatting" need? Are we talking about a visual design show (like, how the guard moves through formations), or is this purely about standardizing how data displays across pages?

<!-- tags: ge, guard, visual -->
**[drill_writer]** I see what's happening — the spec's missing the core design sections that the swarm actually needs to build from. Right now we've got a solid *utility* spec (functions, pages, aesthetics), but we're not telling the swarm *why* this formatting matters or *where* it fits into the show's creative intent.

Let me ask you straight: **What's the creative thesis here?** Is this show about *clarity under pressure* (field commander brutalism = legible data in chaos)? Or is it *process visualization* (showing how the system thinks)? That answer changes everything about how we frame the Guard Design, Musical Design, and what the "show concept" even is.

Once I know that, I can fill in those six sections so the swarm knows what they're building *for*, not just *what* they're building.
