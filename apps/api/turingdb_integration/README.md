# TuringDB Integration

This folder is a safe bridge between BreachPath and TuringDB.

The existing FastAPI endpoints still use the local JSON demo graph. Nothing in this folder is imported by the API app yet.

The connection test proves Python can connect to TuringDB and query the provided `attack_scenarios` graph from the EDTH hackathon dataset repo.

Later, BreachPath can add a `TuringDBPathFinder` to replace or support the current local JSON path finder. Later recommendation simulation can also use TuringDB versioning and branching to test defensive changes in separate graph branches.

This integration must remain defensive only. Do not add exploitation, scanning, credential harvesting, payload generation, or offensive automation here.

## Windows Docker Note

The Python SDK may not install on native Windows. For now, TuringDB runs through Docker, and the visualizer should be used to inspect `attack_scenarios`.

Backend integration with the TuringDB SDK is postponed until we decide whether to run the backend inside Docker or use another supported integration path.

Existing FastAPI endpoints still use local JSON.

## Dockerized Backend Path

Bit 5B adds a Dockerized API environment where the TuringDB Python SDK can run on Linux.

The import script loads `data/demo_network.json` into a TuringDB graph called `breachpath_demo`:

```powershell
docker compose -f docker-compose.dev.yml run --rm api python apps/api/turingdb_integration/import_demo_network.py
```

The graph repository can then load `breachpath_demo` into the same in-memory shape used by the existing local JSON path finder.

Local JSON remains the default. To test TuringDB-backed loading, start the Dockerized API with:

```powershell
$env:BREACHPATH_GRAPH_SOURCE="turingdb"
docker compose -f docker-compose.dev.yml up --build
```

## Run the Test

From the BreachPath project root:

```powershell
python apps/api/turingdb_integration/connection_test.py
```

If the test cannot connect, first start TuringDB from the dataset repo:

```powershell
docker compose -f docker-compose.turingdb.yml up
```
