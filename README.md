# BreachPath

BreachPath is a defensive graph-analysis demo for understanding exposure paths from a suspected compromised node to critical systems.

## Current Architecture

- `apps/api`: FastAPI BreachPath brain for graph loading, exposure-path analysis, risk scoring, and recommendations.
- `apps/visualizer`: official product UI, based on the real TuringDB visualizer source and customised for BreachPath.
- `apps/visualizer_prototype`: archived interim React prototype, kept only as reference.
- `apps/web`: original Next.js UI, kept as backup/reference.
- `data`: local JSON demo graph and improvement data.
- `docker-compose.dev.yml`: TuringDB plus the FastAPI backend for local integration.

## Main Local URLs

- Modified BreachPath visualizer: `http://localhost:3001`
- FastAPI backend: `http://localhost:8000`
- TuringDB API: `http://localhost:16666`
- Stock TuringDB visualizer for reference/debug: `http://localhost:18080`

## Start

Use the current runbook:

```powershell
scripts/start_real_turingdb_visualizer_breachpath.md
```
