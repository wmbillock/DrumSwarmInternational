```markdown
show_slug: improve-the-corps-list-page
version: 8
created_at: "2026-02-14T19:56:13.455971+00:00"
updated_at: "2026-02-14T22:15:00.000000+00:00"
approved_at: "2026-02-14T22:15:00.000000+00:00"
approved_by: user
roles_consulted:
  - program_coordinator
  - drill_writer
  - choreographer
  - music_writer

# Improve the Corps List Page

## Show Concept
The redesign of the Corps List Page enhances user engagement through visually differentiated corps cards that reflect the individual themes and identities of each corps. Each card serves as the single standardized component across the DrumSwarmInternational UI for all corps information display, eliminating duplication and ensuring consistency. The cards prominently display vital information—logo, mascot, name, executive director, and current state—allowing users to quickly recognize and connect with each corps. Corps philosophy and definitions inform the personality and interaction flavors for the swarm but are not displayed on the card itself. The component architecture prioritizes maximum reusability to minimize code duplication wherever corps information appears throughout the application.

## Musical Design
A moderately fast 4/4 tempo with brass-heavy fanfares introduces each corps card transition. Each corps receives a unique melodic motif derived from its definition and thematic identity, creating dynamic engagement between cards. Musical transitions between corps highlights reinforce the individual character of each ensemble while maintaining cohesive flow throughout the page. The fanfare format establishes immediate recognition and emotional connection as users encounter each corps presentation.

## Visual Design
Create dynamic, reusable corps info cards with unique themed backgrounds reflecting each corps' identity and visual brand. Each card prominently features:
- Corps logo
- Corps mascot
- Corps name
- Executive director
- Current state

The background styling will be customized per corps to enhance visual recognition and thematic connection. All components must be designed for maximum reusability across the entire DrumSwarmInternational UI to minimize code duplication and ensure visual consistency wherever corps information appears. Card structure and layout remain consistent across all instances while allowing customization of background themes and visual branding elements.

## Guard Design
Incorporate silk fans and sabres in formation shifts that symbolize the dynamic nature of each corps and the collaborative essence of the organization. Movement patterns tell stories of unity and adaptability, with each formation transition reinforcing the visual theme of the corps card being presented. Silk fans establish connecting flow between cards during transitions, creating visual continuity as users navigate between corps. Formation shifts communicate themes of collaboration and dynamic engagement through deliberate positioning and sustained visual flow.

## General Effect
Staggered card cascade entrance with slight rotation creates visual momentum as the page loads. Each corps logo leads formation diagonally across the viewport as cards enter, establishing immediate visual hierarchy and engagement. Silk fans establish connecting flow between successive cards, maintaining visual coherence throughout the sequence. The recognition moment occurs when each card settles into its final position, providing emotional payoff and reinforcing corps identity. This settling moment serves as the climactic beat before the next corps introduction. Overall visual flow prioritizes smooth transitions between corps while maintaining emotional engagement through deliberate pacing, staggered timing, and formation choreography that celebrates individual corps identity within a unified design system.

## Constraints
- The corps info card component must be the single, standardized corps display element used throughout the entire UI.
- All components must be reusable to ensure consistency and reduce code duplication.
- Card designs must adhere to existing UI framework and design system guidelines.
- Corps philosophy and thematic definitions drive interaction personality but should not appear on the card display.
- Background customization per corps must maintain consistent card structure and layout.
- Cascade entrance and settling animations must work across all responsive breakpoints.
- Silk fan choreography transitions must maintain visual coherence between card sequences.
- No redundant corps display code may exist elsewhere in the application.

## Deliverables
- Redesigned, reusable corps info card component with dynamic themed backgrounds.
- Implementation of logo, mascot, name, executive director, and state information display.
- Component API documentation for consistent implementation across the UI.
- Design tokens and style guide for corps card customization and background theming.
- Integration of unique musical motifs for corps card introductions based on corps definitions (4/4 tempo, brass-heavy fanfare format).
- Guard choreography featuring silk fans and sabres in formation transitions emphasizing unity and adaptability.
- Staggered cascade entrance sequence with diagonal logo-led formations and settling recognition moments.
- Silk fan transition choreography establishing visual flow between consecutive corps cards.
- Comprehensive component documentation for UI-wide reuse and implementation standards.
- Design system specifications ensuring visual consistency across all corps card instances.
- Migration plan for replacing all existing corps display instances with the new component.
- Verification that zero redundant corps display code exists elsewhere in the application.

## Swarm Prompt

### Objective
Develop a single, reusable corps info card component for the DrumSwarmInternational UI that serves as the standardized corps information display throughout the entire application. Each card will display logo, mascot, name, executive director, and state with unique themed backgrounds reflecting individual corps identity. Implement a staggered cascade entrance with diagonal logo-led formations, silk fan transitions, and settling recognition moments. Pair visual elements with unique musical motifs (moderately fast 4/4 tempo, brass-heavy fanfare) derived from corps definitions and guard choreography emphasizing formation shifts, unity, and adaptability.

### Deliverables
- Single reusable corps info card component with customizable themed backgrounds
- Dynamic background styling system reflecting each corps' visual brand
- Component API documentation for consistent implementation across UI locations
- Design tokens and style guide for corps card customization
- Unique melodic motif library keyed to corps definitions for card introductions (moderately fast 4/4 tempo, brass-heavy fanfare format)
- Guard choreography sequences (silk fans and sabres) for corps theme reinforcement, emphasizing formation shifts that communicate unity and adaptability
- Cascade entrance animation system with staggered timing, diagonal logo-led formations, and settling recognition moments with emotional payoff
- Silk fan transition choreography establishing visual flow between consecutive corps cards
- Migration plan for replacing all existing corps display instances with the new component
- Verification documentation confirming zero redundant corps display code elsewhere in the application

### Constraints
- Component must be the only corps information display element used throughout the UI
- Backgrounds must be customizable per corps while maintaining consistent card structure and layout
- Philosophy and thematic information must not appear on the card—reserved for swarm personality and interaction flavors
- All styling must integrate with existing UI framework and design system
- Code must minimize duplication through proper component abstraction and composition
- Cascade entrance and settling animations must work across all responsive breakpoints
- Silk fan choreography transitions must maintain visual coherence between card sequences
- Card designs must support logo, mascot, name, executive director, and state information prominently
- No redundant corps display implementations may exist elsewhere in the application

### Acceptance Criteria
- Corps info card visually reflects each corps' unique identity and brand with themed backgrounds
- All required information (logo, mascot, name, executive director, state) is clearly displayed and easily scannable
- Component successfully reused in at least three different UI locations without modification to core structure
- Component API is well-documented with clear examples for implementation
- Musical motifs correspond to and enhance each corps' thematic definition, following 4/4 tempo and brass-heavy fanfare conventions
- Guard choreography movements effectively communicate unity and adaptability through silk fan and sabre formation shifts
- Cascade entrance animation creates visual momentum with staggered timing and diagonal logo-led formations
- Recognition moment (card settling) provides clear emotional payoff and reinforces corps identity
- Silk fan transitions establish visual flow between consecutive corps cards
- Design documentation provides clear guidelines for adding new corps cards with consistent theming and animation timing
- All responsive breakpoints support cascade entrance and settling animations without performance degradation
- Migration audit confirms zero redundant corps display code exists elsewhere in the application
```