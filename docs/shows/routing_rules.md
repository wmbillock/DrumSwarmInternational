# Note Routing Rules

Design notes are auto-tagged when appended to a show workspace. Tags are inserted as an HTML comment at the top of each note block.

## Tags

| Tag | Keywords |
|---|---|
| `music` | tempo, bpm, key signature, brass, percussion, woodwind, melody, chord, dynamics, crescendo, decrescendo, forte, piano, measure, beat, instrument, horn, drum, marimba, pit, front ensemble, battery, music |
| `visual` | drill, formation, set, transition, spacing, step size, march, visual, hash, yard line, staging, block, scatter, follow-the-leader |
| `guard` | guard, flag, rifle, sabre, toss, catch, silk, color guard, equipment, spin |
| `ge` | ge, general effect, audience, impact, emotion, story, narrative, theme, arc, pacing, energy |
| `admin` | budget, schedule, deadline, travel, logistics, roster, staffing, uniform, prop, admin |
| `questions` | Text contains a `?` character |

## Default Behavior

If no keyword matches are found, the note is tagged `admin`.

Multiple tags can apply to a single note. Tags are sorted alphabetically.

## Format

Tags are prepended as an HTML comment:

```markdown
<!-- tags: music, visual -->
The brass section should enter at measure 32 in a wedge formation.
```

## Extensibility

To add a new tag, add an entry to `TAG_KEYWORDS` in `backend/services/note_router.py`. The keyword list supports multi-word phrases (matched with word boundaries, case-insensitive).
