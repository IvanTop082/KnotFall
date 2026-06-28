# Start BreachPath Visualizer

This file is kept for continuity. The current official product UI is no longer the interim custom visualizer; it is the modified official TuringDB visualizer source in `apps/visualizer`.

Use `scripts/start_real_turingdb_visualizer_breachpath.md` for the complete current runbook.

## Quick local start

From the project root, start the FastAPI brain:

```powershell
python -m uvicorn apps.api.main:app --reload --port 8000
```

Then start the modified official TuringDB visualizer source:

```powershell
cd apps/visualizer
npm install
npm run dev
```

Open:

```text
http://localhost:3001
```

The stock Docker visualizer remains a reference/debug viewer at `http://localhost:18080`.

For the full TuringDB-backed graph workflow, including importing `breachpath_demo`, use `scripts/start_real_turingdb_visualizer_breachpath.md`.
