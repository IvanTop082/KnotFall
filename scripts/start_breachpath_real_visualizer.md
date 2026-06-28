# Start BreachPath Real Visualizer

This starts the real TuringDB engine, the FastAPI BreachPath brain, and the modified source-code version of the official TuringDB visualizer.

The stock Docker visualizer at `http://localhost:18080` is only a reference/debug viewer. The product UI is the modified real visualizer in `apps/visualizer`.

## 1. Start TuringDB Docker

From the project root:

```powershell
docker compose -f docker-compose.turingdb.yml up -d
```

Expected URLs:

- TuringDB API: `http://localhost:16666`
- Stock TuringDB visualizer: `http://localhost:18080`

## 2. Start FastAPI backend

From the project root, in another terminal:

```powershell
python -m uvicorn apps.api.main:app --reload --port 8000
```

Quick check:

```powershell
curl.exe http://localhost:8000/health
```

## 3. Start modified real visualizer

From a third terminal:

```powershell
cd apps/visualizer
npm install
npm run dev
```

Open:

```text
http://localhost:3001
```

## 4. Create a small test network

Use the `Network builder` drawer in the modified visualizer.

Fastest path:

1. Click `Network builder`.
2. Choose `Basic Home Network`.
3. Click `Load example network`.

Manual path:

Add these nodes:

- Router
- Laptop
- Printer
- NAS / Home Server
- Admin Account

Create these typed edges:

- Laptop -> Router: `same_network`
- Laptop -> Printer: `can_access`
- Laptop -> NAS / Home Server: `can_access`
- NAS / Home Server -> Admin Account: `stores_credentials_for`

Every edge must have a cyber relationship type. Do not create blank edges.

## 5. Save to backend / TuringDB

In the `Save to backend / TuringDB` section:

1. Set `Network ID`, for example `home_network`.
2. Set `Network name`, for example `My Home Network`.
3. Set a commit message, for example `Initial network`.
4. Click `Save version`.

The backend returns a version and commit id. If TuringDB writing is unavailable, the network is still saved to the local history fallback under `data/saved_networks/`, which is ignored by Git.

To load it again:

1. Enter the same `Network ID`.
2. Click `Load network`.

Useful API checks:

```powershell
curl.exe http://localhost:8000/networks
curl.exe http://localhost:8000/networks/home_network/history
curl.exe http://localhost:8000/networks/home_network/versions
```

## 6. Use version history

In the same builder section:

1. Click `Version history`.
2. Use `View` to preview an older version without overwriting the latest graph.
3. Use `Analyse` to run the selected-node analysis against that version.
4. Use `Compare` to compare that version with the latest saved version.
5. Use `Restore` to create a new latest version from an old graph snapshot.

Restore does not delete history. It creates a new version with a message like `Restored from version 1`.

Useful API checks:

```powershell
curl.exe "http://localhost:8000/networks/home_network/compare?from_version=1&to_version=2"
curl.exe http://localhost:8000/networks/storage-status
```

## 7. Run compromise simulation

1. Click the Laptop node on the canvas.
2. In `Compromise analysis`, choose `Compromise`.
3. Click `Analyse selected node`, or use the top toolbar `Analyse selected` button.
3. Expected result:
   - affected nodes highlight
   - risky path to Admin Account appears
   - recommendations mention segmentation and privileged credential review/rotation

Successful analysis records the analysed saved version when the network has been saved.

## 8. Try other simulation types

Use the simulation dropdown:

- `Compromise`
- `Offline / destroyed`
- `Spyware`
- `Data leak`
- `Lateral movement`

Each simulation follows different defensive relationship types and returns different recommendations.

## 9. See outdated-analysis warning

1. Run an analysis.
2. Add a new node or edge.
3. The right-side analysis panel should show:

```text
Network changed. Previous exposure analysis may be outdated. Re-run analysis.
```

Click `Re-run analysis` to analyse the same selected node again.

## 10. Local fallback persistence

The builder still supports browser `localStorage` for:

- New network
- Save locally
- Load locally
- Export JSON
- Import JSON

Keep these as the quick fallback if the backend or TuringDB is not running.
