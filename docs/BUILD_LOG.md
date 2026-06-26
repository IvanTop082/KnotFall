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
