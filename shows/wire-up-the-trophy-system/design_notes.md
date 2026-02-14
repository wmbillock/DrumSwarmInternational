
<!-- tags: admin -->
**[program_coordinator]** Welcome, Director! I'm your Program Coordinator for **"Wire up the trophy system."** 

What's your vision for how we score and award the corps this season?
<!-- tags: admin -->

**[user]** So we had a trophy page at one point but it disappeared. So I want to implement trophy mechanisms that are awarded to corps. We already have some code for this, so step 1 is figuring out what we still need. Step 2 is making the trophies actually award. Step 3 is showing the trophies that have been awarded in the UI, in an appropriate section.

<!-- tags: admin -->
**[program_coordinator]** **Step 1 complete.** Found robust trophy infrastructure: DB model âœ“, 5 tiers (bronzeâ€“diamond), 12 categories, achievement catalog + detector, 2 API endpoints (`/awards`, `/awards/summary`), and frontend TrophyShowcase UI âœ“.

**Key gap:** Trophies aren't being awardedâ€”achievement check endpoints exist but aren't wired into agent sessions. Where should they trigger?

<!-- tags: admin -->
**[judge]** Open issues: Brief — Musical Design: Unfilled placeholder: \bTBD\b; Brief — Guard Design: Unfilled placeholder: \bTBD\b
<!-- tags: admin -->

**[user]** ok I actually found the page-  it's under "Swarm Health", which makes no sense to me. I think we need a "Results and Rankings" tab where we can display awards and rankings between corps

<!-- tags: admin -->
**[program_coordinator]** Understood. Moving trophy showcase from "Swarm Health" to new "Results and Rankings" tab. Confirm: Should this tab show trophies + competition standings together, or separate sections?

<!-- tags: admin -->
**[judge]** Open issues: Brief — Musical Design: Unfilled placeholder: \bTBD\b; Brief — Guard Design: Unfilled placeholder: \bTBD\b
<!-- tags: admin -->

**[user]** Separate sections, like subtabs

<!-- tags: admin -->
**[program_coordinator]** Got it. Creating "Results and Rankings" tab with separate trophy and standings subtabs.

Next: Should trophies award **during rehearsals** (real-time feedback) or **after performances** (formal recognition)?

<!-- tags: admin -->
**[judge]** Open issues: Brief — Musical Design: Unfilled placeholder: \bTBD\b; Brief — Guard Design: Unfilled placeholder: \bTBD\b
<!-- tags: admin -->

**[user]** Some should be awarded during rehearsal, if exceptional events occur. Otherwise they're formally awarded after competitions, and then more significant awards are awarded after each finals.

<!-- tags: admin -->
**[program_coordinator]** Got it. **Trophy awarding logic:**
- **During rehearsal**: Trigger on exceptional events (real-time)
- **Post-competition**: Formal awards
- **Post-finals**: High-tier awards

**Next step**: Wire achievement detection into agent sessions + define "exceptional events" for rehearsal triggers?

<!-- tags: admin -->
**[judge]** Open issues: Brief — Musical Design: Unfilled placeholder: \bTBD\b; Brief — Guard Design: Unfilled placeholder: \bTBD\b
<!-- tags: admin -->

**[user]** Yep

<!-- tags: admin -->
**[program_coordinator]** **Next step:** I'll wire achievement detection into agent sessions and post-performance trophy awards. Start now?

<!-- tags: admin -->
**[judge]** Open issues: Brief — Musical Design: Unfilled placeholder: \bTBD\b; Brief — Guard Design: Unfilled placeholder: \bTBD\b
<!-- tags: admin -->

**[user]** Thanks, I've approved and published the show!

<!-- tags: admin -->
**[program_coordinator]** Perfect! **Starting implementation now.** Wiring achievement detection into agent sessions, then post-performance trophy awards. I'll handle the "Results and Rankings" tab migration next.

<!-- tags: admin -->
**[judge]** Open issues: Brief — Musical Design: Unfilled placeholder: \bTBD\b; Brief — Guard Design: Unfilled placeholder: \bTBD\b
