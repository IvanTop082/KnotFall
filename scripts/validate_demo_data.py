from pathlib import Path
import json
import sys


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


def load_network_data():
    project_root = Path(__file__).resolve().parents[1]
    network_path = project_root / "data" / "demo_network.json"

    try:
        with network_path.open("r", encoding="utf-8") as network_file:
            return json.load(network_file)
    except FileNotFoundError:
        print(f"Error: could not find {network_path}")
        sys.exit(1)
    except json.JSONDecodeError as error:
        print(f"Error: invalid JSON in {network_path}")
        print(f"  {error}")
        sys.exit(1)


def validate_network(network):
    errors = []

    nodes = network.get("nodes")
    edges = network.get("edges")

    if not isinstance(nodes, list):
        errors.append("Network must include a 'nodes' list.")
        nodes = []

    if not isinstance(edges, list):
        errors.append("Network must include an 'edges' list.")
        edges = []

    node_ids = set()

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"Node at index {index} must be an object.")
            continue

        missing_fields = REQUIRED_NODE_FIELDS - node.keys()
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            errors.append(f"Node at index {index} is missing required fields: {fields}.")

        node_id = node.get("id")
        if node_id in node_ids:
            errors.append(f"Duplicate node id found: {node_id}.")
        elif node_id:
            node_ids.add(node_id)

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"Edge at index {index} must be an object.")
            continue

        missing_fields = REQUIRED_EDGE_FIELDS - edge.keys()
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            errors.append(f"Edge at index {index} is missing required fields: {fields}.")

        source = edge.get("source")
        target = edge.get("target")
        edge_id = edge.get("id", f"index {index}")

        if source and source not in node_ids:
            errors.append(f"Edge {edge_id} has unknown source node: {source}.")

        if target and target not in node_ids:
            errors.append(f"Edge {edge_id} has unknown target node: {target}.")

    return errors


def main():
    network = load_network_data()
    errors = validate_network(network)

    if errors:
        print("Demo network data is invalid:")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

    print("Demo network data is valid.")


if __name__ == "__main__":
    main()
