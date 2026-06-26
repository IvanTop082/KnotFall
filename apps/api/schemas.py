from typing import Any

from pydantic import BaseModel


class NodeSummary(BaseModel):
    id: str
    label: str
    type: str
    zone: str
    criticality: int
    description: str


class EdgeSummary(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    risk_weight: int
    description: str


class GraphResponse(BaseModel):
    metadata: dict[str, Any]
    nodes: list[NodeSummary]
    edges: list[EdgeSummary]


class AttackPathResult(BaseModel):
    asset_id: str
    asset_label: str
    asset_type: str
    criticality: int
    path_node_ids: list[str]
    path_labels: list[str]
    edge_relationships: list[str]
    hops: int
    edge_risk_total: int
    risk_score: int
    risk_level: str
    reason: str


class AttackPathResponse(BaseModel):
    compromised_node: str
    max_depth: int
    paths_found: int
    critical_assets_found: int
    message: str
    results: list[AttackPathResult]


class ErrorResponse(BaseModel):
    detail: str
