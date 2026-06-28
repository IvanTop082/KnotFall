export interface GraphNode {
  id: string;
  label: string;
  type: string;
  zone: string;
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
  metadata: Record<string, string>;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AnalysisEdgeRef {
  source: string;
  target: string;
}

export interface AnalysisPath {
  target: string;
  risk_score: number;
  risk_level: string;
  nodes: string[];
  edges: AnalysisEdgeRef[];
  explanation: string;
}

export interface AnalysisRecommendation {
  title: string;
  type: string;
  priority: string;
  estimated_risk_reduction: number;
  explanation: string;
}

export interface CompromisedNodeAnalysis {
  compromised_node: {
    id: string;
    label: string;
    type: string;
  };
  summary: {
    affected_node_count: number;
    affected_edge_count: number;
    critical_assets_reachable: number;
    highest_risk_score: number;
    risk_level: string;
  };
  highlighted_nodes: string[];
  highlighted_edges: AnalysisEdgeRef[];
  paths: AnalysisPath[];
  recommendations: AnalysisRecommendation[];
  defensive_note: string;
}
