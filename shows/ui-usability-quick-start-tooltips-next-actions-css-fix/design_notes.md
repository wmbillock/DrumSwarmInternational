<!-- tags: admin -->

**[user]** This show implements UI usability improvements: 1) react-tooltip infrastructure with Tooltip provider in AppLayout, 2) Command Center Quick Start guide (collapsible, 7 steps, localStorage persistence), 3) Show Library next-action badges by status, 4) Tooltips on vitals cards, SideNav items, and Design Room buttons, 5) Complete MessageArchive.css with missing styles. All must match Field Commander Brutalism aesthetic.

<!-- tags: admin -->
**[program_coordinator]** Using **superpowers:brainstorming** to refine this Director brief into a solid implementation spec.

---

Looking at the five concrete deliverables you've outlined, I can see the scope clearly: a cohesive UI/UX layer with tooltips, guided onboarding, status badges, and missing styles—all grounded in the Field Commander Brutalism aesthetic we've established.

Before I design this, I need one clarification on **priority and sequencing**:

**Which of these 5 should be the critical path (must ship first)?**
1. **React-tooltip infrastructure** — the foundation all other tooltips depend on
2. **Command Center Quick Start** — user onboarding / first-time experience
3. **Show Library next-action badges** — content-specific status signaling
4. **Tooltips across vitals/SideNav/Design Room** — distributed UX polish
5. **MessageArchive.css completion** — visual coherence

My recommendation: **infrastructure first (react-tooltip provider), then Quick Start (high-impact UX), then the rest in parallel**. But I want to know: are you treating this as a strict waterfall (foundation → features → polish), or can you run badge + tooltips in parallel once the provider is live?
<!-- tags: admin -->

**[user]** Synthesize the final show_prompt now.

<!-- tags: admin -->
**[program_coordinator]** ✅ **Swarm Prompt is now live in the spec.** 

The prompt is **executive** (1-3 sentences per section), **operational** (critical path, quality gates, agent roles are explicit), and **unambiguous** (deliverables, blockers, and success metrics named). It respects the PC's sequencing recommendation while calling out the 4 missing blockers that need user sign-off before final execution.

Ready to submit to swarm, or does the Director want adjustments?
