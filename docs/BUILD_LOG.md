# Build Log

## Bit 1: Project scaffold

Created the initial project folder structure, documentation files, `.gitignore`, and environment example file.

Next step: Bit 2, create the demo cyber network data.

## Bit 2: Demo cyber network data

Added demo graph data, demo alerts, improvement options, data model documentation, and a validation script.

## Bit 3: Attack path backend

Added a FastAPI backend that loads the demo cyber network, finds bounded attack paths from a compromised node to critical assets, calculates explainable risk scores, and returns clean JSON for the future frontend.

## Bit 4: Visual frontend

Added a Next.js frontend that loads the demo cyber graph from the FastAPI backend, lets the user select a compromised node, requests attack path analysis, and visualises dangerous paths with a risk explanation panel.

## Bit 5: Recommendation simulation engine

Added a local recommendation engine that tests possible defensive improvements by simulating each action, recalculating attack-path risk, comparing before/after risk, and ranking options by risk reduction minus operational cost. The design is modular so this local simulation can later be replaced by TuringDB versioned branching and diffing.

## Bit 5A: TuringDB setup and connection test

Added a safe TuringDB setup path using the EDTH hackathon dataset repo, documented how to start the TuringDB server and visualizer, and added a Python connection test for querying the `attack_scenarios` graph. Existing local JSON backend and Next.js frontend were left unchanged.

## Bit 5A: TuringDB Docker setup for Windows

Added Windows-friendly Docker setup notes for running TuringDB with the EDTH hackathon dataset repo, including Docker Compose support and documentation for using the TuringDB visualizer with the `attack_scenarios` graph. Existing local JSON backend and frontend remain unchanged.

## Bit 5B: TuringDB-backed backend integration

Added Dockerized backend support for using the TuringDB Python SDK, a script to import the BreachPath demo network into TuringDB, and a graph repository layer so the existing attack-path brain can later run on TuringDB-backed data while keeping local JSON fallback.

## Bit 5: Custom TuringDB Visualizer + BreachPath Brain Integration

Added `apps/visualizer` as the official BreachPath product UI, connected node click events to a FastAPI analysis endpoint, added `/analysis/compromised/{node_id}` for frontend-friendly defensive exposure results, and added path highlighting with a BreachPath analysis side panel. The old `apps/web` UI and local JSON fallback remain available as backup/reference. Next step is switching the backend graph source from local JSON to TuringDB-backed graph data.

## Bit 5 Correction: Real TuringDB Visualizer Customisation

Corrected the Bit 5 UI direction. The interim custom React visualizer was moved to `apps/visualizer_prototype`, and the real TuringDB visualizer source from `https://github.com/turing-db/turingdb-visualizer` was vendored under `apps/visualizer`.

The modified official visualizer now defaults to the Docker TuringDB API on `http://localhost:16666`, runs locally on `http://localhost:3001`, and calls the BreachPath FastAPI endpoint `GET /analysis/compromised/{node_id}` when a graph node is clicked. A BreachPath analysis store, API client, right-side panel, and native TuringDB canvas highlighter were added.

Current limitation: the visualizer uses actual TuringDB graph data after `breachpath_demo` is imported, while FastAPI can still use the local JSON fallback for analysis. The next step is hardening the TuringDB-backed FastAPI graph source so display and analysis both come from the same TuringDB graph by default.

## Bit 6: Cyber Network Builder in Real TuringDB Visualizer

Verified that `apps/visualizer` is the real TuringDB visualizer source and kept the previous custom React Flow UI only as `apps/visualizer_prototype`.

Added cyber node templates for home and business networks, typed cyber edge creation with smart relationship suggestions, and a BreachPath builder panel inside the real TuringDB visualizer canvas. The product UI is now narrowed to cyber network exposure simulation and hides unrelated example graph domains from the graph selector.

Added `POST /analysis/compromised` so the visualizer can send the current graph to the FastAPI brain, run defensive exposure analysis for a selected node, highlight affected nodes/edges, and show risk plus recommendations in the BreachPath panel.

Added local New network, Save locally, Load locally, Export JSON, and Import JSON using browser localStorage. TuringDB remains the long-term graph persistence target.

## Bit 7: User-Facing Network Builder UX

Refined the modified real TuringDB visualizer so BreachPath feels like a cyber network builder and exposure simulator instead of a raw database explorer.

Hid irrelevant graph datasets from the product UI, removed the normal-mode Cypher/query command bar, replaced the fixed builder block with a collapsible Network builder drawer, and improved node creation so users can set template, label, criticality, zone, internet exposure, admin privileges, and notes.

Changed graph edges to display as clean lines without arrowheads while preserving relationship type and direction metadata for analysis. Improved analysis results with clearer affected-device, critical-device, exposure-path, explanation, and fallback recommendation messaging.

Added home-network recommendation rules for same-network spread, router exposure, NAS/home server exposure, printer access, work laptop separation, and admin account credential risk.

