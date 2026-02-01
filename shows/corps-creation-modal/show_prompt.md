# Corps Creation Modal

Implement a modal-based corps creation flow that auto-generates identity (name, mascot, colors, iconography) and lets users approve or customize before creating.

## Backend
- POST /api/v1/corps/generate-identity
- POST /api/v1/corps/generate-icon
- Update POST /api/v1/corps to accept full identity fields

## Frontend
- Modal component with identity preview
- Color swatches, editable fields
- Regenerate buttons per field
- Approve & Create action
