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

## Demo

Run the lifecycle tour to see the full pool → draft → score → reputation → decay → release cycle:

```bash
python -m backend.scripts.tour_demo
```
