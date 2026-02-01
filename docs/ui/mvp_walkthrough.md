# MVP UI Walkthrough

## Prerequisites

- Python 3.11+, Node 20+
- Dependencies installed: `pip install -e .` and `cd frontend && npm install`

## 1. Generate demo data

```bash
export DCI_PROJECT_ROOT=$(pwd)
./dci swarm demo tour --seed 42 --seasons 2 --corps-count 3 --yes
```

This creates corps, shows, seasons, standings, and reputation data under the project root.

## 2. Start the backend

```bash
DCI_PROJECT_ROOT=$(pwd) uvicorn backend.api.app:app --reload --port 8000
```

## 3. Start the frontend

```bash
cd frontend
npm run dev
```

Opens at `http://localhost:5173` (default Vite port).

## 4. What to verify

### Command Center (`/`)

- System vitals cards (active corps, total agents, failure rate, stale reps)
- Corps status grid with progress bars
- Active shows table
- Recent activity feed
- Data refreshes every 15 seconds

### Corps List (`/corps`)

- Card grid showing all 3 demo corps
- Each card shows name, state badge, philosophy, roster size, placement count
- Click a card to navigate to corps detail

### Corps Detail — History Tab (`/corps/:id/history`)

- Click the "History" tab in the corps detail view
- Table of competition placements with season, placement rank, score, show slug
- Summary row: total seasons, best placement, average score

### Runs & Rehearsals (`/runs`)

- Table of all run manifests (run ID, show, corps, season, status, timestamps)
- Click a row to open run detail

### Run Detail (`/runs/:runId`)

- Manifest card with metadata, config, and inputs
- Output viewer showing the run's output text
- Back link returns to runs list

### Sidebar Navigation

- Left sidebar with section abbreviations (CMD, SHW, CRP, RUN, etc.)
- Active section highlighted
- All links navigate correctly
