import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from "reactflow";

import { getApiBaseUrl, getCompromisedAnalysis, getGraph } from "./api";
import { positionForNode } from "./graphLayout";
import type {
  CompromisedNodeAnalysis,
  GraphEdge,
  GraphNode,
  GraphResponse,
} from "./types";

function edgeKey(edge: { source: string; target: string }) {
  return `${edge.source}->${edge.target}`;
}

function nodeStyle(
  node: GraphNode,
  selectedNodeId: string | null,
  highlightedNodes: Set<string>,
  criticalTargets: Set<string>,
) {
  const isSelected = node.id === selectedNodeId;
  const isHighlighted = highlightedNodes.has(node.id);
  const isCritical = criticalTargets.has(node.id) || node.criticality >= 85;
  const shouldFade = selectedNodeId && !isSelected && !isHighlighted;

  if (isSelected) {
    return {
      background: "#7f1d1d",
      border: "2px solid #f87171",
      color: "#fee2e2",
      opacity: 1,
    };
  }

  if (isCritical && isHighlighted) {
    return {
      background: "#2e1065",
      border: "2px solid #c4b5fd",
      color: "#f5f3ff",
      opacity: 1,
    };
  }

  if (isHighlighted) {
    return {
      background: "#7c2d12",
      border: "2px solid #fb923c",
      color: "#ffedd5",
      opacity: 1,
    };
  }

  if (isCritical) {
    return {
      background: "#1e1b4b",
      border: "1px solid #8b5cf6",
      color: "#ddd6fe",
      opacity: shouldFade ? 0.35 : 1,
    };
  }

  return {
    background: "#101827",
    border: "1px solid #334155",
    color: "#e5e7eb",
    opacity: shouldFade ? 0.28 : 1,
  };
}

function buildFlowNodes(
  graphNodes: GraphNode[],
  selectedNodeId: string | null,
  analysis: CompromisedNodeAnalysis | null,
): Node[] {
  const rowByZone = new Map<string, number>();
  const highlightedNodes = new Set(analysis?.highlighted_nodes || []);
  const criticalTargets = new Set(analysis?.paths.map((path) => path.target) || []);

  return graphNodes.map((graphNode) => ({
    id: graphNode.id,
    position: positionForNode(graphNode, rowByZone),
    data: {
      label: (
        <div>
          <div className="node-title">{graphNode.label}</div>
          <div className="node-meta">
            {graphNode.type.replace("_", " ")} - C{graphNode.criticality}
          </div>
        </div>
      ),
    },
    style: nodeStyle(graphNode, selectedNodeId, highlightedNodes, criticalTargets),
  }));
}

function buildFlowEdges(
  graphEdges: GraphEdge[],
  selectedNodeId: string | null,
  analysis: CompromisedNodeAnalysis | null,
): Edge[] {
  const highlightedEdges = new Set(
    analysis?.highlighted_edges.map((edge) => edgeKey(edge)) || [],
  );

  return graphEdges.map((graphEdge) => {
    const isHighlighted = highlightedEdges.has(edgeKey(graphEdge));
    const shouldFade = selectedNodeId && !isHighlighted;

    return {
      id: graphEdge.id,
      source: graphEdge.source,
      target: graphEdge.target,
      label: graphEdge.relationship.replace("_", " "),
      animated: isHighlighted,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: isHighlighted ? "#fb923c" : "#64748b",
      },
      style: {
        stroke: isHighlighted ? "#fb923c" : "#475569",
        strokeWidth: isHighlighted ? 3 : 1.4,
        opacity: shouldFade ? 0.2 : 1,
      },
      labelStyle: {
        fill: isHighlighted ? "#fed7aa" : "#cbd5e1",
        fontSize: 11,
        fontWeight: 600,
      },
      labelBgStyle: {
        fill: isHighlighted ? "#431407" : "#0f172a",
        fillOpacity: 0.92,
      },
    };
  });
}

