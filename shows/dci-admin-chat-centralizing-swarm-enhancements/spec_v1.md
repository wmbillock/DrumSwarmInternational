# DCI Admin Chat - Centralizing Swarm Enhancements

## Show Concept

A centralized administrative communication hub designed to streamline coordination between the Director (DCI Swarm Director), DSI admin, and corps representatives. This feature enables real-time discussion of swarm operations, collaborative troubleshooting, celebration of achievements, and data-driven scheduling decisions emerging from operational conversations. The chat room serves as the operational nerve center where high-level decisions about show scheduling are informed by live team input and swarm performance insights.

The Director (DCI Swarm Director) functions as the primary interlocutor, driving conversation by asking targeted questions of corps directors and other DCI agents, summarizing input, and clearly signaling when it's the user's turn to respond with prominent visual cues. The visual turn indicator makes it obvious whose turn it is to contribute, with design flexibility to adjust or dial back prominence as needed based on operational tempo. Corps representatives function as operational avatars of their respective executive directors, capable of coordinating decisions within the chat and reporting back to their organizations as appropriate.

All communication remains live with real-time notifications alerting targeted participants as messages are posted. Notifications respect participant presence status—only online participants receive immediate alerts; offline users see notifications upon reconnection. Participants access the static membership roster directly without authentication—the system recognizes fixed participants and displays their presence status (online/offline) in real-time. All participants display as available operational avatars ready to coordinate, with presence status reflecting actual connectivity only. Chat discussions inform operational decision-making but do not directly affect executing sessions until a formal task is created, ensuring separation between deliberation and execution. Messages cannot be edited or deleted once posted, maintaining operational record integrity and live transparency.

## Musical Design

TBD — awaiting design input

## Visual Design

Standard Discord/IRC-style layout with three primary components:

- **Message History Pane**: Chronological display of all messages with speaker attribution and timestamp. Font styling enabled for text formatting (bold, italic, underline, color) with full visual rendering in history.
- **Input Field**: Text composition area with font styling controls (bold, italic, underline, color) supporting formatted message creation.
- **Participant Roster Sidebar**: Real-time display of all static participants with current online/offline status indicator, participant role, and availability status (all display as available operational avatars).
- **Turn Indicator**: Prominent visual cue clearly highlighting whose turn it is to respond, making participant expectations obvious. Displays as "Your turn" when user response is expected or "Awaiting [Participant Name]" when waiting for another participant. Design allows for adjustment or dial-back in prominence based on operational needs.

Message visibility follows role-based rules: Director receives full operational context across all messages; other participants see messages with role-appropriate data visibility applied at message content level.

Director's conversation management signals remain unambiguous: questions are clearly marked as Director inquiries requiring response, summaries are distinctly identified, and turn-taking cues are visually emphasized.

## Guard Design

TBD — awaiting design input

## General Effect

The admin chat room creates operational transparency and distributed decision-making capability across the swarm ecosystem. It serves as the nerve center for:

- **Swarm Operations Oversight**: Real-time monitoring and discussion of swarm behavior
- **Failure Investigation**: Collaborative root-cause analysis of system anomalies
- **Performance Celebration**: Recognition of successful operations and milestones
- **Show Scheduling**: Data-informed scheduling decisions derived from operational insights and team input
- **Directive Leadership**: Director drives primary conversation, asks targeted questions of corps directors and DCI agents, summarizes input, and signals user's turn clearly with prominent visual cues adjustable as needed
- **Role-Based Context**: Director maintains full operational visibility while other participants access role-appropriate data
- **Presence Awareness**: Real-time online/offline status display for all static participants reflects actual connectivity; all participants display as available operational avatars ready to coordinate
- **Avatar Coordination**: Corps representatives function as operational delegates capable of coordinating with their home organizations and reporting back as appropriate
- **Deliberation-to-Execution Separation**: Chat discussions enable collaborative planning without impacting active sessions until formal task creation occurs
- **Live Transparency**: Messages remain immutable upon posting; no editing or deletion affects operational record integrity
- **Standard Interface**: Familiar Discord/IRC-style layout with font styling reduces participant learning curve and enables rapid coordination
- **Turn-Taking Clarity**: Visual indicators make it obvious when user input is required, with prominent cues that can be adjusted as operational needs change
- **Participant Query Capability**: Representatives can access dependent data as operationally needed to inform discussions
- **Session Isolation**: Chat discussions remain isolated from executing operations; changes require explicit task creation to take effect
- **Presence-Aware Notifications**: Real-time alerts to targeted participants respect online/offline status; offline participants receive notifications upon reconnection
- **Notification Targeting**: Immediate alerts triggered by Director inquiries or message posting, targeted to relevant participants based on conversation flow
- **Live-Only Architecture**: Messages persist during active sessions only; no archival, export, or long-term storage beyond session lifetime

## Constraints