## Bit 8: Guided Criticality and Example Networks

Added default criticality by device template so routers, internet boundaries, admin accounts, domain controllers, databases, work laptops, NAS/home servers, VPN gateways, firewalls, and similar systems start with useful impact levels.

Added explanation text in the node creation flow so users understand why a device is low, medium, high, or critical and can still override the suggested value.

Fixed home-style compromise traversal so `same_network`, `can_access`, and `routes_through` can spread risk bidirectionally, while admin, credential, control, backup, monitoring, dependency, and internet-exposure relationships remain directional.

Added router-focused recommendations for changing the router admin password, updating firmware, disabling remote administration, separating guest/IoT devices, and reviewing connected devices.

Added built-in example networks for Basic Home Network, Home + IoT Network, and Small Office Network testing.

## Bit 9: Persistence, Versioning, Simulation Types, and Visual Severity

Added save/load network endpoints for user-created BreachPath networks, including `POST /networks/save`, `GET /networks`, `GET /networks/{network_id}`, and `GET /networks/{network_id}/history`.

Added version/history support with commit-like metadata containing commit id, version, message, timestamp, node count, and edge count. TuringDB write is attempted when available, while a local JSON history fallback keeps the demo reliable.

Added graph fingerprint tracking in the visualizer so previous analysis is marked outdated when the user changes the graph after running a simulation.

Added `simulation_type` to current-graph analysis for compromise, offline/destroyed, spyware, data leak, and lateral movement scenarios.

Added visual severity colour coding for affected nodes/edges and pulsing highlighted exposure paths in the real TuringDB canvas.

Added animated dotted/dashed exposure path visualisation after analysis. Severity now affects highlighted path styling, with stronger animated lines for higher-risk paths and faded styling for unrelated edges.

## Bit 10: Network version history and analysis audit trail

Added GitHub-like network version history for user-created BreachPath graphs, including manual `Save version`, version history, read-only version preview, restore-as-new-version, and compare-version support.

Added backend endpoints for saving versions, listing versions, loading a specific version, restoring a previous version, comparing two versions, and reporting storage status. Analysis results now include `network_id`, `version`, `graph_hash`, `simulation_type`, and `analysed_at`, and saved versions are marked as analysed after a successful simulation.

The visualizer now shows storage status, saved/preview versions, analysis freshness, and version history controls inside the customised real TuringDB visualizer. TuringDB write support remains best-effort and honest; local JSON history stays the reliable fallback.

## Bit 11: Network Library and Version History UI

Added a clearer Network Library inside the customised real TuringDB visualizer, with multiple local networks, create/rename/delete, visible save/load feedback, JSON import/export, and saved network browsing.

Added a separate Version History panel for saved snapshots, including view, restore, compare, and analyse actions. Viewing an old version opens a read-only preview, and restoring an old version creates a new latest version instead of deleting history.

Improved manual localStorage fallback using `breachpath.networks.index`, `breachpath.networks.<network_id>`, and `breachpath.currentNetworkId`, while keeping backend/TuringDB persistence honest through storage status messaging.

Added top toolbar controls for Network Library, Version History, Save Version, current network/version display, and unsaved changes status.

## Bit 12: Navigation and Tool Panel UX Cleanup

Moved controls out of the giant fixed sidebar pattern and into navbar-driven tool panels inside the customised real TuringDB visualizer.

Added separate closable panels for Network Builder, Analyse, Save / Load, Version History, and Example Networks so the canvas stays the main focus and users no longer need to scroll through one long control wall.

Kept existing builder, analysis, save/load, version history, examples, highlighting, and animated path functionality while making each tool panel internally scrollable and easier to find.

## Bit 13: Recommendation Reasoning and Attack-Type-Specific Highlighting

Replaced broad reachable-node highlighting with simulation-specific traversal rules, ranked critical paths, backend-selected highlighted nodes/edges, and firewall/segmentation blocker handling.

Replaced generic recommendations with path-based recommendations that explain the triggering path, relevant edge types, what the action fixes, expected effect, confidence, and defensive next steps.

Updated the BreachPath Analysis panel to show ranked path reasoning, blocked/reduced paths, and recommendation explanations. Added deterministic backend tests proving phone, router, firewall, data leak, offline, and lateral-movement scenarios do not all highlight the same graph.

## Bit 14: Analysis Transparency and Edge Direction Evidence

Added traversal reasoning to analysis responses, including followed edges, skipped edge reasons, ranked-but-not-highlighted paths, connected-but-not-highlighted nodes, and all reachable debug nodes/edges.

Made edge direction visible in the BreachPath builder and kept only suitable relationships configurable as bidirectional. Added a `Show all reachable nodes` debug toggle so low-relevance reachable nodes can be shown muted without changing the default ranked-path highlighting.

Added evidence tests for the Admin Account and File Server direction case, proving `stores_credentials_for` is not traversed backwards unless a valid `can_access` or equivalent edge is added.
