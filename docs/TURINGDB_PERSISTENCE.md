# BreachPath TuringDB persistence runbook

## Why the old backend fell back to local storage

The previous backend used `TuringDBNetworkRepository`, which imported the Python `turingdb` SDK.
That SDK is not published for native Windows Python, so import failed and `/storage/status`
reported `local_fallback` even when the TuringDB Docker server was already running on
`http://localhost:16666`.

The Docker server was reachable the whole time. `GET /` returns HTTP 405 because TuringDB
expects **POST** requests such as `/list_avail_graphs` and `/query`.

## Current approach

- **Graph storage:** TuringDB Docker HTTP API (`POST /query`, `POST /load_graph`, etc.)
- **Version metadata:** local JSON at `data/breachpath_turingdb_metadata.json`
- **No browser localStorage** for save/load when `BREACHPATH_STORAGE_MODE=turingdb`

Each saved version becomes its own TuringDB graph snapshot:

```text
breachpath_<network_id>_v1
breachpath_<network_id>_v2
```

This is snapshot-style versioning, not native Git-like branching unless TuringDB change APIs
are used directly later.

## Start TuringDB Docker

From the BreachPath project root:

```powershell
docker run --rm -it -p 16666:6666 -p 18080:8080 -v "${PWD}\external\turingdb-hackathon-defense:/work" -w /work turingdbai/turingdb:nightly turingdb start -turing-dir /work -ui
```

Stock TuringDB UI (optional reference): `http://localhost:18080`

TuringDB HTTP API: `http://localhost:16666`

## Start backend (Windows host)

```powershell
set BREACHPATH_STORAGE_MODE=turingdb
set TURINGDB_URL=http://localhost:16666
python -m uvicorn apps.api.main:app --reload --port 8000
```

Check storage status:

```powershell
curl http://localhost:8000/storage/status
```

Expected when Docker is running:

```json
{
  "mode": "turingdb",
  "connected": true,
  "repository": "TuringDBHttpNetworkRepository",
  "turingdb_url": "http://localhost:16666",
  "sdk_available": false,
  "http_server_reachable": true,
  "graph_writes_supported": true,
  "graph_storage": "turingdb",
  "metadata_storage": "local_json",
  "message": "Connected to TuringDB through Docker HTTP API. Python SDK not required."
}
```

## Start custom UI

```powershell
cd apps/visualizer
npm run dev
```

Open `http://localhost:3001`.

## Prove persistence

Run the proof script:

```powershell
set BREACHPATH_STORAGE_MODE=turingdb
set TURINGDB_URL=http://localhost:16666
python scripts/test_turingdb_http_persistence.py
```

You should see `PASS`.

In TuringDB, list graphs and confirm snapshots such as:

```text
breachpath_http_persistence_proof_v1
breachpath_http_persistence_proof_v2
```

## Prove localStorage is not used

1. Open browser devtools → Application → Local Storage.
2. Save a network from the UI.
3. Confirm no new `breachpath.networks.*` keys appear for that save path.
4. Confirm the backend metadata file updates: `data/breachpath_turingdb_metadata.json`.
5. Confirm TuringDB lists a new graph snapshot via:

```powershell
python -c "import urllib.request; print(urllib.request.urlopen(urllib.request.Request('http://localhost:16666/list_avail_graphs', data=b'{}', method='POST')).read())"
```

## Local fallback mode (explicit only)

```powershell
set BREACHPATH_STORAGE_MODE=local_fallback
python -m uvicorn apps.api.main:app --reload --port 8000
```

This writes server-side JSON under `data/saved_networks/` and does not use TuringDB.

## Limitations

- Version metadata (names, messages, version index) is stored locally because TuringDB
  does not expose a BreachPath-specific metadata API.
- Graph delete does not yet remove old TuringDB snapshot graphs from the database engine.
- `BREACHPATH_GRAPH_SOURCE=turingdb` for analysis still uses the SDK path inside Docker;
  network persistence no longer depends on the SDK on Windows.
