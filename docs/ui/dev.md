# Frontend + Backend Development

## Prerequisites

- Node.js 18+
- Python 3.11+

## Running the Backend

```bash
cd /path/to/dci-swarm
python -m backend.api.app
# Starts on http://localhost:8000
```

## Running the Frontend

```bash
cd frontend
npm install
npm run dev
# Starts on http://localhost:5173
```

The frontend proxies API calls to `http://localhost:8000` by default. Override with `VITE_API_URL` env var.

## Running Tests

### Frontend

```bash
cd frontend
npx vitest run        # Single run
npx vitest            # Watch mode
npx tsc --noEmit      # Type check
npx vite build        # Production build
```

### Backend

```bash
python -m pytest backend/tests/ -v
```

## Architecture

- **3-column layout**: SideNav (180px) | Main content (flex) | TelemetryPanel (280px)
- **V1 API client**: `frontend/src/services/v1.ts` — typed, with AbortController cancellation
- **UI components**: `frontend/src/ui/` — Panel, DataTable, Tabs, Badge, Card
- **Pages**: `frontend/src/pages/` — one file per route
- **Routes**: `frontend/src/router.tsx`
