"""Import the BreachPath demo network into TuringDB.

Run this inside the Dockerized API environment because the TuringDB Python SDK
does not currently install cleanly on the user's native Windows Python.
"""

from pathlib import Path
import json
import os
import re


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEMO_NETWORK_PATH = PROJECT_ROOT / "data" / "demo_network.json"
TURINGDB_HOST = os.getenv("TURINGDB_HOST", "http://localhost:16666")
GRAPH_NAME = os.getenv("TURINGDB_GRAPH_NAME", "breachpath_demo")


def escape_cypher_string(value):
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def cypher_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return f"'{escape_cypher_string(value)}'"


def cypher_properties(data):
    parts = [f"{key}: {cypher_value(value)}" for key, value in data.items()]
    return "{ " + ", ".join(parts) + " }"


def safe_identifier(value, fallback):
    identifier = re.sub(r"[^A-Za-z0-9_]", "_", str(value))
    if not identifier:
        identifier = fallback
    if identifier[0].isdigit():
        identifier = f"{fallback}_{identifier}"
    return identifier


def load_demo_network():
    with DEMO_NETWORK_PATH.open("r", encoding="utf-8") as network_file:
        return json.load(network_file)


def connect_to_turingdb():
    from turingdb import TuringDB

    return TuringDB(host=TURINGDB_HOST)


def create_or_load_graph(client):
    try:
        client.create_graph(GRAPH_NAME)
        print(f"Created graph: {GRAPH_NAME}")
    except Exception as error:
        print(f"Could not create graph, trying to load existing graph: {error}")
        try:
            client.load_graph(GRAPH_NAME)
            print(f"Loaded existing graph: {GRAPH_NAME}")
        except Exception as load_error:
            print(f"Could not load graph. It may already be loaded: {load_error}")

    client.set_graph(GRAPH_NAME)


def create_node_query(node):
    node_label = safe_identifier(node.get("type", "Node"), "Node")
    properties = cypher_properties(node)
    return f"CREATE (:BreachPathNode:{node_label} {properties})"


def create_edge_query(edge):
    relationship_label = safe_identifier(
        edge.get("relationship", "RELATES_TO"),
        "RELATES_TO",
    ).upper()
    properties = cypher_properties(edge)
    source_id = escape_cypher_string(edge["source"])
    target_id = escape_cypher_string(edge["target"])

    return (
        f"MATCH (source {{id: '{source_id}'}}), (target {{id: '{target_id}'}}) "
        f"CREATE (source)-[:{relationship_label} {properties}]->(target)"
    )


def main():
    print("Importing BreachPath demo graph into TuringDB.")
    print("Warning: rerunning this script may create duplicate nodes or edges if the graph is not reset first.")
    print(f"TuringDB host: {TURINGDB_HOST}")
    print(f"Graph name: {GRAPH_NAME}")

    try:
        graph = load_demo_network()
        client = connect_to_turingdb()
        create_or_load_graph(client)

        change = client.new_change()
        client.checkout(change=change)

        valid_node_ids = set()
        for node in graph.get("nodes", []):
            if not node.get("id"):
                print(f"Skipping invalid node without id: {node}")
                continue

            client.query(create_node_query(node))
            valid_node_ids.add(node["id"])

        client.query("COMMIT")

        imported_edges = 0
        for edge in graph.get("edges", []):
            if edge.get("source") not in valid_node_ids or edge.get("target") not in valid_node_ids:
                print(f"Skipping edge with missing endpoint: {edge}")
                continue

            client.query(create_edge_query(edge))
            imported_edges += 1

        client.query("CHANGE SUBMIT")
        client.checkout()

        print("Import complete.")
        print(f"Imported nodes: {len(valid_node_ids)}")
        print(f"Imported edges: {imported_edges}")
        print("Open the visualizer and select graph: breachpath_demo")
    except Exception as error:
        print("Could not import demo network into TuringDB.")
        print("Make sure TuringDB is running and the API is reachable.")
        print(f"Original error: {error}")


if __name__ == "__main__":
    main()
