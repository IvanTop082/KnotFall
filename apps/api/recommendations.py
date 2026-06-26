import json
from pathlib import Path
from typing import Any

from .config import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_PATHS_PER_ASSET,
    DEMO_IMPROVEMENTS_PATH,
)
from .graph_loader import load_demo_network
from .path_finder import LocalJSONPathFinder
from .simulation import LocalGraphSimulator


class LocalRecommendationEngine:
    """Ranks improvements by simulating before/after attack-path risk."""

    def __init__(
        self,
        improvements_path: Path = DEMO_IMPROVEMENTS_PATH,
    ):
        self.improvements_path = improvements_path
        self.simulator = LocalGraphSimulator()

    def recommend(
        self,
        compromised_node_id: str,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_paths_per_asset: int = DEFAULT_MAX_PATHS_PER_ASSET,
    ) -> dict[str, Any]:
        graph = load_demo_network()

        if compromised_node_id not in graph["node_lookup"]:
            raise ValueError(f"Node not found: {compromised_node_id}")

        baseline_paths = self._find_paths(
            graph,
            compromised_node_id,
            max_depth,
            max_paths_per_asset,
        )
        baseline_total_risk = self._total_risk(baseline_paths)

        if not baseline_paths:
            return {
                "compromised_node": compromised_node_id,
                "baseline_total_risk": 0,
                "recommendations_count": 0,
                "best_recommendation_id": None,
                "message": (
                    "No critical assets are currently reachable, so no urgent "
                    "blocking recommendation is needed."
                ),
                "results": [],
            }

        recommendations = [
            self._score_improvement(
                graph=graph,
                compromised_node_id=compromised_node_id,
                improvement=improvement,
                baseline_paths=baseline_paths,
                baseline_total_risk=baseline_total_risk,
                max_depth=max_depth,
                max_paths_per_asset=max_paths_per_asset,
            )
            for improvement in self._load_improvements()
        ]
        recommendations.sort(
            key=lambda result: (
                -result["recommendation_score"],
                result["operational_cost"],
                result["title"],
            )
        )

        return {
            "compromised_node": compromised_node_id,
            "baseline_total_risk": baseline_total_risk,
            "recommendations_count": len(recommendations),
            "best_recommendation_id": recommendations[0]["improvement_id"]
            if recommendations
            else None,
            "message": "Ranked recommendations calculated from simulated risk changes.",
            "results": recommendations,
        }

    def _score_improvement(
        self,
        graph: dict[str, Any],
        compromised_node_id: str,
        improvement: dict[str, Any],
        baseline_paths: list[dict[str, Any]],
        baseline_total_risk: int,
        max_depth: int,
        max_paths_per_asset: int,
    ) -> dict[str, Any]:
        target_node_id = improvement["target_node_id"]
        target_node = graph["node_lookup"].get(target_node_id)
        operational_cost = int(improvement["operational_cost"])

        if target_node is None:
            return self._invalid_target_result(
                improvement,
                baseline_total_risk,
                len(baseline_paths),
            )

        simulated_graph = self.simulator.apply_improvement(graph, improvement)
        after_paths = self._find_paths(
            simulated_graph,
            compromised_node_id,
            max_depth,
            max_paths_per_asset,
        )
        after_total_risk = self._total_risk(after_paths)
        risk_reduction = baseline_total_risk - after_total_risk
        recommendation_score = risk_reduction - operational_cost
        recommendation_level = self._level_for_score(recommendation_score)
        protected_assets = self._critical_assets_protected(baseline_paths, after_paths)
        paths_removed_count = self._paths_removed_count(baseline_paths, after_paths)
        simulation_metadata = simulated_graph.get("simulation", {})
        why_not_enough = self._why_not_enough(
            improvement=improvement,
            recommendation_score=recommendation_score,
            risk_reduction=risk_reduction,
            paths_removed_count=paths_removed_count,
            simulation_metadata=simulation_metadata,
        )

        return {
            "improvement_id": improvement["id"],
            "title": improvement["title"],
            "action_type": improvement["action_type"],
            "target_node_id": target_node_id,
            "expected_effect": improvement["expected_effect"],
            "operational_cost": operational_cost,
            "baseline_total_risk": baseline_total_risk,
            "after_total_risk": after_total_risk,
            "risk_reduction": risk_reduction,
            "recommendation_score": recommendation_score,
            "paths_before": len(baseline_paths),
            "paths_after": len(after_paths),
            "paths_removed_count": paths_removed_count,
            "critical_assets_protected": protected_assets,
            "recommendation_level": recommendation_level,
            "reason": self._build_reason(
                improvement=improvement,
                target_node=target_node,
                recommendation_level=recommendation_level,
                risk_reduction=risk_reduction,
                protected_assets=protected_assets,
                paths_removed_count=paths_removed_count,
                simulation_metadata=simulation_metadata,
            ),
            "tradeoff": self._tradeoff_for_action(improvement["action_type"]),
            "why_not_enough": why_not_enough,
        }

    def _find_paths(
        self,
        graph: dict[str, Any],
        compromised_node_id: str,
        max_depth: int,
        max_paths_per_asset: int,
    ) -> list[dict[str, Any]]:
        finder = LocalJSONPathFinder(graph)
        return finder.find_attack_paths(
            compromised_node_id=compromised_node_id,
            max_depth=max_depth,
            max_paths_per_asset=max_paths_per_asset,
        )

    def _load_improvements(self) -> list[dict[str, Any]]:
        with self.improvements_path.open("r", encoding="utf-8") as improvements_file:
            return json.load(improvements_file)

    def _total_risk(self, paths: list[dict[str, Any]]) -> int:
        return sum(int(path["risk_score"]) for path in paths)

    def _paths_removed_count(
        self,
        baseline_paths: list[dict[str, Any]],
        after_paths: list[dict[str, Any]],
    ) -> int:
        baseline_keys = {self._path_key(path) for path in baseline_paths}
        after_keys = {self._path_key(path) for path in after_paths}
        return len(baseline_keys - after_keys)

    def _critical_assets_protected(
        self,
        baseline_paths: list[dict[str, Any]],
        after_paths: list[dict[str, Any]],
    ) -> list[str]:
        baseline_assets = {
            path["asset_id"]: path["asset_label"] for path in baseline_paths
        }
        after_asset_ids = {path["asset_id"] for path in after_paths}
        protected_ids = sorted(set(baseline_assets) - after_asset_ids)
        return [baseline_assets[asset_id] for asset_id in protected_ids]

    def _path_key(self, path: dict[str, Any]) -> tuple[str, ...]:
        return tuple(path["path_node_ids"])

    def _level_for_score(self, recommendation_score: int) -> str:
        if recommendation_score >= 60:
            return "strong"
        if recommendation_score >= 25:
            return "useful"
        if recommendation_score >= 1:
            return "limited"
        return "weak"

    def _build_reason(
        self,
        improvement: dict[str, Any],
        target_node: dict[str, Any],
        recommendation_level: str,
        risk_reduction: int,
        protected_assets: list[str],
        paths_removed_count: int,
        simulation_metadata: dict[str, Any],
    ) -> str:
        if improvement["action_type"] == "improve_monitoring":
            return (
                "Limited recommendation because monitoring improves visibility "
                "but does not remove any attack paths."
            )

        if risk_reduction <= 0:
            return (
                f"Weak recommendation because {target_node['label']} is not "
                "reducing the currently simulated attack-path risk."
            )

        protected_text = self._format_asset_list(protected_assets)
        if protected_text:
            return (
                f"{recommendation_level.title()} recommendation because "
                f"{improvement['title'].lower()} removes paths to "
                f"{protected_text}."
            )

        return (
            f"{recommendation_level.title()} recommendation because "
            f"{improvement['title'].lower()} removes {paths_removed_count} paths "
            f"and reduces total simulated risk by {risk_reduction}."
        )

    def _tradeoff_for_action(self, action_type: str) -> str:
        tradeoffs = {
            "isolate_node": "May disrupt shared service access for legitimate users.",
            "disable_account": "May affect administrator operations.",
            "remove_stored_credentials": "Low disruption, but credential storage processes may need cleanup.",
            "segment_network": "May require firewall or routing changes.",
            "improve_monitoring": "Low disruption, but does not directly reduce reachability.",
        }
        return tradeoffs.get(action_type, "Operational impact should be reviewed.")

    def _why_not_enough(
        self,
        improvement: dict[str, Any],
        recommendation_score: int,
        risk_reduction: int,
        paths_removed_count: int,
        simulation_metadata: dict[str, Any],
    ) -> str | None:
        if not simulation_metadata.get("applied", True):
            return simulation_metadata.get("message")

        if improvement["action_type"] == "improve_monitoring":
            return "Monitoring does not directly break attacker reachability."

        if recommendation_score > 0:
            return None

        if risk_reduction <= 0:
            return "It does not reduce the current reachable critical-asset risk."

        if paths_removed_count == 0:
            return "It reduces risk score but does not remove complete attack paths."

        return "Its risk reduction does not outweigh the operational cost."

    def _invalid_target_result(
        self,
        improvement: dict[str, Any],
        baseline_total_risk: int,
        paths_before: int,
    ) -> dict[str, Any]:
        operational_cost = int(improvement["operational_cost"])

        return {
            "improvement_id": improvement["id"],
            "title": improvement["title"],
            "action_type": improvement["action_type"],
            "target_node_id": improvement["target_node_id"],
            "expected_effect": improvement["expected_effect"],
            "operational_cost": operational_cost,
            "baseline_total_risk": baseline_total_risk,
            "after_total_risk": baseline_total_risk,
            "risk_reduction": 0,
            "recommendation_score": -operational_cost,
            "paths_before": paths_before,
            "paths_after": paths_before,
            "paths_removed_count": 0,
            "critical_assets_protected": [],
            "recommendation_level": "weak",
            "reason": (
                "Weak recommendation because the target node is missing from "
                "the demo graph."
            ),
            "tradeoff": "Cannot simulate until the target exists in the graph data.",
            "why_not_enough": "The improvement target node could not be found.",
        }

    def _format_asset_list(self, assets: list[str]) -> str:
        if not assets:
            return ""
        if len(assets) == 1:
            return assets[0]
        return f"{', '.join(assets[:-1])}, and {assets[-1]}"