- **Participants**: Static membership list comprising Director (DCI Swarm Director), DSI admin, and one representative per corps (fixed roster, no open invitations or dynamic membership changes)
- **Access Model**: Static participant list accessed directly without authentication; system recognizes fixed participants; participants can query their dependents as needed
- **Purpose Scope**: Discussion limited to swarm operations, troubleshooting, celebrations, and show scheduling
- **Access Control**: Role-based data visibility; Director has full operational context visibility, other participants see role-appropriate data
- **Message History**: Live chat only — no scheduled archival, bulk export, or long-term storage beyond active session lifetime
- **Notifications**: Real-time alerts for Director questions and message activity upon posting (no batch intervals); alerts respect participant presence status (online participants receive immediate alerts; offline participants receive notifications upon reconnection); alerts may be targeted to specific participants based on conversation context
- **Presence Display**: Online/offline status shown for all static participants in real-time; all participants display as available operational avatars ready to coordinate; presence status reflects actual connectivity only
- **Session Impact**: Chat discussions do not affect executing sessions until a formal task is created
- **Corps Representatives**: Function as operational avatars of their respective executive directors; responsible for reporting decisions back to their home organizations as appropriate
- **Message Transparency**: Message editing and deletion disabled for live transparency and operational record integrity; messages immutable upon posting
- **Interface Standard**: Discord/IRC-style layout with font styling support (bold, italic, underline, color); no custom interface paradigms
- **Conversation Flow**: Director drives primary interlocution with corps directors and DCI agents, asks targeted questions, summarizes input, and clearly signals user's turn with prominent visual turn indicator; turn indicator design allows for adjustment or dial-back based on operational needs
- **Turn Indicator Prominence**: Visual turn cue clearly indicates whose responsibility it is to respond next; design allows for operational flexibility to adjust prominence as needed

## Deliverables

- Centralized chat room interface supporting group messaging (Director + DSI admin + 1 rep per corps) with Discord/IRC-style layout
- Static participant roster with real-time online/offline status display for each member
- Direct access to static participant list without authentication requirement; system recognizes fixed participants
- Role-based data visibility system: Director receives full operational context; other participants see context appropriate to their role
- Real-time notification system alerting targeted participants immediately upon new messages or Director conversation initiators; notifications respect participant presence status (online participants receive immediate alerts; offline participants receive notifications upon reconnection); no batching of alerts
- Chat interface displaying participant roles and current online/offline status for all static members in roster sidebar
- Message history pane with chronological message display, speaker attribution, and timestamps
- Message input field with font styling support (bold, italic, underline, color)
- Participant query capability enabling representatives to access dependent data as operationally needed
- Live message persistence during active sessions only; no long-term archival or export functionality
- Message transparency enforcement: editing and deletion disabled to maintain operational record integrity; messages immutable upon posting
- Integration points for swarm operational data and metrics referenced in conversations
- Real-time presence indicators reflecting actual connectivity status for all static members
- All participants display as available operational avatars ready to coordinate
- Prominent visual turn indicator system clearly highlighting whose turn it is to respond (displays as "Your turn" or "Awaiting [Participant Name]"), making it obvious when user input is expected; indicator design allows for adjustment or dial-back based on operational needs
- Director's conversation management signals (questions, summaries, turn-taking cues) prominently displayed and unambiguous
- Task creation workflow enabling chat discussion outcomes to transition into actionable operational changes
- Session isolation mechanism preventing chat discussions from impacting executing sessions until task creation

## Swarm Prompt

### Objective

Build a live-only centralized admin chat room with Discord/IRC-style interface enabling the Director (DCI Swarm Director as primary interlocutor), DSI admin, and one designated representative per corps to discuss swarm operations, investigate system failures, celebrate wins, and make scheduling decisions collaboratively. The Director drives conversation by asking targeted questions of corps directors and DCI agents, summarizing input, and clearly signaling when it's the user's turn to respond with prominent visual turn indicators that display as "Your turn" or "Awaiting [Participant Name]" and can be adjusted in prominence based on operational tempo. The Director maintains full operational visibility while other participants access role-appropriate data. Corps representatives function as operational avatars of their respective executive directors, empowered to coordinate decisions within chat and report back to their home organizations. Chat remains live-only with messages persisting only during active sessions; real-time notifications respect presence status (immediate alerts for online; notifications upon reconnection for offline); no message editing/deletion; no archival or export. Participants access static membership roster directly without authentication—system recognizes fixed participants and displays real-time online/offline status reflecting actual connectivity. All participants display as available operational avatars ready to coordinate. Participants can query dependents as needed for operational context. Chat discussions inform decision-making but do not affect executing sessions until formal task creation.

### Deliverables

