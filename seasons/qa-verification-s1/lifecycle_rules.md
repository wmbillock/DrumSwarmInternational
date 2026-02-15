# Season Lifecycle Rules

## States
- **registration**: Corps can register. No competitions run.
- **in_progress**: Competitions are active. New registrations closed.
- **completed**: All competitions scored. Final standings locked.
- **archived**: Historical record only.

## Transitions
- registration -> in_progress: Requires at least 2 registered corps.
- in_progress -> completed: All scheduled competitions must have final scores.
- completed -> archived: Manual trigger only. Standings become read-only.

## Competition Rules
- Each corps may enter each competition at most once.
- A corps must be in ON_TOUR or READY_FOR_CONTEST state to compete.
- Scores are final after judging panel submits. No retroactive changes.

## Scoring
- Caption scores: Brass, Percussion, Guard, Visual, General Effect (each 0-20).
- Total score = sum of all captions (max 100).
- Tiebreaker: highest General Effect score wins.

## Penalties
- Late entry (after registration closes): -2.0 from total.
- Incomplete show (missing movements): -5.0 from total.
- Process violations (bypassed hierarchy, skipped rehearsal modes): -1.0 each.
