## Show Concept
After each competition, generate and store judge critiques per corps. Provide an endpoint for clarifying critique feedback. Display critiques in the competition detail view.

## Musical Design
Backend changes:

### Critique generation (in tour_coordinator.py or competition scoring)
After run_competition_round scores each competition:
- For each corps in the competition, generate a critique markdown file
- Store at seasons/{season_id}/performances/{corps_id}/critique_round_{N}.md
- Critique content: per-caption feedback (brass, percussion, guard, visual, general_effect), overall assessment, specific improvement recommendations
- Use the LLM client to generate the critique based on scores and the show prompt

### New endpoint: POST /api/v1/corps/{id}/critique/{round}/clarify
- Body: {question: str}
- Loads the critique file, uses LLM to answer the clarifying question in context
- Returns {answer: str, round: int, corps_id: str}
- Add to backend/api/v1/corps.py

### New endpoint: GET /api/v1/competitions/{competition_id}/critiques
- Returns list of critique summaries for all corps in this competition
- Each entry: {corps_id: str, corps_name: str, round: int, overall_assessment: str, has_full_critique: bool}

## Visual Design
Frontend changes:

### frontend/src/pages/CompetitionLive.tsx
Add a "Critiques" tab to the existing tabs (standings, scorecards, tapes).
Critiques tab shows:
- List of corps with their critique summaries
- Click to expand full critique (loads from file)
- Per-caption feedback displayed in styled cards
- "Ask a Question" button that opens a text input and calls the clarify endpoint

### frontend/src/services/v1.ts
Add: getCompetitionCritiques, clarifyCorpsCritique API calls.

## Guard Design
- Handle missing critique files gracefully (return empty critique)
- Clarify endpoint should work even if critique file is minimal
- Handle competition not found

## General Effect
Judge critiques provide actionable feedback to each corps after every competition, enabling meaningful self-improvement cycles.

## Constraints
- Use the existing LLM client from app.py get_task_manager()
- Store critiques as markdown files in the season performances directory
- Do not modify existing scoring logic
- Critique generation should be best-effort (if LLM fails, store a placeholder)

## Deliverables
- Critique generation logic (in tour_coordinator.py or new file)
- Modified backend/api/v1/corps.py with clarify endpoint
- Modified backend/api/v1/competitions router with critiques endpoint
- Modified frontend/src/pages/CompetitionLive.tsx with Critiques tab
- Modified frontend/src/services/v1.ts with new API calls

## Evaluation Rubric
- Critique files generated after competition: 25 points
- Critique content includes per-caption feedback: 15 points
- Clarify endpoint works with context: 15 points
- Competition critiques list endpoint: 15 points
- CompetitionLive Critiques tab UI: 20 points
- TypeScript compiles: 10 points