- Chat interface with Discord/IRC-style layout: message history pane, input field with font styling support (bold, italic, underline, color), participant roster sidebar with role and real-time online/offline status display
- Prominent visual turn indicator clearly displaying "Your turn" when user response is needed or "Awaiting [Participant Name]" when waiting for other participants; indicator design supports adjustment or dial-back in prominence based on operational tempo
- Static participant roster management system (Director, DSI admin, one designated representative per corps; fixed membership with no dynamic changes)
- Direct-access static participant list without authentication requirement; system recognizes fixed participants upon entry
- Role-based data visibility layer: Director sees full operational context; other participants see role-appropriate operational data
- Presence-aware real-time notification system: alerts targeted participants immediately upon new message posting or Director conversation initiation for online participants; offline participants receive notifications upon reconnection (no batch intervals, no scheduled delivery)
- Message chronological display with speaker attribution, timestamp, and font styling options (bold, italic, underline, color) fully rendered in history
- Message transparency enforcement: no editing or deletion capability; all posted messages remain immutable for operational record integrity
- Message persistence during active session only (live chat, no scheduled export or long-term archival)
- Participant query capability enabling representatives to access dependent operational data on-demand
- Real-time online/offline presence indicators for all static members displayed in roster sidebar; presence reflects actual connectivity only
- All participants display as available operational avatars within presence display
- Integration hooks for swarm operational data referenced in conversations
- Avatar framework enabling corps representatives to function as operational delegates of their executive directors, coordinating decisions within chat and reporting back to home organizations as appropriate
- Director-led conversation flow management: Director asks targeted questions, summarizes responses, maintains lively discussion while making clear when user input is required
- Director question/summary signals prominently displayed and unambiguous within chat interface
- Task creation mechanism translating chat discussion outcomes into actionable operational changes; task structure mirrors chat workflow with trigger point, assigned participants, execution parameters, and status tracking
- Session isolation ensuring chat does not impact executing operations until task is formally created and applied

### Constraints

- Participant list is fixed and role-defined (Director, DSI admin, one rep per corps; no open membership or invitations)
- No authentication system required; static participant list accessed directly by recognized participants
- Discussion scope limited to: swarm operations, troubleshooting, celebrations, show scheduling
- Live chat only — no scheduled message history export, archival functionality, or data persistence beyond active session
- Real-time notifications only — alerts respect participant presence status; online participants receive immediate alerts; offline participants receive alerts upon reconnection; no batch notification intervals or notification scheduling
- Message editing and deletion disabled; all messages immutable upon posting
- Closed group — no public access or guest participation
- Role-based visibility: Director has full operational context; other roles see context appropriate to their function
- Online/offline status displayed for all static participants in real-time; presence reflects actual connectivity only
- All participants display as available; presence status reflects actual connectivity only
- Corps representatives function as operational avatars of their executive directors, responsible for reporting decisions to home organizations
- Chat discussions remain isolated from executing sessions; changes require explicit task creation to take effect
- Interface follows Discord/IRC standard layout paradigm with font styling support
- Participants can query dependent data as needed for operational context
- Director drives primary conversation with corps directors and DCI agents: asks targeted questions, summarizes input, clearly signals user's turn with prominent visual turn indicator that displays as "Your turn" or "Awaiting [Participant Name]"; indicator design allows for adjustment or dial-back based on operational tempo
- Real-time notifications targeted to specific participants based on conversation context and presence status
- Turn indicator must clearly communicate whose responsibility it is to respond next; adjustability allows for operational flexibility
- Task creation is the exclusive mechanism for transitioning chat discussion outcomes into active session impacts

### Acceptance Criteria

- Users access the static participant roster directly and join the chat as recognized fixed members without authentication
- Chat interface displays Discord/IRC-style layout with message history, input field, participant roster sidebar with roles and real-time online/offline status, and prominent turn indicator
- Turn indicator clearly displays "Your turn" when user response is expected or "Awaiting [Participant Name]" when awaiting other participants; prominence can be adjusted or dialed back as operational needs evolve
- Director receives full operational context; other participants receive role-appropriate data visibility at message level
- All online targeted participants receive immediate real-time notifications of Director questions or new messages upon posting; offline participants receive notifications upon reconnection
- Font styling (bold, italic, underline, color) is supported in message input and displays correctly in message history
- Posted messages cannot be edited or deleted; all messages remain immutable for operational transparency
- Messages display with speaker attribution and timestamp in chronological order
- Live messaging enables collaborative discussion of swarm operations and scheduling decisions
- Chat persists only during active session; no long-term archival or export capability
- Closed group membership restricts participation to Director, DSI admin, and one corps representative per team
- Participants can query dependent data as operationally needed
- Chat supports operational data discussion and decision-making workflow without external archival or export
- Real-time online/offline presence status accurately reflects actual participant connectivity and updates in roster
- All participants display as available operational avatars within presence display
- Corps representatives understand their role as operational avatars of their executive directors and coordinate decisions within the chat
- Director successfully drives conversation by asking targeted questions of corps directors and DCI agents, summarizing responses, and clearly signaling when user input is needed with prominent visual turn indicator
- Turn indicator prominently highlights whose turn it is to respond, making user expectations obvious; design clearly communicates responsibility for next response through "Your turn" or "Awaiting [Participant Name]" display; design can be adjusted or dialed back as operational needs change
- Director questions and summaries are visually distinct and unambiguous
- Executing sessions remain unaffected by chat discussions until a formal task is created and applied
- Task creation workflow allows deliberate transition from chat discussion to operational implementation; task structure includes trigger point, assigned participants, execution parameters, and status tracking
- Notification system respects presence status: online users receive immediate alerts; offline users see notifications upon reconnection
- All participants view presence status reflecting actual connectivity only