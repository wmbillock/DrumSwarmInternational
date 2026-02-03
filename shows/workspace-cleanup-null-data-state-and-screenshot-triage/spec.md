## Brief

Cleanup task with three deliverables:

1. **Delete stale corps directories**: Remove `corps/cavaliers/` and `corps/scouts/` to achieve true null data state (corps are DB-only now)
2. **Verify corps/.gitkeep**: Ensure `corps/` contains only `.gitkeep` after deletion
3. **Screenshot triage**: Analyze all 26 unprocessed screenshots in `screenshots/` for UI problems, move each to `screenshots/SEEN AND FIXED/`, and append any discovered fix prompts to `screenshots/prompts.md`

### Acceptance Criteria
- `corps/` contains only `.gitkeep`
- No `.png` files remain in `screenshots/` root (all moved to subdirectory)
- `screenshots/prompts.md` updated with any UI issues found

### Constraint
Screenshot filenames contain Unicode narrow no-break space (U+202F) and must be handled with shell globbing, not literal paths.