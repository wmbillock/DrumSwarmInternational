# Prompt Lint Rules ("Judge Snare")

The prompt linter validates `show_prompt.md` files against structural and content rules.

## Required Sections

Every show prompt must contain these `## ` headings:

- `## Show Concept`
- `## Musical Design`
- `## Visual Design`
- `## Guard Design`
- `## General Effect`
- `## Constraints`
- `## Deliverables`
- `## Evaluation Rubric`

## Checks

| Check | Severity |
|---|---|
| Missing required section | REQUIRED FIX |
| Unfilled placeholder (`TODO`, `TBD`, `[PLACEHOLDER]`, `___`, `XXX`) | REQUIRED FIX |
| Ambiguous `MUST` (no concrete verb/noun within 60 chars) | NICE TO HAVE |
| `## Constraints` section has <2 bullet items | NICE TO HAVE |
| `## Deliverables` section has <1 bullet item | REQUIRED FIX |
| `## Evaluation Rubric` is empty or has no references | NICE TO HAVE |
| Section present but <20 chars of content | ACCEPTABLE RISK |

## Severity Levels

- **REQUIRED FIX** — Must be resolved before the prompt is considered valid.
- **NICE TO HAVE** — Recommended improvements that strengthen the prompt.
- **ACCEPTABLE RISK** — Informational; the prompt may still be usable.

## API

```python
from backend.services.prompt_linter import lint_prompt

report = lint_prompt(content)
report.required_fix    # List[LintFinding]
report.nice_to_have    # List[LintFinding]
report.acceptable_risk # List[LintFinding]
```
