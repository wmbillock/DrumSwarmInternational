# DCI Swarm — Domain Glossary (Ubiquitous Language)

This document defines the domain model for the DCI Swarm agent orchestration engine, rooted in the structure and operations of a Drum Corps International drum and bugle corps, circa late 1990s–early 2000s.

---

## The Activity

**Drum and Bugle Corps**: A pageantry ensemble descended from military signalling corps. A marching music ensemble composed of brass, percussion, and color guard that learns, polishes, and presents a competitive field show.

**Drum Corps International (DCI)**: The governing organization for all drum and bugle corps competitions and organizations. Evaluates new corps before they may compete, and may remove corps for safety violations.

**Show**: The 12-minute field performance that is the corps' product. A cohesive themed presentation combining music, drill, and visual performance. Composed of 2–5 **movements**, each an independent but related piece of music.

**Movement**: A distinct section of the show — an independent but related piece of music. Movements give the show its narrative arc and structure.

**Props**: Equipment placed on the field during a show to produce a specific visual impact. Can range from small (a tree) to large (a series of slides). Part of the show design.

**Tour**: The summer competition season (~80 days) of continuous travel, rehearsal, and performance. The corps refines and polishes the show throughout tour. Culminates in **Finals Week** — quarterfinals, semifinals, and finals.

**Competition**: An event where multiple named corps perform and are scored against each other. Each corps performs its show and receives a composite score. Rankings drive competitive fervor and performer pride.

**Named Corps**: A specific drum and bugle corps organization with its own identity, membership, staff, and show (e.g., the Cavaliers, Blue Devils, Phantom Regiment). Each named corps is an independent orchestration — a competition is an orchestration of orchestrations, with each corps ranked against every other corps.

---

## The Field & Drill

**Field**: A football field — the performance surface.

**Drill**: The visual component of the show — all forms and movement that performers execute on the field. Designed by the drill writer.

**Set**: A specific formation at a point in time. Each set defines where every performer must be at that moment.

**Form**: The shape created by all performers' segments for a single set.

**Segment**: A performer's exact position for a given set. Every performer has the same number of segments (one per set). Their complete list of segments defines their path through the show.

---

## Performers

**Performer**: A member who takes a performance role on the field. Subject to DCI age restrictions (max 21).

### Performer Hierarchy (strict)

1. **Drum Major** — Senior leadership performer. Liaison between staff and performers. During performance: the **visual tempo source** (conducts from podium). During rehearsal: conducts alongside an electronic metronome.
2. **Caption Lead** — Leadership performer for a caption. Supplements the drum major's communication within their section.
   - **Horn Sergeant** (brass)
   - **Center Snare** (percussion) — During performance, the battery (led by center snare) is the **auditory tempo source**.
   - **Color Guard Captain** (color guard)
3. **Section Leader** — Leader for a specific instrument or guard technique. First point of contact when a performer is stuck.
4. **Section Performer** — Individual contributor.

---

## Captions

A **caption** is a functional grouping of performers by discipline. Most on-field performers belong to **two captions**: their primary caption and visual (see Visual Caption Head below).

### Brass

All horn players. Led by the horn sergeant.

| Instrument | Analog | Role |
|---|---|---|
| Soprano | Trumpet | Melody, lead voice |
| Mellophone | French Horn | Harmony, countermelody |
| Baritone | Baritone horn | Mid-voice, harmonic foundation |
| Euphonium | Euphonium | Optional supplement/replacement for baritone; rounder, more blendable tone |
| Contrabass | Tuba | Bass voice, foundation |

### Percussion

All percussion. Led by the center snare. Split into two physically distinct groups under a single percussion caption head.

**Battery** (on-field marching percussion):
- Snare drums (led by center snare)
- Tenor drums (aka quads/quints depending on tom count)
- Bass drums (up to 6, graduated sizes)
- Cymbal line (marching crash cymbals, optional)

**Front Ensemble / Pit** (stationary, at front sideline):
- Keyboard: xylophones, vibraphones, marimbas
- Auxiliary: floor toms, concert bass drums, concert snares, cymbals, gongs, tam-tams
- Effects: ratchets, windchimes, and anything the show design requires
- Drum set (optional)
- Single section leader for the entire front ensemble

