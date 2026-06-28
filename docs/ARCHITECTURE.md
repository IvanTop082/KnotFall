# BreachPath Architecture

This document describes the planned architecture for BreachPath.

## Project Areas

### apps/visualizer

Official BreachPath product UI. This is the real TuringDB visualizer source from `https://github.com/turing-db/turingdb-visualizer`, vendored into the repo and customised for BreachPath.

The visualizer still connects to the TuringDB API for graph loading and rendering. It defaults to the Docker-exposed TuringDB API at `http://localhost:16666` through the Vite `/api` proxy.

BreachPath is now a cyber network builder and exposure simulator. Users build home or company network graphs visually inside the real TuringDB canvas using cyber node templates such as Personal Laptop, Router, Phone, Printer, NAS / Home Server, VPN Gateway, Domain Controller, and Admin Account.

Edges are typed cyber relationships. The UI requires a relationship type such as `same_network`, `can_access`, `administers`, `stores_credentials_for`, `controls`, `routes_through`, or `internet_exposes` before adding an edge. Blank/untyped edges are not part of the BreachPath builder flow.

Edges display as clean lines without arrowheads so the network feels like a normal user-facing topology map. Analysis still uses the stored relationship type and direction where appropriate. For home-style compromise exposure, `same_network`, `can_access`, and `routes_through` are treated as risk-spreading both ways, while relationships such as `administers`, `stores_credentials_for`, `controls`, `internet_exposes`, `backs_up`, `monitors`, and `depends_on` remain directional internally.

Criticality has defaults by device type so normal users do not need to know every impact level upfront. For example, routers, NAS/home servers, work laptops, VPN gateways, firewalls, backup servers, and databases default to `high`, while admin accounts, domain controllers, internet boundary nodes, critical services, and operations servers default to `critical`. Users can override the suggested criticality during node creation.

For analysis, the visualizer sends the current graph to FastAPI with `POST /analysis/compromised`. FastAPI acts as the BreachPath brain and returns affected nodes, exposure paths, risk, mitigation recommendations, followed edge types, and visual severity hints for nodes and edges.

`POST /analysis/compromised` supports simulation types:

- `compromise` for attacker reachability from a compromised device or account.
- `offline` for availability and resilience if a device is broken, destroyed, or offline.
- `spyware` for monitoring/data-visibility exposure from an infected device.
- `data_leak` for data stores, accounts, NAS, server, database, and cloud/session exposure.
- `lateral_movement` for privilege, credential, control, and chokepoint movement paths.

The BreachPath customisation adds a collapsible network builder drawer, built-in example networks for testing, a right-side `BreachPath Analysis` panel, local graph save/load/export/import using browser `localStorage`, and native TuringDB canvas highlighting for selected suspected nodes, affected nodes, affected exposure-path edges, reachable critical assets, and faded unrelated graph elements.

The built-in example networks are `Basic Home Network`, `Home + IoT Network`, and `Small Office Network`. These are designed for quick demos and regression testing of router, laptop, IoT, storage, VPN, identity, and server exposure paths.

The UI tracks a stable graph fingerprint and increments a lightweight version counter when the graph changes. After analysis succeeds, the analysed graph hash/version is stored. If the user adds or changes nodes/edges later, the analysis panel warns: "Network changed. Previous exposure analysis may be outdated. Re-run analysis."

Visual severity is returned by the backend as `visual_severity_by_node` and `visual_severity_by_edge`. The modified real TuringDB canvas uses this to colour affected graph elements: low as blue/grey, medium as yellow/orange, high as orange/red, and critical as red/purple. Highlighted exposure edges pulse for demo-friendly path animation, while unrelated nodes and edges fade.

Normal product mode hides raw database controls such as the Cypher command bar and arbitrary TuringDB example graph selection. Other TuringDB example graphs such as `attack_scenarios`, `supply_chain`, `logistics_risk`, `drone_swarm`, `power_plants`, and `poledb` are hidden from the product UI.

If a TuringDB node does not contain a BreachPath `id` property, the UI falls back to the internal TuringDB node id and shows a mapping warning. The expected local demo path is to import `data/demo_network.json` into TuringDB as `breachpath_demo`, which preserves node ids such as `workstation-17`.

### apps/web

Original Next.js frontend. It is kept as backup/reference while `apps/visualizer` becomes the official product UI.

### apps/api

FastAPI backend. It loads demo graph data, finds bounded attack paths, calculates explainable risk, and returns JSON for the future frontend.

