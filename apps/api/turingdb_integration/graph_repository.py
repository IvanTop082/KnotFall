"""TuringDB-backed graph loading for BreachPath.

This module is isolated from the main local JSON logic so we can adjust SDK
return parsing without touching the working fallback backend.
"""

from typing import Any

from ..graph_loader import build_adjacency_list, build_node_lookup


class TuringDBGraphRepository:
    def __init__(self, host: str, graph_name: str = "breachpath_demo"):
        self.host = host
        self.graph_name = graph_name

    def load_graph(self) -> dict[str, Any]:
        client = self._connect()
        self._select_graph(client)

        nodes_result = client.query(
            """
            MATCH (n)
            WHERE n.id IS NOT NULL
            RETURN n.id AS id, n.label AS label, n.type AS node_type,
                   n.zone AS zone, n.criticality AS criticality,
                   n.description AS description
            """
        )
        edges_result = client.query(
            """
            MATCH (src)-[edge]->(dst)
            WHERE src.id IS NOT NULL AND dst.id IS NOT NULL
            RETURN edge.id AS id, src.id AS source_id, dst.id AS target_id,
                   edge.relationship AS relationship,
                   edge.risk_weight AS risk_weight,
                   edge.description AS description
            """
        )

        nodes = self._parse_nodes(nodes_result)
        edges = self._parse_edges(edges_result)

        return {
            "metadata": {
                "name": "BreachPath Demo Network from TuringDB",
                "version": "0.1.0",
                "description": "Demo cyber network loaded from TuringDB.",
                "created_for": "Bit 5B TuringDB-backed graph source",
            },
            "nodes": nodes,
            "edges": edges,
            "node_lookup": build_node_lookup(nodes),
            "adjacency": build_adjacency_list(nodes, edges),
        }

    def ping(self) -> dict[str, Any]:
        client = self._connect()
        self._select_graph(client)
        result = client.query("MATCH (n) RETURN n LIMIT 1")
        return {
            "status": "connected",
            "sample_result": self._result_preview(result),
        }

    def _connect(self):
        try:
            from turingdb import TuringDB
        except Exception as error:
            raise RuntimeError(
                "TuringDB SDK is not installed in this Python environment. "
                "Run the Dockerized API when using BREACHPATH_GRAPH_SOURCE=turingdb."
            ) from error

        return TuringDB(host=self.host)

    def _select_graph(self, client):
        try:
            client.load_graph(self.graph_name)
        except Exception:
            # The graph may already be loaded. Setting it below is the real test.
            pass
        client.set_graph(self.graph_name)

    def _parse_nodes(self, result) -> list[dict[str, Any]]:
        rows = self._rows_from_result(result)
        nodes = []

        for row in rows:
            node = {
                "id": self._row_value(row, "n.id", "id"),
                "label": self._row_value(row, "n.label", "label"),
                "type": self._row_value(row, "n.type", "node_type", "type"),
                "zone": self._row_value(row, "n.zone", "zone"),
                "criticality": int(self._row_value(row, "n.criticality", "criticality") or 0),
                "description": self._row_value(row, "n.description", "description") or "",
            }
            nodes.append(node)

        return nodes

    def _parse_edges(self, result) -> list[dict[str, Any]]:
        rows = self._rows_from_result(result)
        edges = []

        for row in rows:
            edge = {
                "id": self._row_value(row, "edge.id", "id"),
                "source": self._row_value(row, "source.id", "source_id", "source"),
                "target": self._row_value(row, "target.id", "target_id", "target"),
                "relationship": self._row_value(row, "edge.relationship", "relationship"),
                "risk_weight": int(self._row_value(row, "edge.risk_weight", "risk_weight") or 0),
                "description": self._row_value(row, "edge.description", "description") or "",
            }
            edges.append(edge)

        return edges

    def _rows_from_result(self, result) -> list[dict[str, Any]]:
        if hasattr(result, "to_dict"):
            return result.to_dict(orient="records")
        if isinstance(result, list):
            return result

        raise RuntimeError(
            "Could not parse TuringDB query result. "
            f"Unexpected result type: {type(result).__name__}. "
            f"Preview: {self._result_preview(result)}"
        )

    def _row_value(self, row: dict[str, Any], *keys: str):
        for key in keys:
            if key in row:
                return row[key]
        return None

    def _result_preview(self, result) -> str:
        try:
            return str(result.head()) if hasattr(result, "head") else str(result)
        except Exception:
            return "<could not render result preview>"