The pit is physically separated from the field during performance, creating unique coordination challenges — limited visibility of the drum major, heavier reliance on auditory cues from the battery. The front ensemble does not typically have a visual component.

### Color Guard

Visual performers using equipment and movement. Composed of 1–4 techniques: flags, rifles, sabres, and dance. Techniques may be assigned to specialists or performed by all guard members. Led by the color guard captain.

---

## Staff

### Administrative

**Executive Director**: Head of the organization. Owns the show concept and the entire corps operation. Approves the design created by the program coordinator, identifies gaps, and requests clarification from the user (the human operator) when needed. The ultimate decider — does not create the design, but approves, questions, and steers it.

**Board of Directors**: Governing body for the corps entity.

### Instructional — Design

Design staff create the show's content. They work closely with their respective caption heads but do not typically interact directly with performers.

**Program Coordinator**: Responsible for delivering the creative product. Manages all design staff and resolves conflicts between them. Drives full ensemble rehearsal tempo and targets. Reports to the executive director for design approval and escalates questions they cannot answer. Owns rehearsal and implementation; the executive director owns concept and approval.

**Drill Writer**: Designs all drill (formations, transitions, staging). Delivers to the visual caption head. Rarely interacts directly with membership.

**Music Writer / Arranger**: Selects and arranges music. Delivers to brass and percussion caption heads.

**Choreographer**: Designs the color guard's dance and visual movements. Delivers to the color guard caption head.

**Design Handoff** — strict chain: Design Staff → Caption Head → Techs → Performers. No skipping levels.

### Instructional — Teaching

Teaching staff deliver the design to performers and refine execution to competition standards.

**Caption Head**: Senior instructor for a caption. Leads basics (fundamentals) and sectional rehearsal. Resolves cross-caption conflicts with other caption heads. Works closely with the program coordinator.

| Caption Head | Covers |
|---|---|
| Brass Caption Head | All horn parts |
| Percussion Caption Head | Battery and front ensemble |
| Color Guard Caption Head | All guard roles and techniques |
| Visual Caption Head | Cross-cutting (see below) |

**The Visual Caption Head** is unique — no dedicated performers. Responsible for how every on-field performer marches, moves, and presents. This is a cross-cutting concern spanning brass, battery, and color guard. The front ensemble is excluded from visual caption oversight.

**Tech**: Assistant instructor under a caption head. Handles detail work while the caption head focuses broadly. Spawned per instrument or category. Visual caption head has only visual techs; other captions may have a tech per instrument type or guard technique.

### Logistical

**Convoy**: The fleet that transports the corps — member buses, equipment truck, food truck (full kitchen, three meals plus post-show snack), staff bus, and utility vehicles (e.g., golf carts for hauling pit equipment). Each vehicle has a dedicated driver.

**Housing Site**: Typically a school. Performers sleep on gym floors; staff in classrooms.

**Crews**: Performers organized into groups for operational maintenance duties (garbage, bus loading, scaffolding construction, field lining, etc.) — additional duty on top of their performance role.

---

## Rehearsal & Performance

### Key Rehearsal Concepts

**Basics**: Fundamental technique practice isolated from show context. Focuses on *how* to do things correctly — marching technique, playing fundamentals, equipment work. Caption heads lead, techs support.

**Sectionals (Caption Sectionals)**: Rehearsal where a single caption works independently on their own material. The caption head leads their section without the other captions present.

**Full Ensemble**: Rehearsal with all captions together. The program coordinator drives the session with caption heads contributing. This is where integration across captions happens.

**Run-Through**: A complete, uninterrupted performance of the show in rehearsal conditions. Used to assess the show holistically and build stamina.

**Warm-up**: Pre-performance preparation. Each caption warms up separately — visual warm-up (marching), brass warm-up (playing), color guard warm-up (stretching and equipment). Brings performers to performance readiness.

**GE (General Effect)**: The artistic and emotional impact of a performance. Scored separately from technique. A show can have high GE (entertaining, moving, creative) but still lose on technique. Both are judged, but precision is the primary differentiator.

### Daily Structure (on tour)

