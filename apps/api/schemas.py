from typing import Any

from pydantic import BaseModel, Field


SimulationType = str


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


class RecommendationResult(BaseModel):
    improvement_id: str
    title: str
    action_type: str
    target_node_id: str
    expected_effect: str
    operational_cost: int
    baseline_total_risk: int
    after_total_risk: int
    risk_reduction: int
    recommendation_score: int
    paths_before: int
    paths_after: int
    paths_removed_count: int
    critical_assets_protected: list[str]
    recommendation_level: str
    reason: str
    tradeoff: str
    why_not_enough: str | None = None


class RecommendationResponse(BaseModel):
    compromised_node: str
    baseline_total_risk: int
    recommendations_count: int
    best_recommendation_id: str | None
    message: str
    results: list[RecommendationResult]


class AnalysisCompromisedNode(BaseModel):
    id: str
    label: str
    type: str


class AnalysisSummary(BaseModel):
    affected_node_count: int
    affected_edge_count: int
    critical_assets_reachable: int
    highest_risk_score: int
    risk_level: str


class AnalysisEdgeRef(BaseModel):
    id: str | None = None
    source: str
    target: str
    relationship: str | None = None
    blocked_or_reduced_by: list[str] = []


class AnalysisPath(BaseModel):
    path_id: str | None = None
    target: str
    risk_score: int
    risk_level: str
    nodes: list[str]
    edges: list[AnalysisEdgeRef]
    explanation: str
    edge_ids: list[str] = []
    edge_types: list[str] = []
    target_node: str | None = None
    target_criticality: int | None = None
    score: int | None = None
    severity: str | None = None
    why_this_path_matters: str | None = None
    blocked_or_reduced_by: list[str] = []


class AnalysisRankedPath(BaseModel):
    path_id: str
    nodes: list[str]
    edges: list[str]
    edge_refs: list[AnalysisEdgeRef] = []
    edge_types: list[str]
    target_node: str
    target_criticality: int
    score: int
    severity: str
    why_this_path_matters: str
    blocked_or_reduced_by: list[str] = []


class AnalysisBlockedPath(BaseModel):
    path_id: str
    nodes: list[str]
    edges: list[str] = []
    edge_refs: list[AnalysisEdgeRef] = []
    edge_types: list[str] = []
    target_node: str | None = None
    reason: str
    severity: str = "reduced"


class AnalysisTraversalEdgeDecision(BaseModel):
    edge_id: str
    from_: str = Field(alias="from")
    to: str
    edge_type: str
    direction: str
    decision: str
    reason: str
    from_label: str | None = None
    to_label: str | None = None
    score: int | None = None


class AnalysisRankedButNotHighlightedPath(BaseModel):
    nodes: list[str]
    edges: list[str] = []
    edge_types: list[str] = []
    score: int
    reason: str


class AnalysisConnectedButNotHighlighted(BaseModel):
    node_id: str
    label: str
    reason: str
    edge_id: str | None = None
    edge_type: str | None = None


class AnalysisTraversalExplanation(BaseModel):
    source_node: str
    simulation_type: SimulationType
    highlight_threshold: int
    max_highlighted_paths: int
    followed_edges: list[AnalysisTraversalEdgeDecision] = []
    skipped_edges: list[AnalysisTraversalEdgeDecision] = []
    ranked_but_not_highlighted_paths: list[AnalysisRankedButNotHighlightedPath] = []
    connected_but_not_highlighted: list[AnalysisConnectedButNotHighlighted] = []
    reachable_nodes: list[str] = []
    reachable_edges: list[AnalysisEdgeRef] = []


class AnalysisRecommendation(BaseModel):
    title: str
    type: str
    priority: str
    estimated_risk_reduction: int
    explanation: str
    severity: str | None = None
    reason: str | None = None
    triggered_by_path: list[str] = []
    affected_nodes: list[str] = []
    relevant_edge_types: list[str] = []
    simulation_type: SimulationType | None = None
    what_it_fixes: str | None = None
    expected_effect: str | None = None
    confidence: str | None = None
    action_steps: list[str] = []