The current Bit 3 backend uses local JSON data through a `LocalJSONPathFinder`. This is designed so a future `TuringDBPathFinder` can replace the local path-finding implementation without changing the API shape.

### Recommendation simulation layer

The current recommendation layer uses a local JSON graph copy. Each possible defensive improvement is applied to a simulated graph, attack paths are recalculated, and before/after risk is compared.

This means recommendations are ranked by measured simulated impact instead of hardcoded advice. The MVP calculates risk reduction, subtracts operational cost, and returns a ranked list of defensive options.

Later, this should map to TuringDB branching and versioning. Each defensive action can be tested in a separate graph branch, then compared with graph diffs before a defender chooses what to change.

### TuringDB integration plan

TuringDB is now the intended graph database and graph-rendering source for the official visualizer UI.

The EDTH hackathon dataset repo provides ready graphs, including `attack_scenarios`. The stock TuringDB visualizer at `http://localhost:18080` is for raw graph inspection.

The modified official TuringDB visualizer in `apps/visualizer` is the BreachPath product UI. It can still load graph data from TuringDB, but the Bit 6 cyber builder uses local canvas state and browser localStorage first so users can quickly create their own network.

The BreachPath backend will add defensive analysis, risk scoring, and recommendations on top of TuringDB data. A planned future class, `TuringDBPathFinder`, will replace or support the current local JSON path finder.

### TuringDB on Windows via Docker

The current app still uses local JSON for the stable MVP.

On Windows, TuringDB will run as a Docker service. The EDTH hackathon graph repo is mounted into the Docker container. With the BreachPath Docker Compose setup, the TuringDB visualizer is available on the Windows host at `http://localhost:18080`, and the TuringDB API is available on the Windows host at `http://localhost:16666`. Inside Docker Compose, the API container reaches TuringDB at `http://turingdb:6666`.

The stock Docker visualizer is reference/debug only. The modified visualizer source in `apps/visualizer` is the product UI and should normally run at `http://localhost:3001`.

### TuringDB-backed graph source

The current local JSON graph remains the FastAPI fallback and default source for stable defensive analysis.

The Dockerized API can switch graph source with `BREACHPATH_GRAPH_SOURCE`:

- `local` loads `data/demo_network.json`.
- `turingdb` loads `breachpath_demo` from TuringDB.

The stock TuringDB visualizer shows the same graph data after `data/demo_network.json` is imported into the `breachpath_demo` graph. The modified official TuringDB visualizer can use this TuringDB graph for display, while the BreachPath builder can also analyse the current local canvas graph through the POST analysis endpoint.

The planned `TuringDBPathFinder` can later replace or support the current local JSON path finder. For Bit 5B, the existing attack-path and risk code is reused on graph data loaded from TuringDB.

### data

Stores demo graph data for the first MVP, starting with JSON.

### packages/shared

Future shared schemas/types used by frontend and backend.

### scripts

Helper scripts for seeding demo data, testing graph queries, and later TuringDB setup.

## Planned Data Flow

1. User creates or loads a cyber network in the modified TuringDB visualizer.
2. User adds typed cyber edges between devices, accounts, services, and assets.
3. User selects a suspected compromised node.
4. Visualizer sends the selected node and current graph to FastAPI `POST /analysis/compromised`.
5. FastAPI follows compromise-relevant relationships and calculates defensive risk.
6. Visualizer highlights affected nodes and edges in the TuringDB canvas.
7. Visualizer shows risk, blast radius, exposure path, and mitigation recommendations in the BreachPath side panel.

## Persistence

The builder still supports browser `localStorage` for New network, Save locally, Load locally, Export JSON, and Import JSON. This remains the fastest demo fallback.

Bit 9 adds backend save/load endpoints for user-created networks:

- `POST /networks/save`
- `GET /networks`
- `GET /networks/{network_id}`
- `GET /networks/{network_id}/history`

Saved networks use IDs such as `home_network`; the intended TuringDB graph name is `breachpath_home_network`. The backend attempts an isolated TuringDB write when the Python SDK and server are available. Because the exact SDK write/reset workflow can vary, local JSON history under `data/saved_networks/` is the reliable temporary commit metadata fallback and is ignored by Git.

Each save creates a commit-like history entry with `commit_id`, `version`, `message`, `created_at`, `node_count`, and `edge_count`. This gives BreachPath a GitHub-like version trail now, while leaving room for native TuringDB branching/versioning later.
