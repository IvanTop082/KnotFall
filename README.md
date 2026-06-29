# KnotFall

KnotFall is a defensive cyber graph tool for exploring what an attacker may be able to reach from a compromised machine.

The project is currently under active development and is not the full final product yet. It is a hackathon MVP that already demonstrates graph-based exposure analysis, risk highlighting, recommendations, and saved network versions, but more hardening and polish are still planned.

Demo video: https://youtu.be/1NA7XcIOGPY

## Current State

- The main demo UI is the customised TuringDB visualizer in `apps/visualizer`.
- The backend is a FastAPI service in `apps/api`.
- TuringDB is used for graph storage and the visualizer.
- Local JSON demo data still exists as a fallback and development aid.

## Local URLs

- KnotFall visualizer: `http://localhost:3001`
- FastAPI backend: `http://localhost:8000`
- TuringDB API: `http://localhost:16666`
- TuringDB reference visualizer: `http://localhost:18080`

## Start the Project

Run each part in a separate PowerShell window from the project root unless stated otherwise.

### 1. Start TuringDB and the backend

```powershell
docker compose -f docker-compose.dev.yml up --build
```

This starts:

- TuringDB on `http://localhost:16666`
- FastAPI on `http://localhost:8000`
- the reference TuringDB visualizer on `http://localhost:18080`

### 2. Import the demo graph

In a second PowerShell window:

```powershell
docker compose -f docker-compose.dev.yml run --rm api python apps/api/turingdb_integration/import_demo_network.py
```

This creates the KnotFall demo graph used by the visualizer.

### 3. Start the KnotFall visualizer

In a third PowerShell window:

```powershell
cd apps/visualizer
npm install
npm.cmd run dev
```

Open:

```text
http://localhost:3001
```

### 4. Check the backend

In another PowerShell window, you can test:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/analysis/compromised/workstation-17
```

## Demo Flow

1. Open `http://localhost:3001`.
2. Load or view the KnotFall demo graph.
3. Select a device node.
4. Run compromise analysis.
5. Review highlighted exposure paths, affected systems, risk, and recommendations.
6. Save graph versions and use version history to move between saved snapshots.

## Notes

- This is still a work in progress, so some workflows may change.
- The current goal is a strong demo, not a finished production deployment.
- Do not use `apps/web` for the main demo; the active UI is `apps/visualizer`.
