# BreachPath Architecture

This document describes the planned architecture for BreachPath.

## Project Areas

### apps/web

Next.js frontend. It loads the graph from the FastAPI backend, lets the user select a compromised node, displays attack path results, and visualises dangerous paths in a React Flow graph.

### apps/api

FastAPI backend. It loads demo graph data, finds bounded attack paths, calculates explainable risk, and returns JSON for the future frontend.

The current Bit 3 backend uses local JSON data through a `LocalJSONPathFinder`. This is designed so a future `TuringDBPathFinder` can replace the local path-finding implementation without changing the API shape.

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
