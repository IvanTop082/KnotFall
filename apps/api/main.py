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
from .schemas import (
    AttackPathResponse,
    CompromisedNodeAnalysisRequest,
    CompromisedNodeAnalysisResponse,
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ],
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
    try:
        graph = _normalise_analysis_graph(request.graph.dict())
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
    )

    return _build_compromised_node_analysis(
        graph=graph,
        compromised_node_id=request.node_id,
        paths=paths,
        recommendations=recommendations,
        highlighted_nodes=reachable["nodes"],
        highlighted_edges=reachable["edges"],
    )


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


def _build_compromised_node_analysis(
    graph,
    compromised_node_id,
    paths,
    recommendations,
    highlighted_nodes=None,
    highlighted_edges=None,
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

    return {
        "compromised_node": {
            "id": compromised_node["id"],
            "label": compromised_node["label"],
            "type": compromised_node["type"],
        },
        "summary": {
            "affected_node_count": len(highlighted_nodes),
            "affected_edge_count": len(highlighted_edges),
            "critical_assets_reachable": len(critical_assets),
            "highest_risk_score": highest_risk_score,
            "risk_level": risk_level,
        },
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


def _normalise_analysis_graph(graph_payload):
    nodes = [_normalise_analysis_node(node) for node in graph_payload.get("nodes", [])]
    node_ids = {node["id"] for node in nodes}
    edges = []

    for edge in graph_payload.get("edges", []):
        normalised_edge = _normalise_analysis_edge(edge)
        if normalised_edge["source"] not in node_ids or normalised_edge["target"] not in node_ids:
            continue
        if normalised_edge["relationship"] not in COMPROMISE_RELATIONSHIPS:
            continue
        edges.append(normalised_edge)

        if (
            normalised_edge.get("direction") == "bidirectional"
            or normalised_edge.get("risk_can_spread_both_ways")
            or normalised_edge["relationship"] in COMPROMISE_BIDIRECTIONAL_RELATIONSHIPS
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

    if relationship == "same_network" or risk_can_spread_both_ways:
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


def _build_current_graph_recommendations(paths, reachable_edges, graph, compromised_node_id):
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
