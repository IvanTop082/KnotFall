# BreachPath Network Exposure Simulator

[![Node.js CI](https://github.com/turing-db/turingdb-visualizer/actions/workflows/ci.yml/badge.svg)](https://github.com/turing-db/turingdb-visualizer/actions/workflows/ci.yml)

This is the official TuringDB visualizer source vendored from `https://github.com/turing-db/turingdb-visualizer` and customised for BreachPath.

The source was cloned at commit `f6db08117a00ef822e147449cbb7b9bd39fdcdb7`.

## BreachPath defaults

```text
TURING_API_PORT=16666
TURING_FRONTEND_PORT=3001
VITE_TURINGDB_DEFAULT_GRAPH=breachpath_demo
VITE_BREACHPATH_API_URL=http://localhost:8000
```

## Run the modified visualizer

```bash
npm install
npm run dev
```

Open:

```text
http://localhost:3001
```

The Vite `/api` proxy talks to TuringDB at `http://localhost:16666`. BreachPath compromise analysis calls the FastAPI backend at `http://localhost:8000`.

The stock Docker visualizer at `http://localhost:18080` is reference/debug only; it is not the BreachPath product UI.

## BreachPath builder

Use the builder panel to create a local cyber network with templates such as Laptop, Router, NAS / Home Server, Admin Account, VPN Gateway, and Domain Controller.

Edges must use typed cyber relationships such as `same_network`, `can_access`, `administers`, `stores_credentials_for`, `controls`, and `routes_through`.

To test:

1. Add Laptop, Router, Printer, NAS / Home Server, and Admin Account.
2. Connect Laptop -> Router with `same_network`.
3. Connect Laptop -> Printer with `can_access`.
4. Connect Laptop -> NAS / Home Server with `can_access`.
5. Connect NAS / Home Server -> Admin Account with `stores_credentials_for`.
6. Select Laptop and click `Analyse selected node`.

Local graph save/load uses browser localStorage for now. TuringDB persistence for user-created graphs is a future step.
