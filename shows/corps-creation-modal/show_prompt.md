# Corps Creation Modal

## Objective
Replace the inline Create Corps text input with a modal that auto-generates a corps identity (name, color scheme, mascot, uniform concept) and presents it to the user for approval or customization before creation.

## Deliverables
- Modified frontend/src/components/CorpsCreateModal.tsx with identity preview modal
- Integration with existing POST /api/v1/corps/generate-identity endpoint
- Integration with existing POST /api/v1/corps/generate-icon endpoint
- Color scheme displayed as swatches in modal
- Regenerate individual fields button
- Approve and Create button calling POST /api/v1/corps with full identity
- Updated frontend/src/services/v1.ts with generateIdentity and generateIcon methods

## Constraints
- 18-corps cap enforced on creation
- Must work without ChatGPT CLI (graceful fallback for icon generation)
- Color schemes generated deterministically from corps name hash
- Theme stored as JSON in uniform_concept field
- Use v1.ts for all API calls

## Acceptance Criteria
- Clicking Create Corps opens modal with auto-generated identity preview
- User can regenerate or edit individual identity fields
- Approve and Create submits full identity to POST /api/v1/corps
- Color swatches render correctly
- Modal handles API errors gracefully
- TypeScript compiles clean