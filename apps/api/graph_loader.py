import json
from pathlib import Path
from typing import Any

from .config import DEMO_NETWORK_PATH
from .config import (
    BREACHPATH_GRAPH_SOURCE,
    TURINGDB_GRAPH_NAME,
    TURINGDB_HOST,
)


REQUIRED_NODE_FIELDS = {
    "id",
    "label",
    "type",
    "zone",
    "criticality",
    "description",
}

REQUIRED_EDGE_FIELDS = {
    "id",
    "source",
    "target",
    "relationship",
    "risk_weight",
    "description",
}


class GraphDataError(ValueError):
    pass


def load_configured_graph() -> dict[str, Any]:
    if BREACHPATH_GRAPH_SOURCE == "local":
        return load_demo_network()

    if BREACHPATH_GRAPH_SOURCE == "turingdb":
        from .turingdb_integration.graph_repository import TuringDBGraphRepository

        repository = TuringDBGraphRepository(
            host=TURINGDB_HOST,
            graph_name=TURINGDB_GRAPH_NAME,
        )
        graph = repository.load_graph()
        validate_graph_data(graph)
        return graph

    raise GraphDataError(
        "Invalid BREACHPATH_GRAPH_SOURCE. Use 'local' or 'turingdb'."
    )


def load_demo_network(path: Path = DEMO_NETWORK_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as network_file:
        graph = json.load(network_file)

    validate_graph_data(graph)
    nodes = graph["nodes"]
    edges = graph["edges"]

    return {
        "metadata": graph.get("metadata", {}),
        "nodes": nodes,
        "edges": edges,
        "node_lookup": build_node_lookup(nodes),
        "adjacency": build_adjacency_list(nodes, edges),
    }


def validate_graph_data(graph: dict[str, Any]) -> None:
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    errors = []

    if not isinstance(nodes, list):
        errors.append("Graph must include a 'nodes' list.")
        nodes = []

    if not isinstance(edges, list):
        errors.append("Graph must include an 'edges' list.")
        edges = []

    seen_node_ids = set()

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"Node at index {index} must be an object.")
            continue

        missing_fields = REQUIRED_NODE_FIELDS - node.keys()
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            errors.append(f"Node at index {index} is missing fields: {fields}.")

        node_id = node.get("id")
        if not node_id:
            errors.append(f"Node at index {index} must have a non-empty id.")
        elif node_id in seen_node_ids:
            errors.append(f"Duplicate node id found: {node_id}.")
        else:
            seen_node_ids.add(node_id)

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"Edge at index {index} must be an object.")
            continue

        missing_fields = REQUIRED_EDGE_FIELDS - edge.keys()
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            errors.append(f"Edge at index {index} is missing fields: {fields}.")

        edge_id = edge.get("id", f"index {index}")
        source = edge.get("source")
        target = edge.get("target")

        if source and source not in seen_node_ids:
            errors.append(f"Edge {edge_id} has unknown source node: {source}.")

        if target and target not in seen_node_ids:
            errors.append(f"Edge {edge_id} has unknown target node: {target}.")

    if errors:
        raise GraphDataError(" ".join(errors))


def build_node_lookup(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in nodes}


def build_adjacency_list(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    adjacency = {node["id"]: [] for node in nodes}

    for edge in edges:
        # Preserve the full edge information so later scoring and explanations
        # can use relationship, risk, and description details.
        adjacency[edge["source"]].append(dict(edge))

    return adjacency
