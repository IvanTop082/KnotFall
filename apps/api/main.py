from datetime import UTC, datetime

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
from .repositories.network_repository import get_network_repository, graph_hash
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
        "follow": {
            "same_network",
            "can_access",
            "routes_through",
            "administers",
            "stores_credentials_for",
            "controls",
            "internet_exposes",
        },
        "bidirectional": {"same_network", "can_access", "routes_through"},
    },
    "offline": {
        "label": "Offline / destroyed",
        "follow": {"depends_on", "routes_through", "backs_up", "monitors"},
        "bidirectional": {"routes_through"},
    },
    "spyware": {
        "label": "Spyware",
        "follow": {"same_network", "can_access", "monitors", "stores_credentials_for"},
        "bidirectional": {"same_network", "can_access"},
    },
    "data_leak": {
        "label": "Data leak",
        "follow": {"can_access", "stores_credentials_for"},
        "bidirectional": set(),
    },
    "lateral_movement": {
        "label": "Lateral movement",
        "follow": {
            "can_access",
            "administers",
            "controls",
            "stores_credentials_for",
            "routes_through",
        },
        "bidirectional": {"can_access", "routes_through"},
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
    repository = get_network_repository(TURINGDB_HOST)
    status = repository.storage_status()
    connected = status.get("status") == "connected"
    return {
        "mode": "turingdb" if connected else "local_fallback",
        "connected": connected,
        "message": "TuringDB connected" if connected else status.get("message", "Storage: Local fallback"),
    }


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
    repository = get_network_repository(TURINGDB_HOST)
    result = repository.save_network(
        network_id=request.network_id,
        name=request.name,
        graph=request.graph.dict(),
        message=request.message,
    )

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
    repository = get_network_repository(TURINGDB_HOST)
    result = repository.save_network(
        network_id=request.network_id,
        name=request.name,
        graph=request.graph.dict(),
        message=request.message,
    )

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
    repository = get_network_repository(TURINGDB_HOST)
    return repository.storage_status()


@app.get("/networks", response_model=list[NetworkSummary])
def list_saved_networks():
    repository = get_network_repository(TURINGDB_HOST)
    return repository.list_networks()


@app.delete("/networks/{network_id}")
def delete_saved_network(network_id: str):
    repository = get_network_repository(TURINGDB_HOST)
    try:
        repository.delete_network(network_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return {
        "network_id": network_id,
        "status": "deleted",
    }


@app.get("/networks/{network_id}", response_model=SavedNetworkResponse)
def get_saved_network(network_id: str):
    repository = get_network_repository(TURINGDB_HOST)
    try:
        return repository.get_network(network_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/networks/{network_id}/history", response_model=list[NetworkCommitSummary])
def get_saved_network_history(network_id: str):
    repository = get_network_repository(TURINGDB_HOST)
    try:
        return repository.get_history(network_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/networks/{network_id}/versions", response_model=list[NetworkCommitSummary])
def get_saved_network_versions(network_id: str):
    repository = get_network_repository(TURINGDB_HOST)
    try:
        return repository.get_history(network_id)
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
    repository = get_network_repository(TURINGDB_HOST)
    try:
        return repository.get_version(network_id, version)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/networks/{network_id}/restore/{version}", response_model=NetworkSaveResponse)
def restore_saved_network_version(network_id: str, version: int):
    repository = get_network_repository(TURINGDB_HOST)
    try:
        result = repository.restore_version(network_id, version)
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
    repository = get_network_repository(TURINGDB_HOST)
    try:
        return repository.compare_versions(network_id, from_version, to_version)
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

    try:
        graph = _normalise_analysis_graph(request.graph.dict(), simulation_type)
    except GraphDataError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if request.node_id not in graph["node_lookup"]:
        raise HTTPException(
            status_code=404,
            detail=f"Node not found: {request.node_id}",
        )

    reachable = _find_reachable_exposure(graph, request.node_id, max_depth)
    path_finder = LocalJSONPathFinder(graph)
    paths = path_finder.find_attack_paths(
        compromised_node_id=request.node_id,
        max_depth=max_depth,
        max_paths_per_asset=max_paths_per_asset,
    )
    recommendations = _build_current_graph_recommendations(
        paths=paths,
        reachable_edges=reachable["edges"],
        graph=graph,
        compromised_node_id=request.node_id,
        simulation_type=simulation_type,
    )
    analysed_at = datetime.now(UTC).isoformat()
    resolved_graph_hash = request.graph_hash or graph_hash(request.graph.dict())

    analysis = _build_compromised_node_analysis(
        graph=graph,
        compromised_node_id=request.node_id,
        paths=paths,
        recommendations=recommendations,
        simulation_type=simulation_type,
        highlighted_nodes=reachable["nodes"],
        highlighted_edges=reachable["edges"],
        network_id=request.network_id,
        version=request.version,
        graph_hash=resolved_graph_hash,
        analysed_at=analysed_at,
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

    try:
        repository = get_network_repository(TURINGDB_HOST)
        repository.record_analysis(
            network_id=network_id,
            version=int(version),
            analysis={
                "analysed_at": analysis.get("analysed_at"),
                "graph_hash": analysis.get("graph_hash"),
                "node_id": analysis["compromised_node"]["id"],
                "simulation_type": analysis.get("simulation_type"),
                "risk_score": analysis.get("risk_score", 0),
                "risk_level": analysis.get("risk_level", "none"),
                "highlighted_nodes": analysis.get("highlighted_nodes", []),
                "highlighted_edges": analysis.get("highlighted_edges", []),
                "recommendations": analysis.get("recommendations", []),
            },
        )
    except Exception:
        return


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
):
    compromised_node = graph["node_lookup"][compromised_node_id]
    highlighted_nodes = list(highlighted_nodes or [])
    highlighted_edges = list(highlighted_edges or [])
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
            }
        )

    highest_risk_score = max((path["risk_score"] for path in paths), default=0)
    risk_level = _risk_level_from_score(highest_risk_score)
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

    return {
        "compromised_node": {
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
            "affected_node_count": len(highlighted_nodes),
            "affected_edge_count": len(highlighted_edges),
            "critical_assets_reachable": len(critical_assets),
            "highest_risk_score": highest_risk_score,
            "risk_level": risk_level,
        },
        "risk_score": highest_risk_score,
        "risk_level": risk_level,
        "highlighted_nodes": highlighted_nodes,
        "highlighted_edges": highlighted_edges,
        "paths": analysis_paths,
        "recommendations": [
            {
                "title": recommendation["title"],
                "type": recommendation["action_type"],
                "priority": recommendation["recommendation_level"],
                "estimated_risk_reduction": recommendation["risk_reduction"],
                "explanation": recommendation["reason"],
            }
            for recommendation in recommendations[:5]
        ],
        "explanation": _simulation_explanation(simulation_type, compromised_node, followed_edge_types),
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
    edges = []

    for edge in graph_payload.get("edges", []):
        normalised_edge = _normalise_analysis_edge(edge)
        if normalised_edge["source"] not in node_ids or normalised_edge["target"] not in node_ids:
            continue
        if normalised_edge["relationship"] not in rules["follow"]:
            continue
        edges.append(normalised_edge)

        if (
            normalised_edge.get("direction") == "bidirectional"
            or normalised_edge["relationship"] in rules["bidirectional"]
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
    ).strip()
    relationship = LEGACY_RELATIONSHIP_ALIASES.get(relationship, relationship)
    direction = str(edge.get("direction") or "").strip().lower()
    risk_can_spread_both_ways = _normalise_boolean(
        edge.get("risk_can_spread_both_ways")
    )
    risk_weight = _normalise_edge_risk(edge.get("risk_weight"))

    if relationship == "same_network":
        direction = "bidirectional"
    elif not direction:
        direction = "source_to_target"

    return {
        "id": str(edge.get("id") or f"{source}-{relationship}-{target}"),
        "source": source,
        "target": target,
        "relationship": relationship,
        "risk_weight": risk_weight,
        "description": str(edge.get("description") or edge.get("notes") or ""),
        "direction": direction,
        "risk_can_spread_both_ways": risk_can_spread_both_ways,
    }


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
