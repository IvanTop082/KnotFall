# TuringDB Windows Setup

BreachPath is using Docker for TuringDB on Windows because native `python -m pip install turingdb` may fail when a compatible Windows package is not available.

This keeps the current BreachPath backend and frontend stable while still letting us explore the EDTH hackathon graphs through TuringDB.

## What Each Piece Does

- TuringDB engine/image: runs the graph database server inside Docker.
- `turingdb-hackathon-defense` dataset repo: contains ready EDTH challenge graphs, including `attack_scenarios`.
- TuringDB visualizer: browser UI exposed by the Docker container at `http://localhost:18080` when using the BreachPath Docker Compose setup.

We do not need to clone the core `turingdb` C++ repo right now.

The product UI now uses a modified source-code copy of `turingdb-visualizer` in `apps/visualizer`. The Docker visualizer remains useful as a stock reference/debug viewer.

For this project, we need:

- Docker image for running TuringDB.
- Hackathon defense repo for the ready graphs.
- Stock visualizer via `http://localhost:18080`.
- Modified product visualizer via `http://localhost:3001`.

## Start with Docker

From the BreachPath project root:

```powershell
docker run --rm -it -p 16666:6666 -p 18080:8080 -v "${PWD}\external\turingdb-hackathon-defense:/work" -w /work turingdbai/turingdb:nightly turingdb start -turing-dir /work -i 0.0.0.0 -p 6666 -ui -ui-port 8080
```

If PowerShell says `docker: The term 'docker' is not recognized`, install Docker Desktop first, start it, then open a new PowerShell window and check:

```powershell
docker --version
```

If `http://localhost:18080` shows another service, choose another host UI port:

```powershell
docker run --rm -it -p 16666:6666 -p 19080:8080 -v "${PWD}\external\turingdb-hackathon-defense:/work" -w /work turingdbai/turingdb:nightly turingdb start -turing-dir /work -i 0.0.0.0 -p 6666 -ui -ui-port 8080
```

Then open:

```text
http://localhost:19080
```

## Start with Docker Compose

From the BreachPath project root:

```powershell
docker compose -f docker-compose.turingdb.yml up
```

## Verify

Open the visualizer:

```text
http://localhost:18080
```

Select `attack_scenarios`, then run:

```cypher
MATCH (n) RETURN n LIMIT 50
```

The TuringDB API should be available at:

```text
http://localhost:16666
```
