# Start the Full BreachPath Stack

This setup runs TuringDB and the FastAPI backend in Docker. The Next.js frontend still runs normally from `apps/web`.

## Start TuringDB and API

From the BreachPath project root:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

By default, the API uses local JSON mode:

```text
BREACHPATH_GRAPH_SOURCE=local
```

Wait until the TuringDB logs say the server has started before running the import command.

## Import the Demo Graph into TuringDB

In a second PowerShell window, from the BreachPath project root:

```powershell
docker compose -f docker-compose.dev.yml run --rm api python apps/api/turingdb_integration/import_demo_network.py
```

Run this as one command by itself. If another command is pasted directly after `.py`, PowerShell may glue the text together and Docker will try to run a filename like `import_demo_network.pydocker`.

The import creates or loads a TuringDB graph called:

```text
breachpath_demo
```

Rerunning the import may create duplicate nodes or edges if the graph is not reset first.

## Use Local JSON Mode

Local JSON mode is the default:

```powershell
$env:BREACHPATH_GRAPH_SOURCE="local"
docker compose -f docker-compose.dev.yml up --build
```

## Use TuringDB Mode

After importing `breachpath_demo`, restart the API with:

```powershell
$env:BREACHPATH_GRAPH_SOURCE="turingdb"
docker compose -f docker-compose.dev.yml up --build
```

## Open Services

- TuringDB visualizer: http://localhost:18080
- FastAPI backend: http://localhost:8000
- FastAPI docs: http://localhost:8000/docs
- BreachPath frontend: http://localhost:3000

## Verify Backend

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/turingdb/status
Invoke-RestMethod http://localhost:8000/graph
Invoke-RestMethod http://localhost:8000/attack-paths/workstation-17
```

## Verify Visualizer

Open http://localhost:18080, select `breachpath_demo`, then run:

```cypher
MATCH (n) RETURN n LIMIT 50
```
