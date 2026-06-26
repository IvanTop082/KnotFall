import copy
from typing import Any

from .graph_loader import build_adjacency_list, build_node_lookup


class LocalGraphSimulator:
    """Applies defensive changes to a copied local graph.

    The original graph is never mutated. Later, this local copy/edit approach
    can map to TuringDB branch/version simulation, where each proposed action
    is tested in its own graph branch before being compared.
    """

    def apply_improvement(
        self,
        graph_data: dict[str, Any],
        improvement: dict[str, Any],
    ) -> dict[str, Any]:
        simulated = copy.deepcopy(graph_data)
        nodes = simulated["nodes"]
        edges = simulated["edges"]
        node_lookup = build_node_lookup(nodes)

        target_node_id = improvement.get("target_node_id")
        action_type = improvement.get("action_type")
        metadata = {
            "applied": True,
            "blocked_edges_count": 0,
            "monitoring_bonus": 0,
            "message": "",
        }

        if target_node_id not in node_lookup:
            metadata.update(
                {
                    "applied": False,
                    "message": f"Target node not found: {target_node_id}",
                }
            )
            return self._rebuild_graph(simulated, metadata)

        if action_type == "isolate_node":
            edges = self._remove_edges_connected_to_node(edges, target_node_id, metadata)
            node_lookup[target_node_id]["isolated"] = True
            metadata["message"] = "Removed incoming and outgoing edges for the node."
        elif action_type == "disable_account":
            edges = self._disable_identity_edges(
                edges,
                node_lookup[target_node_id],
                metadata,
            )
        elif action_type == "remove_stored_credentials":
            edges = self._remove_stored_credential_edges(
                edges,
                target_node_id,
                metadata,
            )
        elif action_type == "segment_network":
            edges = self._segment_target_node(edges, target_node_id, metadata)
        elif action_type == "improve_monitoring":
            metadata.update(
                {
                    "monitoring_bonus": 10,
                    "message": (
                        "Monitoring improves visibility, but it does not break "
                        "attack paths in the graph."
                    ),
                }
            )
        else:
            metadata.update(
                {
                    "applied": False,
                    "message": f"Unsupported improvement action: {action_type}",
                }
            )

        simulated["edges"] = edges
        return self._rebuild_graph(simulated, metadata)

    def _remove_edges_connected_to_node(
        self,
        edges: list[dict[str, Any]],
        target_node_id: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        remaining_edges = [
            edge
            for edge in edges
            if edge["source"] != target_node_id and edge["target"] != target_node_id
        ]
        metadata["blocked_edges_count"] = len(edges) - len(remaining_edges)
        return remaining_edges

    def _disable_identity_edges(
        self,
        edges: list[dict[str, Any]],
        target_node: dict[str, Any],
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if target_node["type"] != "identity":
            metadata.update(
                {
                    "applied": False,
                    "message": "disable_account only applies to identity nodes.",
                }
            )
            return edges

        remaining_edges = [
            edge for edge in edges if edge["source"] != target_node["id"]
        ]
        metadata["blocked_edges_count"] = len(edges) - len(remaining_edges)
        metadata["message"] = "Removed outgoing edges from the disabled identity."
        return remaining_edges

    def _remove_stored_credential_edges(
        self,
        edges: list[dict[str, Any]],
        target_node_id: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        remaining_edges = [
            edge
            for edge in edges
            if not (
                edge["source"] == target_node_id
                and edge["relationship"] == "stores_credentials"
            )
        ]
        metadata["blocked_edges_count"] = len(edges) - len(remaining_edges)
        metadata["message"] = "Removed stored credential edges from the target node."
        return remaining_edges

    def _segment_target_node(
        self,
        edges: list[dict[str, Any]],
        target_node_id: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        risky_relationships = {"can_access", "grants_access", "controls"}
        remaining_edges = [
            edge
            for edge in edges
            if not (
                edge["target"] == target_node_id
                and edge["relationship"] in risky_relationships
            )
        ]
        metadata["blocked_edges_count"] = len(edges) - len(remaining_edges)
        metadata["message"] = "Removed risky incoming access edges to the target node."
        return remaining_edges

    def _rebuild_graph(
        self,
        graph_data: dict[str, Any],
        simulation_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        nodes = graph_data["nodes"]
        edges = graph_data["edges"]

        return {
            "metadata": graph_data.get("metadata", {}),
            "nodes": nodes,
            "edges": edges,
            "node_lookup": build_node_lookup(nodes),
            "adjacency": build_adjacency_list(nodes, edges),
            "simulation": simulation_metadata,
        }
