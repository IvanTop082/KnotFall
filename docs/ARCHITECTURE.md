# BreachPath Architecture

This document describes the planned architecture for BreachPath.

## Project Areas

### apps/web

Future Next.js frontend. It will show the visual graph, selected compromised node, attack paths, risk score, and recommended improvements.

### apps/api

Future FastAPI backend. It will load graph data, find attack paths, calculate risk, and return recommendations.

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
