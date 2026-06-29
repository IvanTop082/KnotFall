from datetime import UTC, datetime
import threading

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    BREACHPATH_GRAPH_SOURCE,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_PATHS_PER_ASSET,
    TURINGDB_GRAPH_NAME,
    TURINGDB_HOST,
)
from .graph_loader import (
    GraphDataError,
    build_adjacency_list,
    build_node_lookup,
    load_configured_graph,
    validate_graph_data,
)
from .path_finder import LocalJSONPathFinder
from .recommendations import LocalRecommendationEngine
from .repositories.network_repository import (
    StorageUnavailableError,
    get_network_repository,
    graph_hash,
)
from .schemas import (
    AttackPathResponse,
    CompromisedNodeAnalysisRequest,
    CompromisedNodeAnalysisResponse,
    ErrorResponse,
    GraphResponse,
    NetworkCommitSummary,
    NetworkCompareResponse,
    NetworkSaveRequest,
    NetworkSaveResponse,
    NetworkSaveVersionRequest,
    NetworkStorageStatusResponse,
    NetworkSummary,
    RecommendationResponse,
    SavedNetworkResponse,
    SavedNetworkVersionResponse,
)


app = FastAPI(
    title="BreachPath API",
    description="Attack-path analysis API for the BreachPath MVP.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ],
    allow_origin_regex=(
        r"^http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|"
        r"192\.168\.\d+\.\d+)(:\d+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


COMPROMISE_RELATIONSHIPS = {
    "same_network",
    "can_access",
    "administers",
    "stores_credentials_for",
    "controls",
    "routes_through",
    "internet_exposes",
    "backs_up",
    "monitors",
    "depends_on",
}

COMPROMISE_BIDIRECTIONAL_RELATIONSHIPS = {
    "same_network",
    "can_access",
    "routes_through",
}

LEGACY_RELATIONSHIP_ALIASES = {
    "stores_credentials": "stores_credentials_for",
    "grants_access": "controls",
    "authenticates_to": "can_access",
}

CRITICALITY_SCORES = {
    "low": 30,
    "medium": 60,
    "high": 85,
    "critical": 100,
}

EDGE_RISK_SCORES = {
    "low": 25,
    "medium": 55,
    "high": 85,
}

SIMULATION_RULES = {
    "compromise": {
        "label": "Compromise",
        "purpose": "show where control or access could spread from a suspected compromised node",
        "follow": {
            "same_network",
            "can_access",
            "routes_through",
            "administers",
            "stores_credentials_for",
            "controls",
            "internet_exposes",
        },
        "bidirectional": {"same_network"},
        "reverse_for_impact": set(),
        "priority_keywords": {
            "admin",
            "account",
            "router",
            "nas",
            "file",
            "server",
            "domain",
            "database",
            "vpn",
            "critical",
            "credential",
            "internet",
            "work_laptop",
        },
        "dangerous_edges": {
            "administers",
            "controls",
            "stores_credentials_for",
            "internet_exposes",
            "can_access",
        },
        "threshold": 45,
        "max_paths": 5,
    },
    "offline": {
        "label": "Offline / destroyed",
        "purpose": "show what could stop working if this node is unavailable",
        "follow": {"depends_on", "routes_through", "backs_up", "monitors"},
        "bidirectional": set(),
        "reverse_for_impact": {"depends_on"},
        "priority_keywords": {
            "router",
            "firewall",
            "gateway",
            "vpn",
            "backup",
            "monitoring",
            "server",
            "database",
            "critical",
            "domain",
        },
        "dangerous_edges": {"depends_on", "routes_through", "backs_up", "monitors"},
        "threshold": 35,
        "max_paths": 5,
    },
    "spyware": {
        "label": "Spyware",
        "purpose": "show what this device could observe, read, or expose",
        "follow": {"same_network", "can_access", "monitors", "stores_credentials_for"},
        "bidirectional": {"same_network"},
        "reverse_for_impact": set(),
        "priority_keywords": {
            "phone",
            "laptop",
            "work",
            "nas",
            "file",
            "database",
            "cloud",
            "account",
            "credential",
            "sensitive",
        },
        "dangerous_edges": {"can_access", "monitors", "stores_credentials_for"},
        "threshold": 45,
        "max_paths": 5,
    },
    "data_leak": {
        "label": "Data leak",
        "purpose": "show what sensitive information could be exposed",
        "follow": {"can_access", "stores_credentials_for", "backs_up", "depends_on"},
        "bidirectional": set(),
        "reverse_for_impact": set(),
        "priority_keywords": {
            "nas",
            "database",
            "file",
            "server",
            "admin",
            "account",
            "cloud",
            "credential",
            "backup",
            "sensitive",
            "data",
        },
        "dangerous_edges": {"can_access", "stores_credentials_for", "backs_up"},
        "threshold": 45,
        "max_paths": 5,
    },
    "lateral_movement": {
        "label": "Lateral movement",
        "purpose": "show possible movement toward higher privilege or critical systems",
        "follow": {
            "can_access",
            "administers",
            "controls",
            "stores_credentials_for",
            "routes_through",
        },
        "bidirectional": set(),
        "reverse_for_impact": set(),
        "priority_keywords": {
            "admin",
            "account",
            "domain",
            "controller",
            "server",
            "database",
            "vpn",
            "gateway",
            "router",
            "firewall",
            "credential",
            "critical",
        },
        "dangerous_edges": {
            "administers",
            "controls",
            "stores_credentials_for",
            "routes_through",
            "can_access",
        },
        "threshold": 45,
        "max_paths": 5,
    },
}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "breachpath-api",
    }


@app.get("/turingdb/status")
def get_turingdb_status():
    response = {
        "graph_source": BREACHPATH_GRAPH_SOURCE,
        "turingdb_host": TURINGDB_HOST,
        "turingdb_graph_name": TURINGDB_GRAPH_NAME,
        "status": "not_checked",
    }

    try:
        from .turingdb_integration.graph_repository import TuringDBGraphRepository

        repository = TuringDBGraphRepository(
            host=TURINGDB_HOST,
            graph_name=TURINGDB_GRAPH_NAME,
        )
        ping_result = repository.ping()
        response.update(ping_result)
    except Exception as error:
        response.update(
            {
                "status": "not_connected",
                "error": str(error),
            }
        )

    return response


@app.get("/storage/status")
def get_storage_status():
    repository = get_network_repository()
    return repository.storage_status()


def _storage_repository():
    return get_network_repository()


def _raise_storage_unavailable(error: StorageUnavailableError) -> None:
    raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/graph", response_model=GraphResponse)
def get_graph():
    graph = _load_graph_or_error()

    return {
        "metadata": graph["metadata"],
        "nodes": graph["nodes"],
        "edges": graph["edges"],
    }


@app.post("/networks/save", response_model=NetworkSaveResponse)
def save_network(request: NetworkSaveRequest):
    repository = _storage_repository()
    try:
        repository.ensure_available()
        result = repository.save_network(
            network_id=request.network_id,
            name=request.name,
            graph=request.graph.dict(),
            message=request.message,
        )
    except StorageUnavailableError as error:
        _raise_storage_unavailable(error)

    return {
        "network_id": result.network_id,
        "name": result.name,
        "commit_id": result.commit_id,
        "version": result.version,
        "message": result.message,
        "created_at": result.created_at,
        "node_count": result.node_count,
        "edge_count": result.edge_count,
        "status": result.status,
        "storage_backend": result.storage_backend,
        "warning": result.warning,
    }


@app.post("/networks", response_model=NetworkSaveResponse)
def create_or_save_network(request: NetworkSaveVersionRequest):
    return save_network_version(request)


@app.post("/networks/save-version", response_model=NetworkSaveResponse)
def save_network_version(request: NetworkSaveVersionRequest):
    repository = _storage_repository()
    try:
        repository.ensure_available()
        result = repository.save_network(
            network_id=request.network_id,
            name=request.name,
            graph=request.graph.dict(),
            message=request.message,
        )
    except StorageUnavailableError as error:
        _raise_storage_unavailable(error)

    return {
        "network_id": result.network_id,
        "name": result.name,
        "commit_id": result.commit_id,
        "version": result.version,
        "message": result.message,
        "created_at": result.created_at,
        "node_count": result.node_count,
        "edge_count": result.edge_count,
        "status": result.status,
        "storage_backend": result.storage_backend,
        "warning": result.warning,
    }


@app.get("/networks/storage-status", response_model=NetworkStorageStatusResponse)
def get_network_storage_status():
    return _storage_repository().storage_status()


@app.get("/networks", response_model=list[NetworkSummary])
def list_saved_networks():
    repository = _storage_repository()
    try:
        repository.ensure_available()
        return repository.list_networks()
    except StorageUnavailableError as error:
        _raise_storage_unavailable(error)


@app.delete("/networks/{network_id}")
def delete_saved_network(network_id: str):
    repository = _storage_repository()
    try:
        repository.ensure_available()
        repository.delete_network(network_id)
    except StorageUnavailableError as error:
        _raise_storage_unavailable(error)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return {
        "network_id": network_id,
        "status": "deleted",
    }


@app.get("/networks/{network_id}", response_model=SavedNetworkResponse)
def get_saved_network(network_id: str):
    repository = _storage_repository()
    try:
        repository.ensure_available()
        return repository.get_network(network_id)
    except StorageUnavailableError as error:
        _raise_storage_unavailable(error)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/networks/{network_id}/history", response_model=list[NetworkCommitSummary])
def get_saved_network_history(network_id: str):
    repository = _storage_repository()
    try:
        repository.ensure_available()
        return repository.get_history(network_id)
    except StorageUnavailableError as error:
        _raise_storage_unavailable(error)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/networks/{network_id}/versions", response_model=list[NetworkCommitSummary])
def get_saved_network_versions(network_id: str):
    repository = _storage_repository()
    try:
        repository.ensure_available()
        return repository.get_history(network_id)
    except StorageUnavailableError as error:
        _raise_storage_unavailable(error)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/networks/{network_id}/versions", response_model=NetworkSaveResponse)
def save_saved_network_version(network_id: str, request: NetworkSaveVersionRequest):
    return save_network_version(
        NetworkSaveVersionRequest(
            network_id=network_id,
            name=request.name,
            graph=request.graph,
            message=request.message,
        )
    )


@app.get(
    "/networks/{network_id}/versions/{version}",
    response_model=SavedNetworkVersionResponse,
)
def get_saved_network_version(network_id: str, version: int):
    repository = _storage_repository()
    try:
        repository.ensure_available()
        return repository.get_version(network_id, version)
    except StorageUnavailableError as error:
        _raise_storage_unavailable(error)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/networks/{network_id}/restore/{version}", response_model=NetworkSaveResponse)
def restore_saved_network_version(network_id: str, version: int):
    repository = _storage_repository()
    try:
        repository.ensure_available()
        result = repository.restore_version(network_id, version)
    except StorageUnavailableError as error:
        _raise_storage_unavailable(error)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return {
        "network_id": result.network_id,
        "name": result.name,
        "commit_id": result.commit_id,
        "version": result.version,
        "message": result.message,
        "created_at": result.created_at,
        "node_count": result.node_count,
        "edge_count": result.edge_count,
        "status": result.status,
        "storage_backend": result.storage_backend,
        "warning": result.warning,
    }


@app.get("/networks/{network_id}/compare", response_model=NetworkCompareResponse)
def compare_saved_network_versions(
    network_id: str,
    from_version: int = Query(..., ge=1),
    to_version: int = Query(..., ge=1),
):
    repository = _storage_repository()
    try:
        repository.ensure_available()
        return repository.compare_versions(network_id, from_version, to_version)
    except StorageUnavailableError as error:
        _raise_storage_unavailable(error)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


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


@app.get(
    "/analysis/compromised/{node_id}",
    response_model=CompromisedNodeAnalysisResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_compromised_node_analysis(
    node_id: str,
    max_depth: int = Query(DEFAULT_MAX_DEPTH, ge=1, le=20),
    max_paths_per_asset: int = Query(DEFAULT_MAX_PATHS_PER_ASSET, ge=1, le=20),
):
    graph = _load_graph_or_error()

    if node_id not in graph["node_lookup"]:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    finder = LocalJSONPathFinder(graph)
    paths = finder.find_attack_paths(
        compromised_node_id=node_id,
        max_depth=max_depth,
        max_paths_per_asset=max_paths_per_asset,
    )

    recommendations = _load_analysis_recommendations(
        compromised_node_id=node_id,
        max_depth=max_depth,
        max_paths_per_asset=max_paths_per_asset,
    )

    return _build_compromised_node_analysis(
        graph=graph,
        compromised_node_id=node_id,
        paths=paths,
        recommendations=recommendations,
        simulation_type="compromise",
    )


@app.post(
    "/analysis/compromised",
    response_model=CompromisedNodeAnalysisResponse,
    responses={404: {"model": ErrorResponse}},
)
def analyse_compromised_node_from_graph(
    request: CompromisedNodeAnalysisRequest,
    max_depth: int = Query(DEFAULT_MAX_DEPTH, ge=1, le=20),
    max_paths_per_asset: int = Query(DEFAULT_MAX_PATHS_PER_ASSET, ge=1, le=20),
):
    simulation_type = _normalise_simulation_type(request.simulation_type)
    graph_payload = (
        request.graph.model_dump()
        if hasattr(request.graph, "model_dump")
        else request.graph.dict()
    )

    try:
        graph = _normalise_analysis_graph(graph_payload, simulation_type)
    except GraphDataError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if request.node_id not in graph["node_lookup"]:
        raise HTTPException(
            status_code=404,
            detail=f"Node not found: {request.node_id}",
        )

    reasoning = _build_ranked_exposure_reasoning(
        graph=graph,
        source_node_id=request.node_id,
        simulation_type=simulation_type,
        max_depth=max_depth,
    )
    recommendations = _build_reasoned_recommendations(
        reasoning=reasoning,
        graph=graph,
        source_node_id=request.node_id,
        simulation_type=simulation_type,
    )
    analysed_at = datetime.now(UTC).isoformat()
    resolved_graph_hash = request.graph_hash or graph_hash(graph_payload)

    analysis = _build_compromised_node_analysis(
        graph=graph,
        compromised_node_id=request.node_id,
        paths=[],
        recommendations=recommendations,
        simulation_type=simulation_type,
        network_id=request.network_id,
        version=request.version,
        graph_hash=resolved_graph_hash,
        analysed_at=analysed_at,
        reasoning=reasoning,
    )

    _record_version_analysis(
        network_id=request.network_id,
        version=request.version,
        analysis=analysis,
    )

    return analysis


def _load_graph_or_error():
    try:
        return load_configured_graph()
    except GraphDataError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


def _load_analysis_recommendations(
    compromised_node_id: str,
    max_depth: int,
    max_paths_per_asset: int,
):
    try:
        engine = LocalRecommendationEngine()
        response = engine.recommend(
            compromised_node_id=compromised_node_id,
            max_depth=max_depth,
            max_paths_per_asset=max_paths_per_asset,
        )
        return response.get("results", [])
    except Exception:
        return []


def _record_version_analysis(network_id, version, analysis):
    if not network_id or not version:
        return

    analysis_record = {
        "analysed_at": analysis.get("analysed_at"),
        "graph_hash": analysis.get("graph_hash"),
        "node_id": analysis["compromised_node"]["id"],
        "simulation_type": analysis.get("simulation_type"),
        "risk_score": analysis.get("risk_score", 0),
        "risk_level": analysis.get("risk_level", "none"),
        "highlighted_nodes": analysis.get("highlighted_nodes", []),
        "highlighted_edges": analysis.get("highlighted_edges", []),
        "recommendations": analysis.get("recommendations", []),
    }

    def record_in_background():
        try:
            repository = _storage_repository()
            repository.record_analysis(
                network_id=network_id,
                version=int(version),
                analysis=analysis_record,
            )
        except Exception:
            return

    threading.Thread(
        target=record_in_background,
        name="breachpath-analysis-record",
        daemon=True,
    ).start()


def _build_compromised_node_analysis(
    graph,
    compromised_node_id,
    paths,
    recommendations,
    simulation_type="compromise",
    highlighted_nodes=None,
    highlighted_edges=None,
    network_id=None,
    version=None,
    graph_hash=None,
    analysed_at=None,
    reasoning=None,
):
    compromised_node = graph["node_lookup"][compromised_node_id]
    highlighted_nodes = list(reasoning["highlighted_nodes"] if reasoning else highlighted_nodes or [])
    highlighted_edges = list(reasoning["highlighted_edges"] if reasoning else highlighted_edges or [])
    seen_nodes = set()
    seen_edges = set()
    analysis_paths = []

    for node_id in highlighted_nodes:
        seen_nodes.add(node_id)

    for edge in highlighted_edges:
        seen_edges.add((edge["source"], edge["target"]))

    for path in paths:
        for node_id in path["path_node_ids"]:
            if node_id not in seen_nodes:
                highlighted_nodes.append(node_id)
                seen_nodes.add(node_id)

        path_edges = _path_edges(path["path_node_ids"], path.get("edge_relationships", []))
        for edge in path_edges:
            edge_key = (edge["source"], edge["target"])
            if edge_key not in seen_edges:
                highlighted_edges.append(edge)
                seen_edges.add(edge_key)

        analysis_paths.append(
            {
            "target": path["asset_id"],
            "risk_score": path["risk_score"],
            "risk_level": path["risk_level"],
            "nodes": path["path_node_ids"],
            "edges": path_edges,
            "explanation": path["reason"],
            "edge_ids": [],
            "edge_types": [edge.get("relationship") for edge in path_edges if edge.get("relationship")],
            "target_node": path["asset_id"],
            "target_criticality": path.get("criticality"),
            "score": path["risk_score"],
            "severity": path["risk_level"],
            "why_this_path_matters": path["reason"],
            "blocked_or_reduced_by": [],
        }
        )

    if reasoning:
        analysis_paths = reasoning["paths"]
        highlighted_nodes = reasoning["highlighted_nodes"]
        highlighted_edges = reasoning["highlighted_edges"]
        highest_risk_score = reasoning["risk_score"]
        critical_assets = set(reasoning["critical_nodes_reached"])
        followed_edge_types = sorted(
            {
                edge.get("relationship")
                for edge in highlighted_edges
                if edge.get("relationship")
            }
        )
        visual_severity_by_node = reasoning["visual_severity_by_node"]
        visual_severity_by_edge = reasoning["visual_severity_by_edge"]
    else:
        highest_risk_score = max((path["risk_score"] for path in paths), default=0)
        critical_assets = {path["asset_id"] for path in paths}
        followed_edge_types = sorted(
            {
                edge.get("relationship")
                for edge in highlighted_edges
                if edge.get("relationship")
            }
        )
        visual_severity_by_node = _visual_severity_by_node(
            graph=graph,
            highlighted_nodes=highlighted_nodes,
            critical_assets=critical_assets,
            compromised_node_id=compromised_node_id,
            risk_score=highest_risk_score,
        )
        visual_severity_by_edge = _visual_severity_by_edge(
            highlighted_edges=highlighted_edges,
            risk_score=highest_risk_score,
        )

    risk_level = _risk_level_from_score(highest_risk_score)
    top_paths = reasoning["top_paths"] if reasoning else []
    affected_nodes = reasoning["affected_nodes"] if reasoning else [
        node_id for node_id in highlighted_nodes if node_id != compromised_node_id
    ]
    blocked_or_reduced_paths = reasoning["blocked_or_reduced_paths"] if reasoning else []
    low_relevance_nodes = reasoning["low_relevance_nodes"] if reasoning else []
    traversal_explanation = reasoning["traversal_explanation"] if reasoning else None
    summary_text = (
        reasoning["summary_text"]
        if reasoning
        else _simulation_explanation(simulation_type, compromised_node, followed_edge_types)
    )

    return {
        "compromised_node": {
            "id": compromised_node["id"],
            "label": compromised_node["label"],
            "type": compromised_node["type"],
        },
        "source_node": {
            "id": compromised_node["id"],
            "label": compromised_node["label"],
            "type": compromised_node["type"],
        },
        "network_id": network_id,
        "version": version,
        "graph_hash": graph_hash,
        "analysed_at": analysed_at,
        "simulation_type": simulation_type,
        "summary": {
            "affected_node_count": len(affected_nodes),
            "affected_edge_count": len(highlighted_edges),
            "critical_assets_reachable": len(critical_assets),
            "highest_risk_score": highest_risk_score,
            "risk_level": risk_level,
        },
        "summary_text": summary_text,
        "risk_score": highest_risk_score,
        "risk_level": risk_level,
        "highlighted_nodes": highlighted_nodes,
        "highlighted_edges": highlighted_edges,
        "paths": analysis_paths,
        "top_paths": top_paths,
        "affected_nodes": affected_nodes,
        "critical_nodes_reached": sorted(critical_assets),
        "blocked_or_reduced_paths": blocked_or_reduced_paths,
        "low_relevance_nodes": low_relevance_nodes,
        "traversal_explanation": traversal_explanation,
        "recommendations": [
            _format_analysis_recommendation(recommendation, simulation_type)
            for recommendation in recommendations[:5]
        ],
        "explanation": summary_text,
        "followed_edge_types": followed_edge_types,
        "visual_severity_by_node": visual_severity_by_node,
        "visual_severity_by_edge": visual_severity_by_edge,
        "defensive_note": (
            "This is a defensive exposure simulation. It does not perform "
            "exploitation or scanning."
        ),
    }


def _path_edges(path_node_ids, edge_relationships=None):
    edge_relationships = edge_relationships or []
    return [
        {
            "source": path_node_ids[index],
            "target": path_node_ids[index + 1],
            "relationship": edge_relationships[index] if index < len(edge_relationships) else None,
        }
        for index in range(len(path_node_ids) - 1)
    ]


def _risk_level_from_score(score):
    if score <= 0:
        return "none"
    if score <= 39:
        return "low"
    if score <= 69:
        return "medium"
    return "high"


def _normalise_simulation_type(simulation_type):
    normalised = str(simulation_type or "compromise").strip().lower()
    return normalised if normalised in SIMULATION_RULES else "compromise"


def _visual_severity_from_score(score):
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    if score > 0:
        return "low"
    return "low"


def _visual_severity_by_node(
    graph,
    highlighted_nodes,
    critical_assets,
    compromised_node_id,
    risk_score,
):
    severity = {}
    base_severity = _visual_severity_from_score(risk_score)

    for node_id in highlighted_nodes:
        node = graph["node_lookup"].get(node_id, {})
        if node_id == compromised_node_id:
            severity[node_id] = "critical"
        elif node_id in critical_assets or int(node.get("criticality", 0)) >= 90:
            severity[node_id] = "critical"
        elif int(node.get("criticality", 0)) >= 85:
            severity[node_id] = "high"
        else:
            severity[node_id] = base_severity if base_severity != "critical" else "high"

    return severity


def _visual_severity_by_edge(highlighted_edges, risk_score):
    severity = _visual_severity_from_score(risk_score)
    return {
        f"{edge['source']}->{edge['target']}": severity
        for edge in highlighted_edges
    }


def _build_ranked_exposure_reasoning(graph, source_node_id, simulation_type, max_depth):
    rules = SIMULATION_RULES[simulation_type]
    source_node = graph["node_lookup"][source_node_id]
    candidate_paths = []
    blocked_paths = []
    low_relevance_nodes = set()
    reachable_nodes = {source_node_id}
    reachable_edges = {}
    followed_edge_decisions = {}
    blocked_edge_decisions = {}
    queue = [(source_node_id, [source_node_id], [])]
    explored_signatures = set()

    while queue:
        current_node_id, path_nodes, path_edges = queue.pop(0)
        if len(path_edges) >= max_depth:
            continue

        current_node = graph["node_lookup"].get(current_node_id, {})
        for edge in graph["adjacency"].get(current_node_id, []):
            target_node_id = edge["target"]
            if target_node_id in path_nodes:
                continue

            target_node = graph["node_lookup"].get(target_node_id)
            if not target_node:
                continue

            next_nodes = path_nodes + [target_node_id]
            next_edges = path_edges + [edge]
            signature = tuple(next_nodes)
            if signature in explored_signatures:
                continue
            explored_signatures.add(signature)

            blocker_reason = _edge_blocker_reason(
                edge,
                current_node,
                target_node,
                simulation_type,
            )
            if blocker_reason:
                blocked_paths.append(
                    _build_blocked_path(
                        path_id=f"blocked-{len(blocked_paths) + 1}",
                        path_nodes=next_nodes,
                        path_edges=next_edges,
                        reason=blocker_reason,
                    )
                )
                blocked_edge_decisions[_edge_signature(edge)] = _edge_decision(
                    edge=edge,
                    graph=graph,
                    decision="blocked_or_reduced",
                    reason=blocker_reason,
                )
                continue

            scored_path = _score_ranked_path(
                graph=graph,
                path_id=f"path-candidate-{len(candidate_paths) + 1}",
                path_nodes=next_nodes,
                path_edges=next_edges,
                simulation_type=simulation_type,
            )
            candidate_paths.append(scored_path)
            reachable_nodes.add(target_node_id)
            reachable_edges[_edge_signature(edge)] = _edge_ref(edge)
            followed_edge_decisions[_edge_signature(edge)] = _edge_decision(
                edge=edge,
                graph=graph,
                decision="followed",
                reason=(
                    f"{edge['relationship']} is relevant for {simulation_type}; "
                    f"current path score is {scored_path['score']}."
                ),
                score=scored_path["score"],
            )

            if scored_path["score"] < rules["threshold"]:
                low_relevance_nodes.add(target_node_id)

            if len(next_edges) < max_depth:
                queue.append((target_node_id, next_nodes, next_edges))

    ranked_paths = _select_top_ranked_paths(candidate_paths, rules["threshold"], rules["max_paths"])
    for index, path in enumerate(ranked_paths, start=1):
        path["path_id"] = f"path-{index}"
    ranked_path_signatures = {tuple(path["nodes"]) for path in ranked_paths}

    highlighted_nodes = [source_node_id]
    highlighted_edges = []
    seen_highlighted_nodes = {source_node_id}
    seen_highlighted_edges = set()
    critical_nodes_reached = set()
    visual_severity_by_node = {source_node_id: "critical"}
    visual_severity_by_edge = {}

    for path in ranked_paths:
        path_severity = path["severity"]
        for node_id in path["nodes"]:
            if node_id not in seen_highlighted_nodes:
                highlighted_nodes.append(node_id)
                seen_highlighted_nodes.add(node_id)

            node = graph["node_lookup"].get(node_id, {})
            if node_id != source_node_id and _is_critical_for_simulation(node, simulation_type):
                critical_nodes_reached.add(node_id)

            existing = visual_severity_by_node.get(node_id)
            visual_severity_by_node[node_id] = _max_visual_severity(
                existing,
                "critical" if node_id in critical_nodes_reached else path_severity,
            )

        for edge_ref in path["edge_refs"]:
            edge_key = (edge_ref["source"], edge_ref["target"], edge_ref.get("id"))
            if edge_key not in seen_highlighted_edges:
                highlighted_edges.append(edge_ref)
                seen_highlighted_edges.add(edge_key)
            visual_severity_by_edge[f"{edge_ref['source']}->{edge_ref['target']}"] = (
                _max_visual_severity(
                    visual_severity_by_edge.get(f"{edge_ref['source']}->{edge_ref['target']}"),
                    path_severity,
                )
            )

    affected_nodes = [
        node_id for node_id in highlighted_nodes if node_id != source_node_id
    ]
    risk_score = max((path["score"] for path in ranked_paths), default=0)
    risk_level = _risk_level_from_score(risk_score)
    blocked_or_reduced_paths = blocked_paths[:5]
    low_relevance_nodes = sorted(
        node_id
        for node_id in low_relevance_nodes
        if node_id not in set(highlighted_nodes)
    )
    ranked_but_not_highlighted_paths = _ranked_but_not_highlighted_paths(
        candidate_paths=candidate_paths,
        ranked_path_signatures=ranked_path_signatures,
        threshold=rules["threshold"],
        max_paths=rules["max_paths"],
    )
    skipped_edge_decisions = _build_skipped_edge_decisions(
        graph=graph,
        source_node_id=source_node_id,
        simulation_type=simulation_type,
        reachable_nodes=reachable_nodes,
        followed_edge_signatures=set(followed_edge_decisions),
        blocked_edge_signatures=set(blocked_edge_decisions),
    )
    all_skipped_edges = [
        *blocked_edge_decisions.values(),
        *skipped_edge_decisions,
    ]
    connected_but_not_highlighted = _connected_but_not_highlighted(
        graph=graph,
        highlighted_nodes=set(highlighted_nodes),
        low_relevance_nodes=low_relevance_nodes,
        skipped_edges=all_skipped_edges,
        ranked_but_not_highlighted_paths=ranked_but_not_highlighted_paths,
    )
    traversal_explanation = {
        "source_node": source_node_id,
        "simulation_type": simulation_type,
        "highlight_threshold": rules["threshold"],
        "max_highlighted_paths": rules["max_paths"],
        "followed_edges": list(followed_edge_decisions.values()),
        "skipped_edges": all_skipped_edges,
        "ranked_but_not_highlighted_paths": ranked_but_not_highlighted_paths,
        "connected_but_not_highlighted": connected_but_not_highlighted,
        "reachable_nodes": sorted(reachable_nodes),
        "reachable_edges": list(reachable_edges.values()),
    }

    if ranked_paths:
        summary_text = (
            f"{rules['label']} simulation from {source_node['label']} found "
            f"{len(ranked_paths)} ranked exposure path(s). Highlighting is limited to "
            "the highest-risk paths, directly affected critical nodes, and the source node."
        )
    elif blocked_or_reduced_paths:
        summary_text = (
            f"{rules['label']} simulation from {source_node['label']} did not find a "
            "fully exposed critical path because one or more routes were blocked or reduced."
        )
    else:
        summary_text = (
            f"{rules['label']} simulation from {source_node['label']} did not find a "
            "high-relevance exposure path for this simulation type."
        )

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "summary_text": summary_text,
        "paths": [_ranked_path_to_legacy_path(path) for path in ranked_paths],
        "top_paths": ranked_paths,
        "highlighted_nodes": highlighted_nodes,
        "highlighted_edges": highlighted_edges,
        "affected_nodes": affected_nodes,
        "critical_nodes_reached": sorted(critical_nodes_reached),
        "blocked_or_reduced_paths": blocked_or_reduced_paths,
        "low_relevance_nodes": low_relevance_nodes,
        "traversal_explanation": traversal_explanation,
        "visual_severity_by_node": visual_severity_by_node,
        "visual_severity_by_edge": visual_severity_by_edge,
    }


def _score_ranked_path(graph, path_id, path_nodes, path_edges, simulation_type):
    target_node = graph["node_lookup"][path_nodes[-1]]
    target_criticality = int(target_node.get("criticality", 0))
    edge_weights = [int(edge.get("risk_weight", 55)) for edge in path_edges]
    edge_types = [edge["relationship"] for edge in path_edges]
    dangerous_edges = SIMULATION_RULES[simulation_type]["dangerous_edges"]
    average_edge_risk = sum(edge_weights) / max(len(edge_weights), 1)
    dangerous_edge_bonus = sum(12 for edge_type in edge_types if edge_type in dangerous_edges)
    dangerous_edge_bonus += sum(6 for edge_type in edge_types if edge_type == "internet_exposes")
    relevance_bonus = _simulation_relevance_bonus(target_node, simulation_type)
    sensitive_data_bonus = _sensitive_data_bonus(target_node, simulation_type)
    privilege_bonus = _privilege_bonus(graph, path_nodes, edge_types, simulation_type)
    internet_bonus = 12 if "internet_exposes" in edge_types else 0
    hop_penalty = max(0, len(path_edges) - 1) * 8
    low_noise_penalty = _low_noise_penalty(target_node, simulation_type)

    raw_score = (
        target_criticality * 0.55
        + average_edge_risk * 0.25
        + dangerous_edge_bonus
        + relevance_bonus
        + sensitive_data_bonus
        + privilege_bonus
        + internet_bonus
        - hop_penalty
        - low_noise_penalty
    )
    score = _clamp_score(round(raw_score))
    severity = _risk_level_from_score(score)

    return {
        "path_id": path_id,
        "nodes": path_nodes,
        "edges": [edge["id"] for edge in path_edges],
        "edge_refs": [_edge_ref(edge) for edge in path_edges],
        "edge_types": edge_types,
        "target_node": target_node["id"],
        "target_criticality": target_criticality,
        "score": score,
        "severity": severity,
        "why_this_path_matters": _path_reason(
            target_node=target_node,
            edge_types=edge_types,
            simulation_type=simulation_type,
            score=score,
        ),
        "blocked_or_reduced_by": [],
    }


def _select_top_ranked_paths(candidate_paths, threshold, max_paths):
    useful_paths = [
        path
        for path in candidate_paths
        if path["score"] >= threshold
    ]
    useful_paths.sort(key=lambda path: (-path["score"], len(path["nodes"]), path["target_node"]))

    selected_paths = []
    best_score_by_target = {}
    for path in useful_paths:
        target = path["target_node"]
        if target in best_score_by_target and path["score"] <= best_score_by_target[target]:
            continue

        selected_paths.append(path)
        best_score_by_target[target] = path["score"]

        if len(selected_paths) >= max_paths:
            break

    return selected_paths


def _ranked_path_to_legacy_path(path):
    return {
        "path_id": path["path_id"],
        "target": path["target_node"],
        "risk_score": path["score"],
        "risk_level": path["severity"],
        "nodes": path["nodes"],
        "edges": path["edge_refs"],
        "explanation": path["why_this_path_matters"],
        "edge_ids": path["edges"],
        "edge_types": path["edge_types"],
        "target_node": path["target_node"],
        "target_criticality": path["target_criticality"],
        "score": path["score"],
        "severity": path["severity"],
        "why_this_path_matters": path["why_this_path_matters"],
        "blocked_or_reduced_by": path["blocked_or_reduced_by"],
    }


def _edge_ref(edge):
    return {
        "id": edge.get("id"),
        "source": edge["source"],
        "target": edge["target"],
        "relationship": edge.get("relationship"),
        "blocked_or_reduced_by": [],
    }


def _edge_signature(edge):
    return (edge.get("id"), edge.get("source"), edge.get("target"))


def _edge_decision(edge, graph, decision, reason, score=None, from_node=None, to_node=None):
    source = from_node or edge["source"]
    target = to_node or edge["target"]
    return {
        "edge_id": edge.get("id"),
        "from": source,
        "to": target,
        "edge_type": edge.get("relationship"),
        "direction": edge.get("direction", "directional"),
        "decision": decision,
        "reason": reason,
        "from_label": _node_label(graph, source),
        "to_label": _node_label(graph, target),
        "score": score,
    }


def _ranked_but_not_highlighted_paths(
    candidate_paths,
    ranked_path_signatures,
    threshold,
    max_paths,
):
    ranked_but_not_highlighted = []
    selected_targets = {
        path[-1]
        for path in ranked_path_signatures
        if path
    }

    for path in sorted(candidate_paths, key=lambda item: (-item["score"], len(item["nodes"]))):
        if tuple(path["nodes"]) in ranked_path_signatures:
            continue

        if path["score"] < threshold:
            reason = f"path score {path['score']} is below highlight threshold {threshold}"
        elif path["target_node"] in selected_targets:
            reason = "a higher-ranked path to this same target was already highlighted"
        else:
            reason = f"path was reachable but outside the top {max_paths} highlighted paths"

        ranked_but_not_highlighted.append(
            {
                "nodes": path["nodes"],
                "edges": path["edges"],
                "edge_types": path["edge_types"],
                "score": path["score"],
                "reason": reason,
            }
        )

    return ranked_but_not_highlighted[:10]


def _build_skipped_edge_decisions(
    graph,
    source_node_id,
    simulation_type,
    reachable_nodes,
    followed_edge_signatures,
    blocked_edge_signatures,
):
    rules = SIMULATION_RULES[simulation_type]
    skipped = []
    seen = set()

    for edge in graph.get("all_edges", graph.get("edges", [])):
        edge_signature = _edge_signature(edge)
        if edge_signature in followed_edge_signatures or edge_signature in blocked_edge_signatures:
            continue

        relationship = edge["relationship"]
        edge_is_relevant = relationship in rules["follow"]
        edge_is_bidirectional = edge.get("direction") == "bidirectional"

        if edge["source"] in reachable_nodes:
            if not edge_is_relevant:
                decision_key = (edge.get("id"), edge["source"], edge["target"], "type")
                if decision_key not in seen:
                    skipped.append(
                        _edge_decision(
                            edge=edge,
                            graph=graph,
                            decision="skipped",
                            reason=(
                                f"{relationship} is not followed by {simulation_type} "
                                "analysis."
                            ),
                        )
                    )
                    seen.add(decision_key)
            continue

        if edge["target"] in reachable_nodes and not edge_is_bidirectional:
            decision_key = (edge.get("id"), edge["target"], edge["source"], "direction")
            if decision_key in seen:
                continue

            if edge_is_relevant:
                reason = (
                    f"{relationship} is directional from {edge['source']} to {edge['target']}; "
                    f"analysis from {source_node_id} would need to go against that direction."
                )
            else:
                reason = (
                    f"{relationship} is not followed by {simulation_type}, and this edge is "
                    f"directional from {edge['source']} to {edge['target']}."
                )

            skipped.append(
                _edge_decision(
                    edge=edge,
                    graph=graph,
                    decision="skipped",
                    reason=reason,
                    from_node=edge["target"],
                    to_node=edge["source"],
                )
            )
            seen.add(decision_key)

    return skipped[:25]


def _connected_but_not_highlighted(
    graph,
    highlighted_nodes,
    low_relevance_nodes,
    skipped_edges,
    ranked_but_not_highlighted_paths,
):
    connected = {}

    for node_id in low_relevance_nodes:
        connected[node_id] = {
            "node_id": node_id,
            "label": _node_label(graph, node_id),
            "reason": "reachable, but path score was below the highlight threshold",
            "edge_id": None,
            "edge_type": None,
        }

    for path in ranked_but_not_highlighted_paths:
        if not path["nodes"]:
            continue
        node_id = path["nodes"][-1]
        if node_id in highlighted_nodes:
            continue
        connected[node_id] = {
            "node_id": node_id,
            "label": _node_label(graph, node_id),
            "reason": path["reason"],
            "edge_id": path["edges"][-1] if path["edges"] else None,
            "edge_type": path["edge_types"][-1] if path["edge_types"] else None,
        }

    for edge in skipped_edges:
        node_id = edge["to"]
        if node_id in highlighted_nodes:
            continue
        connected[node_id] = {
            "node_id": node_id,
            "label": _node_label(graph, node_id),
            "reason": edge["reason"],
            "edge_id": edge["edge_id"],
            "edge_type": edge["edge_type"],
        }

    return list(connected.values())[:25]


def _build_blocked_path(path_id, path_nodes, path_edges, reason):
    return {
        "path_id": path_id,
        "nodes": path_nodes,
        "edges": [edge["id"] for edge in path_edges],
        "edge_refs": [
            {
                **_edge_ref(edge),
                "blocked_or_reduced_by": [reason],
            }
            for edge in path_edges
        ],
        "edge_types": [edge["relationship"] for edge in path_edges],
        "target_node": path_nodes[-1] if path_nodes else None,
        "reason": reason,
        "severity": "reduced",
    }


def _edge_blocker_reason(edge, current_node, target_node, simulation_type):
    blocked_by = edge.get("blocked_by")
    if blocked_by:
        return f"Path blocked by {blocked_by}."

    if simulation_type == "offline":
        return None

    allowed_by_firewall = edge.get("allowed_by_firewall")
    if allowed_by_firewall is False:
        return "Path reduced or blocked because the firewall rule does not allow this edge."

    if _is_protection_node(current_node) and allowed_by_firewall is not True:
        return (
            f"Path reduced or blocked by {current_node['label']}. "
            "No explicit allowed_by_firewall=true edge was present."
        )

    if _is_protection_node(target_node) and edge.get("relationship") == "internet_exposes":
        return (
            f"Path reduced or blocked by {target_node['label']}. "
            "The protection node is treated as a control, not a free connector."
        )

    return None


def _is_protection_node(node):
    return _node_matches(
        node,
        "firewall",
        "segmented",
        "segmentation",
        "security_tool",
        "security",
        "waf",
    )


def _simulation_relevance_bonus(node, simulation_type):
    text = _node_text(node)
    keywords = SIMULATION_RULES[simulation_type]["priority_keywords"]
    bonus = 0

    if any(keyword in text for keyword in keywords):
        bonus += 22

    if int(node.get("criticality", 0)) >= 90:
        bonus += 14
    elif int(node.get("criticality", 0)) >= 75:
        bonus += 8

    if simulation_type == "offline" and _node_matches(
        node,
        "router",
        "gateway",
        "vpn",
        "server",
        "monitoring",
        "backup",
        "database",
        "critical",
    ):
        bonus += 18

    if simulation_type == "data_leak" and _is_sensitive_data_node(node):
        bonus += 18

    if simulation_type == "lateral_movement" and _is_privilege_node(node):
        bonus += 22

    return bonus


def _sensitive_data_bonus(node, simulation_type):
    if simulation_type not in {"compromise", "spyware", "data_leak", "lateral_movement"}:
        return 0
    return 18 if _is_sensitive_data_node(node) else 0


def _privilege_bonus(graph, path_nodes, edge_types, simulation_type):
    if simulation_type not in {"compromise", "spyware", "data_leak", "lateral_movement"}:
        return 0

    bonus = 0
    if any(edge_type in {"administers", "controls", "stores_credentials_for"} for edge_type in edge_types):
        bonus += 20

    if any(_is_privilege_node(graph["node_lookup"].get(node_id, {})) for node_id in path_nodes):
        bonus += 16

    return bonus


def _low_noise_penalty(node, simulation_type):
    if _is_sensitive_data_node(node) or _is_privilege_node(node):
        return 0
    if int(node.get("criticality", 0)) >= 75:
        return 0
    if _node_matches(node, "printer", "camera", "iot", "smart", "tv"):
        return 35 if simulation_type in {"data_leak", "lateral_movement"} else 24
    if simulation_type == "data_leak":
        return 28
    if simulation_type == "lateral_movement":
        return 18
    return 0


def _is_sensitive_data_node(node):
    return _node_matches(
        node,
        "nas",
        "file",
        "database",
        "db",
        "backup",
        "cloud",
        "storage",
        "share",
        "credential",
        "secret",
        "sensitive",
        "admin",
        "account",
    )


def _is_privilege_node(node):
    return _node_matches(
        node,
        "admin",
        "domain_controller",
        "domain controller",
        "identity",
        "credential",
        "root",
        "privileged",
        "control",
    )


def _is_critical_for_simulation(node, simulation_type):
    if int(node.get("criticality", 0)) >= 85:
        return True
    if node.get("type") in {"critical_asset", "database"}:
        return True
    if simulation_type in {"data_leak", "spyware"} and _is_sensitive_data_node(node):
        return True
    if simulation_type in {"compromise", "lateral_movement"} and _is_privilege_node(node):
        return True
    return False


def _path_reason(target_node, edge_types, simulation_type, score):
    label = target_node["label"]
    target_text = _node_text(target_node)
    edge_text = ", ".join(dict.fromkeys(edge_types))

    if simulation_type == "offline":
        return (
            f"This path matters because {label} may depend on the selected node "
            f"through {edge_text}. Score {score} reflects availability impact."
        )

    if simulation_type == "data_leak":
        return (
            f"This path matters because {label} looks like sensitive data, identity, "
            f"or storage reached through {edge_text}."
        )

    if simulation_type == "spyware":
        return (
            f"This path matters because spyware could observe or expose {label} "
            f"through {edge_text}."
        )

    if simulation_type == "lateral_movement":
        return (
            f"This path matters because it moves toward privilege or a critical system: "
            f"{label} via {edge_text}."
        )

    if "admin" in target_text or "credential" in target_text:
        return f"This path matters because it reaches privilege or stored credentials via {edge_text}."
    if _is_sensitive_data_node(target_node):
        return f"This path matters because it reaches sensitive storage or data: {label}."
    return f"This path matters because it reaches a high-impact node, {label}, via {edge_text}."


def _clamp_score(score):
    return max(0, min(100, int(score)))


def _max_visual_severity(current, candidate):
    if not current:
        return candidate

    levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    return candidate if levels.get(candidate, 0) > levels.get(current, 0) else current


def _node_text(node):
    return " ".join(
        str(node.get(key, ""))
        for key in ("id", "label", "type", "node_type", "zone", "description")
    ).lower()


def _node_matches(node, *needles):
    text = _node_text(node)
    return any(needle in text for needle in needles)


def _node_label(graph, node_id):
    node = graph["node_lookup"].get(node_id, {})
    return node.get("label") or node_id


def _format_path_labels(graph, node_ids):
    return " -> ".join(_node_label(graph, node_id) for node_id in node_ids)


def _format_analysis_recommendation(recommendation, simulation_type):
    action_type = recommendation.get("action_type") or recommendation.get("type") or "review_access"
    priority = (
        recommendation.get("recommendation_level")
        or recommendation.get("priority")
        or recommendation.get("severity")
        or "useful"
    )
    reason = recommendation.get("reason") or recommendation.get("explanation") or ""
    estimated_reduction = recommendation.get(
        "risk_reduction",
        recommendation.get("estimated_risk_reduction", 25),
    )

    return {
        "title": recommendation["title"],
        "type": action_type,
        "priority": priority,
        "estimated_risk_reduction": estimated_reduction,
        "explanation": reason,
        "severity": recommendation.get("severity") or priority,
        "reason": reason,
        "triggered_by_path": recommendation.get("triggered_by_path", []),
        "affected_nodes": recommendation.get("affected_nodes", []),
        "relevant_edge_types": recommendation.get("relevant_edge_types", []),
        "simulation_type": recommendation.get("simulation_type", simulation_type),
        "what_it_fixes": recommendation.get("what_it_fixes"),
        "expected_effect": recommendation.get("expected_effect"),
        "confidence": recommendation.get("confidence", "medium"),
        "action_steps": recommendation.get("action_steps", []),
    }


def _simulation_explanation(simulation_type, compromised_node, followed_edge_types):
    label = SIMULATION_RULES[simulation_type]["label"]
    followed = ", ".join(followed_edge_types) if followed_edge_types else "no relationships"
    return (
        f"{label} simulation for {compromised_node['label']}. "
        f"BreachPath followed {followed} to estimate defensive exposure. "
        "This is a safe model only; it does not scan, exploit, or execute payloads."
    )


def _normalise_analysis_graph(graph_payload, simulation_type="compromise"):
    rules = SIMULATION_RULES[_normalise_simulation_type(simulation_type)]
    nodes = [_normalise_analysis_node(node) for node in graph_payload.get("nodes", [])]
    node_ids = {node["id"] for node in nodes}
    all_edges = []
    edges = []

    for edge in graph_payload.get("edges", []):
        normalised_edge = _normalise_analysis_edge(edge)
        if normalised_edge["source"] not in node_ids or normalised_edge["target"] not in node_ids:
            continue
        all_edges.append(normalised_edge)
        if normalised_edge["relationship"] not in rules["follow"]:
            continue
        edges.append(normalised_edge)

        if (
            normalised_edge.get("direction") == "bidirectional"
            or normalised_edge["relationship"] in rules["bidirectional"]
            or normalised_edge["relationship"] in rules.get("reverse_for_impact", set())
        ):
            reverse_edge = {
                **normalised_edge,
                "id": f"{normalised_edge['id']}-reverse",
                "source": normalised_edge["target"],
                "target": normalised_edge["source"],
                "description": f"Reverse defensive reachability for {normalised_edge['id']}.",
            }
            edges.append(reverse_edge)

    normalised_graph = {
        "metadata": graph_payload.get("metadata", {}),
        "nodes": nodes,
        "edges": edges,
        "all_edges": all_edges,
    }
    validate_graph_data(normalised_graph)

    return {
        **normalised_graph,
        "node_lookup": build_node_lookup(nodes),
        "adjacency": build_adjacency_list(nodes, edges),
    }


def _normalise_analysis_node(node):
    node_id = str(node.get("id") or "").strip()
    label = str(node.get("label") or node_id or "Unnamed node")
    node_type = str(node.get("type") or node.get("node_type") or "workstation")
    normalised_node_type = node_type.strip().lower().replace(" ", "_")
    criticality = _normalise_criticality(node.get("criticality"))

    return {
        "id": node_id,
        "label": label,
        "node_type": normalised_node_type,
        "type": _normalise_node_type(node_type, criticality),
        "zone": str(node.get("zone") or "internal"),
        "criticality": criticality,
        "description": str(node.get("description") or node.get("notes") or ""),
    }


def _normalise_node_type(node_type, criticality):
    normalised = node_type.strip().lower().replace(" ", "_")

    if normalised in {"admin_account", "cloud_account", "account"}:
        return "identity"
    if normalised in {"database", "logistics_db"}:
        return "database"
    if normalised in {"router", "vpn_gateway", "firewall", "internet"}:
        return "network_device"
    if normalised in {"monitoring_system"}:
        return "security_tool"
    if criticality >= 90 or normalised in {
        "critical_service",
        "operations_server",
        "domain_controller",
    }:
        return "critical_asset"
    if normalised in {"file_server", "backup_server", "nas_home_server", "server"}:
        return "server"
    return "workstation"


def _normalise_criticality(value):
    if value is None:
        return 60
    if isinstance(value, int):
        return max(1, min(100, value))

    text = str(value).strip().lower()
    if text.isdigit():
        return max(1, min(100, int(text)))
    return CRITICALITY_SCORES.get(text, 60)


def _normalise_analysis_edge(edge):
    source = str(edge.get("source") or "").strip()
    target = str(edge.get("target") or "").strip()
    relationship = str(
        edge.get("relationship") or edge.get("edge_type") or "can_access"
    ).strip().lower().replace(" ", "_")
    relationship = LEGACY_RELATIONSHIP_ALIASES.get(relationship, relationship)
    direction = str(edge.get("direction") or "").strip().lower()
    risk_can_spread_both_ways = _normalise_boolean(
        edge.get("risk_can_spread_both_ways")
    )
    risk_weight = _normalise_edge_risk(edge.get("risk_weight"))

    if direction in {"both", "undirected", "two_way", "two-way"}:
        direction = "bidirectional"
    elif direction in {"source_to_target", "source-to-target", "directional"}:
        direction = "directional"

    if relationship == "same_network":
        direction = "bidirectional"
    elif not direction:
        direction = "directional"

    return {
        "id": str(edge.get("id") or f"{source}-{relationship}-{target}"),
        "source": source,
        "target": target,
        "relationship": relationship,
        "risk_weight": risk_weight,
        "description": str(edge.get("description") or edge.get("notes") or ""),
        "direction": direction,
        "risk_can_spread_both_ways": risk_can_spread_both_ways,
        "requires_condition": edge.get("requires_condition"),
        "blocked_by": edge.get("blocked_by"),
        "allowed_by_firewall": _normalise_optional_boolean(edge.get("allowed_by_firewall")),
    }


def _normalise_optional_boolean(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _normalise_boolean(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _normalise_edge_risk(value):
    if value is None:
        return 55
    if isinstance(value, int):
        return max(1, min(100, value))

    text = str(value).strip().lower()
    if text.isdigit():
        return max(1, min(100, int(text)))
    return EDGE_RISK_SCORES.get(text, 55)


def _build_reasoned_recommendations(reasoning, graph, source_node_id, simulation_type):
    recommendations = []
    source_label = _node_label(graph, source_node_id)

    def add_recommendation(
        title,
        action_type,
        severity,
        reason,
        path,
        what_it_fixes,
        expected_effect,
        confidence="high",
        risk_reduction=None,
        action_steps=None,
    ):
        key = (
            title,
            tuple(path.get("nodes", [])) if path else (),
            simulation_type,
        )
        if any(recommendation["_dedupe_key"] == key for recommendation in recommendations):
            return

        path_nodes = path.get("nodes", []) if path else []
        edge_types = path.get("edge_types", []) if path else []
        score = path.get("score", 40) if path else 30
        recommendations.append(
            {
                "_dedupe_key": key,
                "title": title,
                "action_type": action_type,
                "recommendation_level": severity,
                "severity": severity,
                "risk_reduction": risk_reduction if risk_reduction is not None else min(90, score),
                "reason": reason,
                "triggered_by_path": path_nodes,
                "affected_nodes": [
                    node_id for node_id in path_nodes if node_id != source_node_id
                ],
                "relevant_edge_types": sorted(dict.fromkeys(edge_types)),
                "simulation_type": simulation_type,
                "what_it_fixes": what_it_fixes,
                "expected_effect": expected_effect,
                "confidence": confidence,
                "action_steps": action_steps or [],
            }
        )

    for path in reasoning["top_paths"]:
        edge_types = set(path["edge_types"])
        path_labels = _format_path_labels(graph, path["nodes"])
        target_node = graph["node_lookup"].get(path["target_node"], {})
        target_label = _node_label(graph, path["target_node"])
        severity = path["severity"] if path["severity"] != "low" else "medium"
        reaches_sensitive = any(
            _is_sensitive_data_node(graph["node_lookup"].get(node_id, {}))
            for node_id in path["nodes"]
        )
        reaches_privilege = any(
            _is_privilege_node(graph["node_lookup"].get(node_id, {}))
            for node_id in path["nodes"]
        )

        if simulation_type == "offline":
            add_recommendation(
                title=f"Add resilience for {target_label}",
                action_type="improve_resilience",
                severity=severity,
                reason=(
                    f"{target_label} is on an availability path from {source_label}: "
                    f"{path_labels}."
                ),
                path=path,
                what_it_fixes="Reduces dependency on one device or route staying online.",
                expected_effect="Keeps services usable if this node goes offline.",
                action_steps=[
                    "Document the dependency.",
                    "Add backup routing, redundancy, or a manual fallback.",
                ],
            )
            if edge_types & {"backs_up", "monitors"}:
                add_recommendation(
                    title="Check backup and monitoring continuity",
                    action_type="improve_monitoring",
                    severity="medium",
                    reason=(
                        f"The offline simulation followed backup or monitoring edges on "
                        f"{path_labels}."
                    ),
                    path=path,
                    what_it_fixes="Confirms monitoring and backup coverage survive this outage.",
                    expected_effect="Improves detection and recovery during availability incidents.",
                    confidence="medium",
                )
            continue

        if simulation_type == "data_leak":
            if reaches_sensitive:
                add_recommendation(
                    title=f"Limit data access to {target_label}",
                    action_type="review_access",
                    severity=severity,
                    reason=(
                        f"The data leak simulation reaches sensitive storage, identity, "
                        f"or account data through {path_labels}."
                    ),
                    path=path,
                    what_it_fixes="Reduces what information can be exposed from the selected node.",
                    expected_effect="Breaks or narrows the data exposure path.",
                    action_steps=[
                        "Review share, database, account, or backup permissions.",
                        "Remove access that is not needed for normal work.",
                    ],
                )
            if "stores_credentials_for" in edge_types or reaches_privilege:
                add_recommendation(
                    title="Rotate exposed credentials on this path",
                    action_type="remove_stored_credentials",
                    severity=severity,
                    reason=(
                        f"The risky data path includes credentials or an admin/account node: "
                        f"{path_labels}."
                    ),
                    path=path,
                    what_it_fixes="Stops leaked stored credentials from remaining useful.",
                    expected_effect="Reduces privilege and account exposure after a leak.",
                )
            continue

        if simulation_type == "spyware":
            if reaches_sensitive:
                add_recommendation(
                    title=f"Reduce what {source_label} can observe",
                    action_type="isolate_node",
                    severity=severity,
                    reason=(
                        f"Spyware on {source_label} could observe or access sensitive systems "
                        f"through {path_labels}."
                    ),
                    path=path,
                    what_it_fixes="Limits nearby data, accounts, or devices visible to spyware.",
                    expected_effect="Shrinks the observation and data-exposure surface.",
                )
            if "stores_credentials_for" in edge_types:
                add_recommendation(
                    title="Remove credentials visible to the spyware path",
                    action_type="remove_stored_credentials",
                    severity=severity,
                    reason=f"The spyware path includes stored credentials: {path_labels}.",
                    path=path,
                    what_it_fixes="Prevents captured local credentials from extending exposure.",
                    expected_effect="Reduces follow-on account and data access.",
                )
            continue

        if simulation_type == "lateral_movement":
            if reaches_privilege or edge_types & {"administers", "controls", "stores_credentials_for"}:
                add_recommendation(
                    title="Reduce admin movement on this path",
                    action_type="restrict_admin_access",
                    severity=severity,
                    reason=(
                        f"The lateral movement simulation reaches privilege or control via "
                        f"{path_labels}."
                    ),
                    path=path,
                    what_it_fixes="Prevents one device from becoming a stepping stone to privilege.",
                    expected_effect="Breaks or narrows the privilege escalation path.",
                    action_steps=[
                        "Remove unnecessary admin rights.",
                        "Use separate admin accounts and just-in-time access where possible.",
                    ],
                )
            if "stores_credentials_for" in edge_types:
                add_recommendation(
                    title="Remove stored credentials from the movement path",
                    action_type="remove_stored_credentials",
                    severity=severity,
                    reason=f"The path uses stored credentials: {path_labels}.",
                    path=path,
                    what_it_fixes="Stops stored secrets from converting access into privilege.",
                    expected_effect="Reduces the chance that lateral movement reaches admin systems.",
                )
            if _path_involves_router_admin(graph, path):
                add_recommendation(
                    title="Harden router or firewall management access",
                    action_type="improve_router_security",
                    severity=severity,
                    reason=(
                        f"The path involves network-device management or control: {path_labels}."
                    ),
                    path=path,
                    what_it_fixes="Protects management access only when it appears on the risky path.",
                    expected_effect="Reduces the chance that a router/firewall becomes a control point.",
                )
            continue

        if edge_types & {"same_network", "can_access"} and reaches_sensitive:
            add_recommendation(
                title=f"Segment {source_label} away from {target_label}",
                action_type="segment_network",
                severity=severity,
                reason=(
                    f"The selected node can reach a sensitive or critical system through "
                    f"{path_labels}."
                ),
                path=path,
                what_it_fixes="Reduces exposure from a lower-trust source to high-impact systems.",
                expected_effect="Breaks or reduces this exposure path.",
                action_steps=[
                    "Move low-trust devices to a guest or isolated network.",
                    "Allow only required traffic to sensitive systems.",
                ],
            )

        if "stores_credentials_for" in edge_types or reaches_privilege:
            add_recommendation(
                title="Review and rotate credentials on this path",
                action_type="remove_stored_credentials",
                severity=severity,
                reason=(
                    f"The compromise path includes stored credentials or privileged identity: "
                    f"{path_labels}."
                ),
                path=path,
                what_it_fixes="Prevents stored credentials from expanding blast radius.",
                expected_effect="Reduces privilege exposure from the compromised source.",
            )

        if edge_types & {"administers", "controls"}:
            add_recommendation(
                title="Restrict control relationships on this path",
                action_type="restrict_admin_access",
                severity=severity,
                reason=f"The path includes admin/control relationships: {path_labels}.",
                path=path,
                what_it_fixes="Limits direct control over high-impact systems.",
                expected_effect="Narrows what a compromised node can control.",
            )

        if _path_involves_router_admin(graph, path):
            add_recommendation(
                title="Harden router or firewall management access",
                action_type="improve_router_security",
                severity=severity,
                reason=(
                    f"The path involves network-device administration, stored credentials, "
                    f"or exposed management: {path_labels}."
                ),
                path=path,
                what_it_fixes="Protects router/firewall administration only when that path is relevant.",
                expected_effect="Reduces management-plane exposure.",
            )

        if "internet_exposes" in edge_types or "routes_through" in edge_types:
            add_recommendation(
                title="Review firewall rules on this exposure path",
                action_type="segment_network",
                severity=severity,
                reason=f"The path crosses routing or internet-exposure edges: {path_labels}.",
                path=path,
                what_it_fixes="Reduces unnecessary route or public-surface exposure.",
                expected_effect="Limits which systems can be reached through the route.",
                confidence="medium",
            )

    for blocked_path in reasoning["blocked_or_reduced_paths"]:
        pseudo_path = {
            "nodes": blocked_path["nodes"],
            "edge_types": blocked_path["edge_types"],
            "score": 30,
        }
        add_recommendation(
            title="Keep firewall or segmentation control in place",
            action_type="segment_network",
            severity="low",
            reason=(
                f"{blocked_path['reason']} Path checked: "
                f"{_format_path_labels(graph, blocked_path['nodes'])}."
            ),
            path=pseudo_path,
            what_it_fixes="Shows the current defensive control is reducing exposure.",
            expected_effect="Maintaining the rule keeps the downstream asset from being treated as fully exposed.",
            confidence="medium",
            risk_reduction=30,
        )

    cleaned = []
    for recommendation in recommendations:
        recommendation.pop("_dedupe_key", None)
        cleaned.append(recommendation)

    return cleaned[:5]


def _path_involves_router_admin(graph, path):
    edge_types = set(path.get("edge_types", []))
    if not edge_types & {"administers", "controls", "stores_credentials_for", "internet_exposes"}:
        return False

    return any(
        _node_matches(
            graph["node_lookup"].get(node_id, {}),
            "router",
            "firewall",
            "gateway",
            "vpn",
        )
        for node_id in path.get("nodes", [])
    )


def _find_reachable_exposure(graph, compromised_node_id, max_depth):
    reachable_nodes = [compromised_node_id]
    reachable_edges = []
    seen_nodes = {compromised_node_id}
    seen_edges = set()
    queue = [(compromised_node_id, 0)]

    while queue:
        current_node_id, depth = queue.pop(0)
        if depth >= max_depth:
            continue

        for edge in graph["adjacency"].get(current_node_id, []):
            target = edge["target"]
            edge_key = (edge["source"], edge["target"])

            if edge_key not in seen_edges:
                reachable_edges.append(
                    {
                        "source": edge["source"],
                        "target": edge["target"],
                        "relationship": edge["relationship"],
                    }
                )
                seen_edges.add(edge_key)

            if target in seen_nodes:
                continue

            seen_nodes.add(target)
            reachable_nodes.append(target)
            queue.append((target, depth + 1))

    return {
        "nodes": reachable_nodes,
        "edges": reachable_edges,
    }


def _build_current_graph_recommendations(
    paths,
    reachable_edges,
    graph,
    compromised_node_id,
    simulation_type="compromise",
):
    recommendations = []
    relationships = {
        (edge["source"], edge["target"], edge.get("relationship"))
        for edge in reachable_edges
    }
    path_nodes = {node for path in paths for node in path["path_node_ids"]}
    affected_nodes = {
        node_id
        for edge in reachable_edges
        for node_id in (edge["source"], edge["target"])
    }
    scope_nodes = path_nodes | affected_nodes | {compromised_node_id}
    highest_risk = max((path["risk_score"] for path in paths), default=0)
    same_network_count = sum(
        1 for edge in reachable_edges if edge.get("relationship") == "same_network"
    )

    def add_recommendation(
        title,
        action_type,
        recommendation_level,
        risk_reduction,
        reason,
    ):
        if any(recommendation["title"] == title for recommendation in recommendations):
            return

        recommendations.append(
            {
                "title": title,
                "action_type": action_type,
                "recommendation_level": recommendation_level,
                "risk_reduction": risk_reduction,
                "reason": reason,
            }
        )

    def node_matches(node_id, *needles):
        node = graph["node_lookup"].get(node_id, {})
        searchable = " ".join(
            str(node.get(key, ""))
            for key in ("id", "label", "type", "node_type", "description")
        ).lower()
        return any(needle in searchable for needle in needles)

    router_in_scope = any(node_matches(node_id, "router") for node_id in scope_nodes)

    if simulation_type == "spyware":
        add_recommendation(
            "Isolate the suspected spyware device.",
            "isolate_node",
            "strong",
            80,
            "Disconnect or isolate the device while checking what accounts, files, and nearby devices it could observe.",
        )
        add_recommendation(
            "Rotate passwords used on or near this device.",
            "rotate_credentials",
            "strong",
            70,
            "Spyware can expose credentials, sessions, and sensitive prompts. Rotate passwords and review sign-ins.",
        )
        add_recommendation(
            "Check sensitive accounts and data access.",
            "review_access",
            "useful",
            55,
            "Review accounts, cloud sessions, shared folders, and sensitive data reachable from this device.",
        )
    elif simulation_type == "data_leak":
        add_recommendation(
            "Revoke unnecessary data access.",
            "revoke_access",
            "strong",
            75,
            "Limit what this device can read from shared folders, cloud accounts, NAS, servers, and databases.",
        )
        add_recommendation(
            "Rotate credentials and sessions.",
            "rotate_credentials",
            "strong",
            70,
            "A data leak can expose stored passwords, access tokens, and active sessions.",
        )
        add_recommendation(
            "Review shared folders and cloud access.",
            "review_access",
            "useful",
            55,
            "Check whether accessible folders, accounts, or cloud services are broader than necessary.",
        )
    elif simulation_type == "lateral_movement":
        add_recommendation(
            "Restrict admin access on reachable paths.",
            "restrict_admin_access",
            "strong",
            80,
            "Privilege and control paths should be narrowed so one device cannot become a stepping stone.",
        )
        add_recommendation(
            "Rotate stored credentials on path chokepoints.",
            "remove_stored_credentials",
            "strong",
            75,
            "Stored credentials can turn ordinary reachability into privileged movement.",
        )
        add_recommendation(
            "Isolate path chokepoints.",
            "segment_network",
            "strong",
            70,
            "Segment routers, VPN gateways, file servers, and identity systems that connect many paths.",
        )
    elif simulation_type == "offline":
        add_recommendation(
            "Review dependencies on the offline device.",
            "improve_resilience",
            "strong",
            70,
            "Devices and services that depend on this node may need backup routing, redundancy, or a manual workaround.",
        )
        add_recommendation(
            "Check backup and monitoring coverage.",
            "improve_monitoring",
            "useful",
            45,
            "Availability scenarios should confirm that backups and monitoring still work when this device is unavailable.",
        )

    if router_in_scope:
        add_recommendation(
            "Change router admin password.",
            "improve_router_security",
            "strong",
            75,
            (
                "Router exposure can affect many connected devices. Use a strong "
                "unique admin password and remove any old/default credentials."
            ),
        )
        add_recommendation(
            "Update router firmware.",
            "improve_router_security",
            "strong",
            65,
            (
                "Router firmware updates fix known weaknesses and reduce the chance "
                "that a compromised or exposed router becomes the centre of the path."
            ),
        )
        add_recommendation(
            "Disable remote administration if not needed.",
            "improve_router_security",
            "strong",
            70,
            (
                "Remote administration can turn a router into an internet-facing "
                "management target. Disable it unless there is a clear operational need."
            ),
        )
        add_recommendation(
            "Separate guest/IoT devices from personal/work devices.",
            "segment_network",
            "strong",
            70,
            (
                "Segmentation limits blast radius if a low-trust device, guest device, "
                "or IoT device becomes compromised."
            ),
        )
        add_recommendation(
            "Review which devices are connected to the network.",
            "review_access",
            "useful",
            45,
            (
                "The analysis found connected devices in scope. Review whether each "
                "device should share the same network path."
            ),
        )

    if same_network_count >= 3:
        add_recommendation(
            "Separate guest and IoT devices",
            "segment_network",
            "useful",
            55,
            (
                "Mitigation recommendation because this device can reach many "
                "systems through same-network exposure. Consider a guest network "
                "or IoT isolation."
            ),
        )

    if paths:
        add_recommendation(
            "Segment high-risk network paths",
            "segment_network",
            "strong" if highest_risk >= 70 else "useful",
            min(100, highest_risk),
            (
                "Mitigation recommendation because segmentation can reduce "
                "blast radius across the reachable exposure paths."
            ),
        )

    if any(node_matches(node_id, "nas", "home_server", "home-server") for node_id in path_nodes):
        add_recommendation(
            "Restrict NAS and shared storage access",
            "segment_network",
            "strong",
            70,
            (
                "Mitigation recommendation because the exposure path reaches a "
                "NAS or home server. Review shared folders, restrict access, and "
                "rotate stored credentials."
            ),
        )

    if any(node_matches(node_id, "printer") for node_id in scope_nodes):
        add_recommendation(
            "Reduce unnecessary printer access",
            "segment_network",
            "useful",
            35,
            (
                "Mitigation recommendation because the exposure path reaches a "
                "printer. Keep firmware updated and block unnecessary access."
            ),
        )

    if any(node_matches(node_id, "work_laptop", "work laptop") for node_id in scope_nodes):
        add_recommendation(
            "Separate work devices from home and IoT devices",
            "segment_network",
            "strong",
            65,
            (
                "Mitigation recommendation because the exposure path reaches a "
                "work laptop. Keep work devices separate from guest, home, and "
                "IoT networks where possible."
            ),
        )

    if any(node_matches(node_id, "admin") for node_id in path_nodes):
        add_recommendation(
            "Review and rotate privileged credentials",
            "remove_stored_credentials",
            "strong",
            75,
            (
                "Mitigation recommendation because the exposure path reaches "
                "privileged identity or stored credential nodes."
            ),
        )

    if relationships and not paths:
        add_recommendation(
            "No high/critical devices were reached, but connected devices may still be exposed.",
            "review_exposure",
            "basic",
            20,
            (
                "The current graph has reachable connected devices even though none "
                "are currently marked high or critical."
            ),
        )
        add_recommendation(
            "Mark important devices as high/critical to improve analysis.",
            "improve_data_quality",
            "basic",
            15,
            (
                "Criticality helps BreachPath decide which reachable systems should "
                "be treated as high-impact."
            ),
        )
        add_recommendation(
            "Consider separating low-trust devices such as printers, smart TVs, and IoT devices.",
            "segment_network",
            "basic",
            30,
            (
                "Low-trust devices should usually be separated from personal, work, "
                "storage, and administrative systems."
            ),
        )

    if relationships:
        add_recommendation(
            "Restrict unnecessary device access",
            "segment_network",
            "useful",
            50,
            (
                "Mitigation recommendation because reducing unnecessary "
                "can-access relationships lowers reachable systems."
            ),
        )

    if not recommendations:
        recommendations.extend(
            [
                {
                    "title": "Review connected device access",
                    "action_type": "review_access",
                    "recommendation_level": "basic",
                    "risk_reduction": 10,
                    "reason": (
                        "Review whether this device needs access to all connected "
                        "devices."
                    ),
                },
                {
                    "title": "Separate guest and IoT devices",
                    "action_type": "segment_network",
                    "recommendation_level": "basic",
                    "risk_reduction": 10,
                    "reason": (
                        "Consider separating guest/IoT devices from personal or work "
                        "devices."
                    ),
                },
                {
                    "title": "Mark important devices as critical",
                    "action_type": "improve_data_quality",
                    "recommendation_level": "basic",
                    "risk_reduction": 10,
                    "reason": (
                        "Mark important devices as critical to improve risk analysis."
                    ),
                },
            ]
        )

    return recommendations[:5]
