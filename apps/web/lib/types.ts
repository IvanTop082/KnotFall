export type GraphNodeType =
  | "workstation"
  | "server"
  | "identity"
  | "security_tool"
  | "network_device"
  | "critical_asset"
  | "database";

export type GraphZone =
  | "user_zone"
  | "server_zone"
  | "identity_zone"
  | "operations_zone"
  | "security_zone";

export type RiskLevel = "low" | "medium" | "high";

export interface GraphNode {
  id: string;
  label: string;
  type: GraphNodeType;
  zone: GraphZone;
  criticality: number;
  description: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  risk_weight: number;
  description: string;
}

export interface GraphResponse {
  metadata: {
    name: string;
    version: string;
    description: string;
    created_for: string;
  };
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AttackPathResult {
  asset_id: string;
  asset_label: string;
  asset_type: string;
  criticality: number;
  path_node_ids: string[];
  path_labels: string[];
  edge_relationships: string[];
  hops: number;
  edge_risk_total: number;
  risk_score: number;
  risk_level: RiskLevel;
  reason: string;
}

export interface AttackPathResponse {
  compromised_node: string;
  max_depth: number;
  paths_found: number;
  critical_assets_found: number;
  message: string;
  results: AttackPathResult[];
}

export interface HealthResponse {
  status: string;
  service: string;
}
