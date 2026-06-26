from collections import defaultdict, deque
from typing import Any

from .risk import calculate_path_risk


class LocalJSONPathFinder:
    """Finds attack paths from the local JSON graph.

    This class is intentionally small and replaceable. Later, a
    TuringDBPathFinder class can expose the same find_attack_paths method while
    reading from TuringDB instead of local JSON.
    """

    def __init__(self, graph: dict[str, Any]):
        self.graph = graph
        self.node_lookup = graph["node_lookup"]
        self.adjacency = graph["adjacency"]

    def find_attack_paths(
        self,
        compromised_node_id: str,
        max_depth: int,
        max_paths_per_asset: int,
    ) -> list[dict[str, Any]]:
        if compromised_node_id not in self.node_lookup:
            raise ValueError(f"Node not found: {compromised_node_id}")

        results = []
        queue = deque([(compromised_node_id, [compromised_node_id], [])])

        while queue:
            current_node_id, path_node_ids, path_edges = queue.popleft()

            if len(path_edges) >= max_depth:
                continue

            for edge in self.adjacency.get(current_node_id, []):
                target_id = edge["target"]

                # Do not revisit a node already in this path. This prevents
                # loops from creating infinite searches.
                if target_id in path_node_ids:
                    continue

                next_path_node_ids = path_node_ids + [target_id]
                next_path_edges = path_edges + [edge]
                target_node = self.node_lookup[target_id]

                if self._is_critical_asset(target_node):
                    results.append(
                        self._build_attack_path_result(
                            target_node=target_node,
                            path_node_ids=next_path_node_ids,
                            path_edges=next_path_edges,
                        )
                    )

                if len(next_path_edges) < max_depth:
                    queue.append((target_id, next_path_node_ids, next_path_edges))

        sorted_results = sorted(
            results,
            key=lambda result: (-result["risk_score"], result["hops"]),
        )

        return self._limit_paths_per_asset(sorted_results, max_paths_per_asset)

    def _is_critical_asset(self, node: dict[str, Any]) -> bool:
        return node["type"] == "critical_asset" or int(node["criticality"]) >= 85

    def _build_attack_path_result(
        self,
        target_node: dict[str, Any],
        path_node_ids: list[str],
        path_edges: list[dict[str, Any]],
    ) -> dict[str, Any]:
        path_nodes = [self.node_lookup[node_id] for node_id in path_node_ids]
        risk = calculate_path_risk(target_node, path_nodes, path_edges)

        return {
            "asset_id": target_node["id"],
            "asset_label": target_node["label"],
            "asset_type": target_node["type"],
            "criticality": target_node["criticality"],
            "path_node_ids": path_node_ids,
            "path_labels": [node["label"] for node in path_nodes],
            "edge_relationships": [edge["relationship"] for edge in path_edges],
            "hops": len(path_edges),
            **risk,
        }

    def _limit_paths_per_asset(
        self,
        results: list[dict[str, Any]],
        max_paths_per_asset: int,
    ) -> list[dict[str, Any]]:
        counts_by_asset = defaultdict(int)
        limited_results = []

        for result in results:
            asset_id = result["asset_id"]

            if counts_by_asset[asset_id] >= max_paths_per_asset:
                continue

            limited_results.append(result)
            counts_by_asset[asset_id] += 1

        return limited_results