function AnalysisPanel({
  selectedNode,
  analysis,
  isLoading,
  error,
}: {
  selectedNode: GraphNode | null;
  analysis: CompromisedNodeAnalysis | null;
  isLoading: boolean;
  error: string | null;
}) {
  if (!selectedNode) {
    return (
      <aside className="analysis-panel empty-state">
        Select a suspected compromised node to analyse exposure paths.
      </aside>
    );
  }

  if (isLoading) {
    return (
      <aside className="analysis-panel empty-state">
        Running defensive exposure simulation...
      </aside>
    );
  }

  if (error) {
    return <aside className="analysis-panel error-state">Could not analyse this node. {error}</aside>;
  }

  if (!analysis) {
    return null;
  }

  const highestPath = analysis.paths[0];
  const criticalSystems = Array.from(new Set(analysis.paths.map((path) => path.target)));

  return (
    <aside className="analysis-panel">
      <div className="panel-section">
        <p className="eyebrow">Selected compromised node</p>
        <h2>{analysis.compromised_node.label}</h2>
        <p className="muted">
          {analysis.compromised_node.id} - {analysis.compromised_node.type}
        </p>
      </div>

      <div className={`risk-card ${analysis.summary.risk_level}`}>
        <span>Risk score</span>
        <strong>{analysis.summary.highest_risk_score}</strong>
        <em>{analysis.summary.risk_level}</em>
      </div>

      <div className="panel-grid">
        <div>
          <span>{analysis.summary.affected_node_count}</span>
          <p>affected nodes</p>
        </div>
        <div>
          <span>{analysis.summary.critical_assets_reachable}</span>
          <p>critical systems</p>
        </div>
      </div>

      <div className="panel-section">
        <h3>Reachable critical systems</h3>
        {criticalSystems.length ? (
          <ul>
            {criticalSystems.map((system) => (
              <li key={system}>{system}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">No critical systems reachable within the current search depth.</p>
        )}
      </div>

      {highestPath ? (
        <div className="panel-section">
          <h3>Highest-risk exposure path</h3>
          <p className="path-text">{highestPath.nodes.join(" -> ")}</p>
          <p className="muted">{highestPath.explanation}</p>
        </div>
      ) : null}

      <div className="panel-section">
        <h3>Recommended mitigations</h3>
        {analysis.recommendations.length ? (
          <div className="recommendation-list">
            {analysis.recommendations.map((recommendation) => (
              <article key={`${recommendation.title}-${recommendation.type}`}>
                <div>
                  <strong>{recommendation.title}</strong>
                  <span>{recommendation.priority}</span>
                </div>
                <p>{recommendation.explanation}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">No urgent mitigation recommendation returned for this node.</p>
        )}
      </div>

      <p className="defensive-note">{analysis.defensive_note}</p>
    </aside>
  );
}

export default function App() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<CompromisedNodeAnalysis | null>(null);
  const [isGraphLoading, setIsGraphLoading] = useState(true);
  const [isAnalysisLoading, setIsAnalysisLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const loadGraph = useCallback(async () => {
    setIsGraphLoading(true);
    setError(null);

    try {
      const graphResponse = await getGraph();
      setGraph(graphResponse);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load graph.");
    } finally {
      setIsGraphLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const selectedNode = useMemo(
    () => graph?.nodes.find((node) => node.id === selectedNodeId) || null,
    [graph, selectedNodeId],
  );

  const onNodeClick: NodeMouseHandler = useCallback(async (_event, node) => {
    setSelectedNodeId(node.id);
    setAnalysis(null);
    setAnalysisError(null);
    setIsAnalysisLoading(true);

    try {
      const response = await getCompromisedAnalysis(node.id);
      setAnalysis(response);
    } catch (analysisLoadError) {
      setAnalysisError(
        analysisLoadError instanceof Error
          ? analysisLoadError.message
          : "Could not analyse this node.",
      );
    } finally {
      setIsAnalysisLoading(false);
    }
  }, []);

  const flowNodes = useMemo(
    () => buildFlowNodes(graph?.nodes || [], selectedNodeId, analysis),
    [graph, selectedNodeId, analysis],
  );
  const flowEdges = useMemo(
    () => buildFlowEdges(graph?.edges || [], selectedNodeId, analysis),
    [graph, selectedNodeId, analysis],
  );

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Custom TuringDB-style workflow</p>
          <h1>BreachPath Visualizer</h1>
        </div>
        <div className="topbar-actions">
          <span>FastAPI brain: {getApiBaseUrl()}</span>
          <button type="button" onClick={loadGraph}>Reload graph</button>
        </div>
      </header>

      <section className="workspace">
        <div className="graph-shell">
          {isGraphLoading ? (
            <div className="center-message">Loading BreachPath graph...</div>
          ) : error ? (
            <div className="center-message error-state">Could not load graph. {error}</div>
          ) : (
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              onNodeClick={onNodeClick}
              fitView
              minZoom={0.3}
              maxZoom={1.8}
            >
              <MiniMap
                nodeColor={(node) =>
                  node.id === selectedNodeId ? "#ef4444" : "#334155"
                }
                maskColor="rgba(2, 6, 23, 0.75)"
              />
              <Controls />
              <Background color="#1e293b" gap={24} />
            </ReactFlow>
          )}
        </div>

        <AnalysisPanel
          selectedNode={selectedNode}
          analysis={analysis}
          isLoading={isAnalysisLoading}
          error={analysisError}
        />
      </section>
    </main>
  );
}
