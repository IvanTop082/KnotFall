# BreachPath Architecture

This document describes the planned architecture for BreachPath.

## Project Areas

### apps/web

Next.js frontend. It loads the graph from the FastAPI backend, lets the user select a compromised node, displays attack path results, and visualises dangerous paths in a React Flow graph.

### apps/api

FastAPI backend. It loads demo graph data, finds bounded attack paths, calculates explainable risk, and returns JSON for the future frontend.

The current Bit 3 backend uses local JSON data through a `LocalJSONPathFinder`. This is designed so a future `TuringDBPathFinder` can replace the local path-finding implementation without changing the API shape.

### Recommendation simulation layer

The current recommendation layer uses a local JSON graph copy. Each possible defensive improvement is applied to a simulated graph, attack paths are recalculated, and before/after risk is compared.

This means recommendations are ranked by measured simulated impact instead of hardcoded advice. The MVP calculates risk reduction, subtracts operational cost, and returns a ranked list of defensive options.

Later, this should map to TuringDB branching and versioning. Each defensive action can be tested in a separate graph branch, then compared with graph diffs before a defender chooses what to change.

### data

Stores demo graph data for the first MVP, starting with JSON.

### packages/shared

Future shared schemas/types used by frontend and backend.

### scripts

Helper scripts for seeding demo data, testing graph queries, and later TuringDB setup.

## Planned Data Flow

1. Frontend asks backend for graph data.
2. User selects a compromised node.
3. Backend finds paths to critical assets.
4. Backend calculates risk and possible improvements.
5. Frontend visualises results.
