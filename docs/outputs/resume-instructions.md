# Resume Instructions — Post Semantic QA

## Current State

All semantic QA work is complete. The application has been verified page-by-page with Playwright accessibility snapshots, confirming real data and meaningful content on every page.

## What Was Done

1. **Navigation**: Performers and Staff Market links added to SideNav + NavBar
2. **15 gap closures** (G1-G14, B4): Models registered, dead code removed, tests added, Alembic migration created, error boundaries added
3. **28+ pages verified** via Playwright semantic analysis
4. **2 bugs fixed**: Corps Staff 500 error, Show Library missing timestamps

## What's Next (Potential Future Work)

### Feature Gaps (Not Bugs)
- **Performer Auditions**: No auditions have been run — the performer identity system exists but hasn't been exercised. Running `./dci swarm draft run <corps_id>` would populate performer data.
- **Show Runs**: The `/runs` page is empty because no `./dci swarm run show` commands have been executed.
- **Tour**: No active tours — seasons exist but haven't been put into touring state.

### Polish Opportunities
- Show Library "Active Shows" default filter works but shows an empty state flash before API data loads — could add a skeleton/loading state
- Competition detail "Compare" tab requires selecting two corps — consider pre-selecting top 2
- Performer identity data could be surfaced more prominently in Corps Roster tab

## How to Resume

```bash
# Start services
./dci ten-hut

# Or individually:
./dci forward-march    # Backend on :4224
./dci company-front    # Frontend on :5173

# Run tests
python -m pytest backend/tests/ -x -q

# Check system health
curl http://localhost:4224/api/v1/system/health
```

## Branch

Current branch: `claude/setup-local-development-ClHf8`
