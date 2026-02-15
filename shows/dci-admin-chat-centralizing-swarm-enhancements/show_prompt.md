## Objective

Build a live-only centralized admin chat room with Discord/IRC-style interface enabling the Director (DCI Swarm Director as primary interlocutor), DSI admin, and one designated representative per corps to discuss swarm operations, investigate system failures, celebrate wins, and make scheduling decisions collaboratively. The Director drives conversation by asking targeted questions of corps directors and DCI agents, summarizing input, and clearly signaling when it's the user's turn to respond with prominent visual turn indicators adjustable based on operational tempo. The Director maintains full operational visibility while other participants access role-appropriate data. Corps representatives function as operational avatars of their respective executive directors, empowered to coordinate decisions within chat and report back to their home organizations. Chat remains live-only with real-time notifications respecting presence status (immediate alerts for online; notifications upon reconnection for offline), no message editing/deletion, and no archival exports. Participants access static membership roster directly without authentication—system recognizes fixed participants and displays real-time online/offline status. All participants display as available operational avatars ready to coordinate with presence status reflecting actual connectivity. Participants can query dependents as needed for operational context. Chat discussions inform decision-making but do not affect executing sessions until formal task creation.

## Deliverables

- Chat interface with Discord/IRC-style layout: message history pane, input field with font styling support (bold, italic, underline, color), participant roster sidebar with role and real-time online/offline status display
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
- Conversation flow management system: Director-led interlocution with prominent visual turn indicator clearly indicating whose turn it is to respond; design allows for adjustment or dial-back based on operational tempo
- Director question/summary signals prominently displayed and unambiguous
- Task creation mechanism translating chat discussion outcomes into actionable operational changes
- Session isolation ensuring chat does not impact executing operations until task is formally created

## Constraints

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
- Director drives primary conversation with corps directors and DCI agents: asks targeted questions, summarizes input, clearly signals user's turn with prominent visual turn indicators; indicator design allows for adjustment or dial-back
- Real-time notifications targeted to specific participants based on conversation context and presence status
- Turn indicator must clearly communicate whose responsibility it is to respond next; adjustability allows for operational flexibility

## Acceptance Criteria

- Users access the static participant roster directly and join the chat as recognized fixed members without authentication
- Chat interface displays Discord/IRC-style layout with message history, input field, and participant roster sidebar with roles and real-time online/offline status
- Director receives full operational context; other participants receive role-appropriate data visibility at message level
- All online targeted participants receive immediate real-time notifications of Director questions or new messages upon posting; offline participants receive notifications upon reconnection
- Font styling (bold, italic, underline, color) is supported in message input and displays correctly in message history
- Posted messages cannot be edited or deleted; all messages remain immutable for operational transparency
- Messages display with speaker attribution and timestamp in chronological order
- Live messaging enables collaborative discussion of swarm operations and scheduling decisions
- Closed group membership restricts participation to Director, DSI admin, and one corps representative per team
- Participants can query dependent data as operationally needed
- Chat supports operational data discussion and decision-making workflow without external archival or export
- Real-time online/offline presence status accurately reflects actual participant connectivity and updates in roster
- All participants display as available operational avatars within presence display
- Corps representatives understand their role as operational avatars of their executive directors and coordinate decisions within the chat
- Director successfully drives conversation by asking targeted questions of corps directors and DCI agents, summarizing responses, and clearly signaling when user input is needed with prominent visual turn indicators
- Turn indicator prominently highlights whose turn it is to respond, making user expectations obvious; design clearly communicates responsibility for next response; design can be adjusted or dialed back as operational needs change
- Executing sessions remain unaffected by chat discussions until a formal task is created and applied
- Task creation workflow allows deliberate transition from chat discussion to operational implementation
- Notification system respects presence status: online users receive immediate alerts; offline users see notifications upon reconnection