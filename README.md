# DCI Swarm

A multi-agent orchestration system modeled on the drum corps international (DCI) metaphor — corps of AI agents collaborate through seasons of shows, scored performances, and reputation-driven drafting.

## Quick Start

```bash
pip install -e ".[dev]"
python -m pytest backend/tests/ -v
```

## Documentation

- [Architecture](docs/architecture.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Quality Contracts](docs/quality/)
- [Domain Glossary](docs/domain-glossary.md)

## Running the Backend API

Start the FastAPI server:

```bash
uvicorn backend.api.app:app --reload --port 8000
```

The API serves two layers:
- **Legacy routes** at `/api/...` — existing endpoints used by the current frontend
- **V1 routes** at `/api/v1/...` — versioned API layer (see [API Reference](docs/api/openapi.md))

Interactive docs at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

## Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. Expects the backend at `http://localhost:8000`.

## Demo

Run the lifecycle tour to see the full pool → draft → score → reputation → decay → release cycle:

```bash
python -m backend.scripts.tour_demo
```