class CompromisedNodeAnalysisResponse(BaseModel):
    compromised_node: AnalysisCompromisedNode
    source_node: AnalysisCompromisedNode | None = None
    network_id: str | None = None
    version: int | None = None
    graph_hash: str | None = None
    analysed_at: str | None = None
    simulation_type: SimulationType = "compromise"
    summary: AnalysisSummary
    summary_text: str | None = None
    risk_score: int = 0
    risk_level: str = "none"
    highlighted_nodes: list[str]
    highlighted_edges: list[AnalysisEdgeRef]
    paths: list[AnalysisPath]
    top_paths: list[AnalysisRankedPath] = []
    affected_nodes: list[str] = []
    critical_nodes_reached: list[str] = []
    blocked_or_reduced_paths: list[AnalysisBlockedPath] = []
    low_relevance_nodes: list[str] = []
    traversal_explanation: AnalysisTraversalExplanation | None = None
    recommendations: list[AnalysisRecommendation]
    explanation: str = ""
    followed_edge_types: list[str] = []
    visual_severity_by_node: dict[str, str] = {}
    visual_severity_by_edge: dict[str, str] = {}
    defensive_note: str


class AnalysisGraphPayload(BaseModel):
    metadata: dict[str, Any] = {}
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class CompromisedNodeAnalysisRequest(BaseModel):
    node_id: str
    simulation_type: SimulationType = "compromise"
    network_id: str | None = None
    version: int | None = None
    graph_hash: str | None = None
    graph: AnalysisGraphPayload


class ErrorResponse(BaseModel):
    detail: str


class NetworkSaveRequest(BaseModel):
    network_id: str
    name: str
    graph: AnalysisGraphPayload
    message: str = "Saved network"


class NetworkSaveVersionRequest(BaseModel):
    network_id: str
    graph: AnalysisGraphPayload
    message: str = "Saved network version"
    name: str | None = None


class NetworkSaveResponse(BaseModel):
    network_id: str
    name: str | None = None
    commit_id: str
    version: int
    message: str | None = None
    created_at: str | None = None
    node_count: int | None = None
    edge_count: int | None = None
    status: str
    storage_backend: str = "local_history_fallback"
    warning: str | None = None


class NetworkSummary(BaseModel):
    network_id: str
    name: str
    version: int
    updated_at: str
    node_count: int
    edge_count: int
    storage_backend: str = "local_history_fallback"


class NetworkCommitSummary(BaseModel):
    commit_id: str
    version: int
    message: str
    created_at: str
    node_count: int
    edge_count: int
    analysed: bool = False
    analysis_count: int = 0


class SavedNetworkResponse(BaseModel):
    network_id: str
    name: str
    graph: dict[str, Any]
    version: int
    commit_id: str
    updated_at: str
    storage_backend: str = "local_history_fallback"


class SavedNetworkVersionResponse(BaseModel):
    network_id: str
    name: str
    graph: dict[str, Any]
    version: int
    commit_id: str
    message: str
    created_at: str
    node_count: int
    edge_count: int
    analysed: bool = False
    analysis_count: int = 0
    storage_backend: str = "local_history_fallback"


class NetworkCompareResponse(BaseModel):
    network_id: str
    from_version: int
    to_version: int
    added_nodes: list[dict[str, Any]]
    removed_nodes: list[dict[str, Any]]
    changed_nodes: list[dict[str, Any]]
    added_edges: list[dict[str, Any]]
    removed_edges: list[dict[str, Any]]
    changed_edges: list[dict[str, Any]]
    summary: dict[str, int]


class NetworkStorageStatusResponse(BaseModel):
    status: str
    storage_backend: str
    turingdb_host: str
    message: str
