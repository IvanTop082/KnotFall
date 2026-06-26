from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import DEFAULT_MAX_DEPTH, DEFAULT_MAX_PATHS_PER_ASSET
from .graph_loader import GraphDataError, load_demo_network
from .path_finder import LocalJSONPathFinder
from .recommendations import LocalRecommendationEngine
from .schemas import (
    AttackPathResponse,
    ErrorResponse,
    GraphResponse,
    RecommendationResponse,
)


app = FastAPI(
    title="BreachPath API",
    description="Attack-path analysis API for the BreachPath MVP.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "breachpath-api",
    }


@app.get("/graph", response_model=GraphResponse)
def get_graph():
    graph = _load_graph_or_error()

    return {
        "metadata": graph["metadata"],
        "nodes": graph["nodes"],
        "edges": graph["edges"],
    }


@app.get(
    "/attack-paths/{compromised_node_id}",
    response_model=AttackPathResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_attack_paths(
    compromised_node_id: str,
    max_depth: int = Query(DEFAULT_MAX_DEPTH, ge=1, le=20),
    max_paths_per_asset: int = Query(DEFAULT_MAX_PATHS_PER_ASSET, ge=1, le=20),
):
    graph = _load_graph_or_error()

    if compromised_node_id not in graph["node_lookup"]:
        raise HTTPException(
            status_code=404,
            detail=f"Node not found: {compromised_node_id}",
        )

    finder = LocalJSONPathFinder(graph)
    results = finder.find_attack_paths(
        compromised_node_id=compromised_node_id,
        max_depth=max_depth,
        max_paths_per_asset=max_paths_per_asset,
    )

    unique_assets = {result["asset_id"] for result in results}
    message = (
        f"Found {len(results)} attack path results."
        if results
        else f"No attack paths found from {compromised_node_id}."
    )

    return {
        "compromised_node": compromised_node_id,
        "max_depth": max_depth,
        "paths_found": len(results),
        "critical_assets_found": len(unique_assets),
        "message": message,
        "results": results,
    }


@app.get(
    "/recommendations/{compromised_node_id}",
    response_model=RecommendationResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_recommendations(
    compromised_node_id: str,
    max_depth: int = Query(DEFAULT_MAX_DEPTH, ge=1, le=20),
    max_paths_per_asset: int = Query(DEFAULT_MAX_PATHS_PER_ASSET, ge=1, le=20),
):
    try:
        engine = LocalRecommendationEngine()
        return engine.recommend(
            compromised_node_id=compromised_node_id,
            max_depth=max_depth,
            max_paths_per_asset=max_paths_per_asset,
        )
    except ValueError as error:
        if str(error).startswith("Node not found:"):
            raise HTTPException(status_code=404, detail=str(error)) from error
        raise HTTPException(status_code=500, detail=str(error)) from error
    except GraphDataError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


def _load_graph_or_error():
    try:
        return load_demo_network()
    except GraphDataError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
