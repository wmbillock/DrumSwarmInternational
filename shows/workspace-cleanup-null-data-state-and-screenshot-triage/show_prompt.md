## Objective

Clean up the workspace to achieve true null data state for corps and triage all unprocessed screenshots.

## Deliverables

- Clean `corps/` directory containing only `.gitkeep` (cavaliers and scouts directories deleted)
- All screenshots moved from `screenshots/` root to `screenshots/SEEN AND FIXED/`
- Updated `screenshots/prompts.md` with UI fix prompts for any issues found in screenshots

## Acceptance Criteria

- `ls corps/` returns only `.gitkeep`
- `ls screenshots/*.png` returns no matches
- `prompts.md` contains entries for any UI problems discovered in screenshots

## Constraints

- Screenshot filenames contain Unicode narrow no-break space (U+202F) -- use shell globs not literal paths
- Corps are DB-only now; filesystem dirs are stale artifacts

## Swarm Prompt

Execute these steps in order:

### Step 1: Delete stale corps directories
```bash
rm -rf /Users/mattbillock/Development/dci-swarm/corps/cavaliers/
rm -rf /Users/mattbillock/Development/dci-swarm/corps/scouts/
```

### Step 2: Verify corps/.gitkeep
Confirm `/Users/mattbillock/Development/dci-swarm/corps/` contains only `.gitkeep`. Create it if missing:
```bash
touch /Users/mattbillock/Development/dci-swarm/corps/.gitkeep
```

### Step 3: Screenshot triage
For every `.png` file in `/Users/mattbillock/Development/dci-swarm/screenshots/` root (not subdirectories), read each file visually to check for UI problems. For any issues found, append a fix prompt to `/Users/mattbillock/Development/dci-swarm/screenshots/prompts.md`.

Then move all screenshots:
```bash
for f in /Users/mattbillock/Development/dci-swarm/screenshots/*.png; do
  mv "$f" "/Users/mattbillock/Development/dci-swarm/screenshots/SEEN AND FIXED/"
done
```

### Step 4: Verify
- `ls corps/` shows only `.gitkeep`
- No `.png` in `screenshots/` root
- `prompts.md` updated with any findings