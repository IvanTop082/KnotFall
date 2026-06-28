# BreachPath API

This is the FastAPI backend for BreachPath.

The backend loads the local demo cyber network, finds bounded exposure paths from a suspected compromised node to critical assets, calculates explainable risk scores, simulates defensive improvements, and returns JSON for the frontend.

Local JSON remains the default graph source. The Dockerized path can also load the `breachpath_demo` graph from TuringDB when `BREACHPATH_GRAPH_SOURCE=turingdb`.

## Install Dependencies

From the project root:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r apps/api/requirements.txt
```

## Run the API

```powershell
uvicorn apps.api.main:app --reload --port 8000
```

## Test URLs

- http://localhost:8000/health
- http://localhost:8000/turingdb/status
- http://localhost:8000/graph
- http://localhost:8000/analysis/compromised/workstation-17
- http://localhost:8000/attack-paths/workstation-17
- http://localhost:8000/recommendations/workstation-17

## Example Commands

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/turingdb/status
curl http://localhost:8000/graph
curl http://localhost:8000/analysis/compromised/workstation-17
curl http://localhost:8000/attack-paths/workstation-17
curl http://localhost:8000/recommendations/workstation-17
```

## TuringDB local setup

On native Windows, `python -m pip install turingdb` may fail if a compatible Windows package is not available. For Windows, use the Docker setup in `docs/TURINGDB_WINDOWS_SETUP.md`.

If the Python SDK is available in your environment, TuringDB is installed with:

```powershell
python -m pip install turingdb
```

The EDTH dataset repo is cloned into:

```text
external/turingdb-hackathon-defense
```

The `external/` folder is ignored by Git so the cloned dataset repo is not committed to BreachPath.

Start TuringDB with Docker from the BreachPath project root:

```powershell
docker compose -f docker-compose.turingdb.yml up
```

TuringDB API:

```text
http://localhost:16666
```

TuringDB visualizer:

```text
http://localhost:18080
```

Test query in the visualizer:

```cypher
MATCH (n) RETURN n LIMIT 50
```

Run the Python connection test from the BreachPath project root:

```powershell
python apps/api/turingdb_integration/connection_test.py
```

## Dockerized TuringDB backend

Native Windows Python does not need the TuringDB SDK for normal local development. The Dockerized API installs `turingdb` inside Linux.

Start TuringDB and the API:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

Import the BreachPath demo graph into TuringDB:

```powershell
docker compose -f docker-compose.dev.yml run --rm api python apps/api/turingdb_integration/import_demo_network.py
```

Switch the API to TuringDB-backed graph loading:

```powershell
$env:BREACHPATH_GRAPH_SOURCE="turingdb"
docker compose -f docker-compose.dev.yml up --build
```
