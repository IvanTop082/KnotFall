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

Use the `BreachPath Network Exposure Simulator` panel.

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

## 5. Analyse Laptop

1. Click the Laptop node on the canvas.
2. Click `Analyse selected node`.
3. Expected result:
   - affected nodes highlight
   - risky path to Admin Account appears
   - recommendations mention segmentation and privileged credential review/rotation

## Current persistence

The Bit 6 builder uses browser `localStorage` for:

- New network
- Save locally
- Load locally
- Export JSON
- Import JSON

TuringDB persistence for user-created networks is a later step.