1. Wake / Breakfast / Ablutions
2. Stretch and Calisthenics
3. **Visual Basics** — Fundamental marching technique, isolated from show context. Caption heads lead, techs support.
4. **Visual Rehearsal** — Working drill with the full corps.
5. Lunch
6. **Caption Sectionals** — Captions rehearse separately. Each caption head leads their section.
7. **Full Ensemble Rehearsal** — All captions together. Program coordinator drives the session with caption heads contributing.
8. **Full Show Run-Through**
9. Dinner / Uniform Change / Travel to Show Site
10. **Warm-ups** — Visual, brass, and color guard warm up separately.
11. **Performance**
12. **Post-Show Feedback** — Immediate, from caption heads to performers.
13. **Awards** — Scores announced. Highest composite score after penalties wins.
14. Load into convoy / Travel to next housing site.

### Correction Escalation

When a performer is stuck: **Section Leader → Tech → Caption Head**

Cross-caption: minor issues are flagged to the appropriate tech or caption head. Major issues may be corrected immediately by whoever sees them.

---

## Adjudication & Scoring

**Judges** work for DCI and are impartial. Each judge is assigned a specific caption for a competition. All operate under a **Head Judge**.

**Rubric**: 5-box framework. Box 1 (bad) through Box 5 (excellent). "Box 5" is cultural shorthand for excellence.

**Score**: Composite 0–100, derived from weighted caption scores.

| Judge Caption | Focus |
|---|---|
| Visual Technique | Precision of drill and marching |
| Visual General Effect | Artistic impact of the visual program |
| Brass Technique | Precision of brass performance |
| Brass General Effect | Artistic impact of the brass program |
| Percussion Technique | Precision of percussion performance |
| Percussion General Effect | Artistic impact of the percussion program |
| Color Guard Technique | Precision of guard work |
| Color Guard General Effect | Artistic impact of the guard program |
| Overall Technique | Aggregate technical achievement |
| Overall General Effect | Aggregate artistic impact |

**Penalties**: Deductions applied for rules infractions, generally assessed at one-tenth of a point per infraction. Examples:
- Show over-time (1 point per minute; may lead to disqualification)
- Performer left the bounds of the performance field
- Performer interrupted another corps' performance
- Use of unapproved instruments (e.g., woodwinds)
- Any other rule violation DCI seeks to enforce at the macro level

Penalties are a system-level enforcement mechanism — punishing non-adherence to the governing rules.

**Precision wins.** A show can be wildly entertaining (high GE) but lose to a more precise corps. Precision and accuracy are the primary differentiators at the championship level.

---

## Communication Patterns

| From | To | Mechanism | Context |
|---|---|---|---|
| Executive Director | Program Coordinator | Direct | Concept approval, gap identification, steering |
| Program Coordinator | Design Staff | Direct | Creative direction, conflict resolution |
| Program Coordinator | Caption Heads | Direct | Rehearsal direction, vision alignment |
| Design Staff | Caption Heads | Direct handoff | New material delivery |
| Caption Head | Techs | Direct | Teaching delegation, detail work |
| Techs | Performers | Direct | Instruction, correction |
| Drum Major | All performers | Visual conducting | Tempo (performance + rehearsal) |
| Battery | All performers | Auditory | Tempo (performance only) |
| Section Leader | Section Performers | Direct | Day-to-day, first-line correction |
| Cross-caption | Flag/escalate | Verbal | Minor: flag to appropriate staff. Major: correct immediately. |

---

## Key Domain Principles

1. **Strict hierarchy**: Communication and authority flow through defined channels.
2. **Design and execution are separate concerns**: Designers create, caption heads deliver, performers execute.
3. **Separation of concept and implementation**: Executive director owns concept and approval; program coordinator owns creative output and delivery.
4. **Strict material handoff chain**: Design → Caption Head → Techs → Performers. No skipping levels.
5. **Escalation before intervention**: Section leaders try first, then techs, then caption heads.
6. **Cross-caption awareness with lane discipline**: Flag problems outside your caption rather than fix them (unless urgent).
7. **Dual tempo sources**: Visual (drum major) and auditory (battery) provide redundant coordination during performance.
8. **Visual is a cross-cutting concern**: Most on-field performers belong to two captions — their primary and visual.
9. **Precision over entertainment**: The scoring system rewards accuracy and technique above artistic ambition.
10. **Continuous refinement**: The same show is polished over 80 days through iteration, not redesign.
11. **Physical separation creates coordination challenges**: The pit's isolation requires different communication patterns.
12. **Performers carry operational duties**: Crews handle logistics tasks on top of performance roles.
