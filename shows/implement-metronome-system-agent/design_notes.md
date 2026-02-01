<!-- tags: admin -->
**[executive_director]** The metronome is a standalone system-level agent run on a cron (every 5 minutes). Its purpose is to keep the swarm marching forward by issuing wake-up commands to all corps.

<!-- tags: admin -->
**[executive_director]** On each metronome tick: wake up, immediately issue ten-hut to every corps, and if needed, resume-hut. Then gather corps status across the swarm.

<!-- tags: admin -->
**[executive_director]** Only wake instructional staff, admin, and logistics agents directly. Let those agents wake performers as necessary — do not wake performers directly from the metronome.
<!-- tags: questions -->

**[user]** How are we doing?

<!-- tags: questions -->
**[program_coordinator]** Great question, Director. Let me take stock of where we are on the metronome system spec.

**What we've got locked in:**
- Purpose & cadence (standalone agent, runs every 5 minutes)
- Core behavior (wake up → ten-hut all corps → resume-hut if needed → gather status)
- Hierarchy rule (wake instructional/admin/logistics only; let them cascade to performers)

**What's still open:**
We haven't filled in the seven required spec sections yet—**Show Concept, Musical Design, Visual Design, Guard Design, General Effect, Deliverables, and Evaluation Rubric.** For a metronome system, some of these will be unconventional (it's not a traditional visual show), but we need to nail down what success looks like.

**Quick clarifying question:** Should we treat the metronome spec as a "system maintenance routine" (where the rubric measures reliability, response time, agent health recovery) or do you want it positioned as a "conceptual show" (with thematic messaging about swarm synchronization, cadence, and collective discipline)?

Let me get the **Music Arranger and Drill Designer** in the room to help us shape this—especially around what "General Effect" means for a background system.
<!-- tags: admin -->

**[user]** System maintenance routine.

<!-- tags: admin -->
**[program_coordinator]** Got it, Director—**system maintenance routine** it is. That locks our lens: we're measuring reliability, uptime, response times, and agent health recovery, not thematic storytelling.

Quick follow-up: **Should the metronome also log its own health metrics** (e.g., "last tick time," "corps response rates," "any agents in distress"), or keep it purely operational—just fire the wake-up calls and let the corps report back?

Let me bring in the **Systems Engineer and Database Architect** to help us spec out the Deliverables (what gets logged, where, how it's monitored) and Evaluation Rubric (what "success" looks like for a 5-minute cycle).
