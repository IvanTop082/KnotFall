# BreachPath API

This is the Bit 3 FastAPI backend for BreachPath.

The backend loads the local demo cyber network, finds bounded attack paths from a compromised node to critical assets, calculates explainable risk scores, and returns JSON for the future frontend.

It does not connect to TuringDB yet. The path-finding code is modular so a future TuringDB-backed path finder can replace the local JSON implementation.

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
- http://localhost:8000/graph
- http://localhost:8000/attack-paths/workstation-17

## Example Commands

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/graph
curl http://localhost:8000/attack-paths/workstation-17
```
