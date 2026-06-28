# Start Real TuringDB Visualizer BreachPath

This starts the real TuringDB engine, the BreachPath FastAPI brain, and the modified source-code version of the official TuringDB visualizer.

The stock Docker visualizer at `http://localhost:18080` is only a reference/debug viewer. The BreachPath product UI is the modified official visualizer source in `apps/visualizer`.

## 1. Start TuringDB Docker

From the BreachPath project root:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

Expected host URLs:

- TuringDB API: `http://localhost:16666`
- Stock TuringDB visualizer: `http://localhost:18080`
- FastAPI backend if using the compose API service: `http://localhost:8000`

If you only want TuringDB without the API container, run:

```powershell
docker compose -f docker-compose.turingdb.yml up
```

## 2. Import the demo graph

In a second PowerShell window, from the project root:

```powershell
docker compose -f docker-compose.dev.yml run --rm api python apps/api/turingdb_integration/import_demo_network.py
```

This creates or loads the TuringDB graph:

```text
breachpath_demo
```

The import writes the BreachPath string node IDs, such as `workstation-17`, into node properties. The modified visualizer uses that property when it calls the BreachPath API.

## 3. Start the FastAPI brain

If you are not using the compose API service, start the backend from the project root:

```powershell
python -m uvicorn apps.api.main:app --reload --port 8000
```

Useful checks:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/analysis/compromised/workstation-17
```

The backend can stay in local JSON mode while the visualizer reads the graph from TuringDB. Switch `BREACHPATH_GRAPH_SOURCE=turingdb` only after the import path is verified end to end.

## 4. Start the modified official visualizer

From a third PowerShell window:

```powershell
cd apps/visualizer
npm install
npm run dev
```

Expected product UI:

```text
http://localhost:3001
```

The visualizer defaults are:

```text
TURING_API_PORT=16666
TURING_FRONTEND_PORT=3001
VITE_TURINGDB_DEFAULT_GRAPH=breachpath_demo
VITE_BREACHPATH_API_URL=http://localhost:8000
```

## 5. Test the demo path

1. Open `http://localhost:3001`.
2. Load `breachpath_demo` if it is not already loaded.
3. Run the default query: `MATCH (n) RETURN n LIMIT 100`.
4. Click the node whose BreachPath `id` property is `workstation-17`.
5. The right panel should call `GET /analysis/compromised/workstation-17`.

Expected exposure path highlight:

```text
workstation-17 -> file-server -> admin-account -> domain-controller -> drone-ops-server
```

Expected UI behavior:

- selected suspected node is highlighted
- affected nodes and exposure-path edges are highlighted
- unrelated nodes and edges are faded
- `BreachPath Analysis` panel shows risk, reachable critical systems, highest-risk exposure path, and mitigation recommendations

## Current limitation

The modified visualizer uses actual TuringDB graph data when `breachpath_demo` has been imported and loaded. The BreachPath analysis endpoint can still use the local JSON fallback, so graph display and analysis can temporarily come from different stores while the TuringDB-backed backend path is hardened.
