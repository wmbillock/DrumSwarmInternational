## Objective
Develop a single, reusable corps info card component for the DrumSwarmInternational UI that serves as the standardized corps information display throughout the entire application. Each card will display logo, mascot, name, executive director, and state with unique themed backgrounds reflecting individual corps identity. Implement a staggered cascade entrance with diagonal logo-led formations, silk fan transitions, and settling recognition moments. Pair visual elements with unique musical motifs (moderately fast 4/4 tempo, brass-heavy fanfare) derived from corps definitions and guard choreography emphasizing formation shifts, unity, and adaptability.

## Deliverables
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

## Constraints
- Component must be the only corps information display element used throughout the UI
- Backgrounds must be customizable per corps while maintaining consistent card structure and layout
- Philosophy and thematic information must not appear on the card—reserved for swarm personality and interaction flavors
- All styling must integrate with existing UI framework and design system
- Code must minimize duplication through proper component abstraction and composition
- Cascade entrance and settling animations must work across all responsive breakpoints
- Silk fan choreography transitions must maintain visual coherence between card sequences
- Card designs must support logo, mascot, name, executive director, and state information prominently
- No redundant corps display implementations may exist elsewhere in the application

## Acceptance Criteria
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