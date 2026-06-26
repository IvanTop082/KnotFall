# BreachPath Web

This is the Bit 4 Next.js frontend for BreachPath.

It loads the demo cyber graph from the FastAPI backend, lets a user select a compromised node, requests attack-path analysis, and highlights dangerous paths in a React Flow graph.

## Install

From the project root:

```powershell
cd apps/web
npm install
```

## Run Backend

From the project root:

```powershell
python -m uvicorn apps.api.main:app --reload --port 8000
```

## Run Frontend

From `apps/web`:

```powershell
npm run dev
```

## Test URLs

- Website: http://localhost:3000
- Backend health: http://localhost:8000/health
- Backend graph: http://localhost:8000/graph
- Attack paths: http://localhost:8000/attack-paths/workstation-17
