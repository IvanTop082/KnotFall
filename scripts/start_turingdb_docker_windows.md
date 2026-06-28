# Start TuringDB with Docker on Windows

Native `python -m pip install turingdb` may fail on Windows if a compatible Windows package is not available.

For Windows, use Docker to run the TuringDB server and visualizer while keeping the EDTH hackathon dataset repo mounted from this project.

## Requirements

- Docker Desktop is installed.
- Docker Desktop is running.
- The dataset repo exists at `external/turingdb-hackathon-defense`.
- Run these commands from the BreachPath project root.

If PowerShell says `docker: The term 'docker' is not recognized`, Docker Desktop is not installed or the Docker CLI is not on PATH. Install Docker Desktop, start it from the Start menu, then open a new PowerShell window and run `docker --version`.

## Ports

- TuringDB API: `http://localhost:16666`
- Stock TuringDB visualizer: `http://localhost:18080`

## PowerShell Command

```powershell
docker run --rm -it `
  -p 16666:6666 `
  -p 18080:8080 `
  -v "${PWD}\external\turingdb-hackathon-defense:/work" `
  -w /work `
  turingdbai/turingdb:nightly `
  turingdb start -turing-dir /work -i 0.0.0.0 -p 6666 -ui -ui-port 8080
```

## Single-Line Version

```powershell
docker run --rm -it -p 16666:6666 -p 18080:8080 -v "${PWD}\external\turingdb-hackathon-defense:/work" -w /work turingdbai/turingdb:nightly turingdb start -turing-dir /work -i 0.0.0.0 -p 6666 -ui -ui-port 8080
```

If port `18080` is already used by another local app, map the visualizer to another host port:

```powershell
docker run --rm -it -p 16666:6666 -p 19080:8080 -v "${PWD}\external\turingdb-hackathon-defense:/work" -w /work turingdbai/turingdb:nightly turingdb start -turing-dir /work -i 0.0.0.0 -p 6666 -ui -ui-port 8080
```

Then open `http://localhost:19080`.

## Verify the Visualizer

Open:

```text
http://localhost:18080
```

In the visualizer:

1. Select `attack_scenarios`.
2. Run:

```cypher
MATCH (n) RETURN n LIMIT 50
```

The TuringDB API should also be available at:

```text
http://localhost:16666
```
