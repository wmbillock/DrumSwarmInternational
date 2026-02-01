<!-- tags: admin -->

**[user]** Create a shared formatters.ts utility at frontend/src/utils/formatters.ts with these functions: formatStatus(status: string) converts snake_case status values like on_tour, winter_camps, ready_for_contest to Title Case with spaces. formatRole(role: string) converts role slugs like music_writer, drill_writer, percussion_caption_head to readable names. formatCaption(caption: string) converts caption identifiers to display names. slugToTitle(slug: string) converts URL slugs to readable titles. formatMode(mode: string) converts rehearsal mode values to display names. Apply these formatters across ALL page components: CommandCenter, CorpsDetailV2, CompetitionLive, Scoreboards, SeasonWorkshop, SystemHealth, DesignRoom. Every place that currently displays raw snake_case or slug values should use the appropriate formatter. Use the existing v1.ts API client. Follow Field Commander Brutalism design aesthetic with JetBrains Mono and IBM Plex Sans fonts.

<!-- tags: admin -->
**[program_coordinator]** Looking at your codebase context and the request, I can see this is straightforward implementation work with clear requirements. Let me ask one clarifying question:

**Should formatters handle fallback/unknown values gracefully (e.g., return the input as-is with a console warning), or should they throw errors for unmapped values?** This matters for robustness—if a new status gets added to the backend but frontend hasn't updated, do we display it as best we can or fail loudly?

Once I know that, I'll sketch the design.
