from typing import Any


def clamp_score(score: int) -> int:
    return max(0, min(100, score))


def get_risk_level(risk_score: int) -> str:
    if risk_score <= 39:
        return "low"
    if risk_score <= 69:
        return "medium"
    return "high"


def calculate_path_risk(
    target_node: dict[str, Any],
    path_nodes: list[dict[str, Any]],
    path_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    target_criticality = int(target_node["criticality"])
    edge_risk_total = sum(int(edge["risk_weight"]) for edge in path_edges)
    hops = len(path_edges)
    includes_identity = any(node["type"] == "identity" for node in path_nodes)

    identity_bonus = 15 if includes_identity else 0
    hop_penalty = hops * 8

    raw_score = target_criticality + edge_risk_total + identity_bonus - hop_penalty
    risk_score = clamp_score(raw_score)
    risk_level = get_risk_level(risk_score)

    return {
        "edge_risk_total": edge_risk_total,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason": build_risk_reason(
            risk_level=risk_level,
            asset_label=target_node["label"],
            target_criticality=target_criticality,
            hops=hops,
            includes_identity=includes_identity,
        ),
    }


def build_risk_reason(
    risk_level: str,
    asset_label: str,
    target_criticality: int,
    hops: int,
    includes_identity: bool,
) -> str:
    identity_text = (
        " and the path passes through an identity node"
        if includes_identity
        else ""
    )

    return (
        f"{risk_level.title()} risk because {asset_label} has criticality "
        f"{target_criticality}, is reachable in {hops} hops{identity_text}."
    )
