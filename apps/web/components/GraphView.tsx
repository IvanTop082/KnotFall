"use client";

import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  type Edge,
  type Node,
} from "reactflow";

import type { AttackPathResult, GraphEdge, GraphNode } from "../lib/types";

interface GraphViewProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string;
  attackPathResults: AttackPathResult[];
}

const zoneOrder = [
  "user_zone",
  "server_zone",
  "identity_zone",
  "operations_zone",
  "security_zone",
];

const zoneLabels: Record<string, string> = {
  user_zone: "User",
  server_zone: "Server",
  identity_zone: "Identity",
  operations_zone: "Operations",
  security_zone: "Security",
};

function buildPathSets(results: AttackPathResult[]) {
  const pathNodeIds = new Set<string>();
  const criticalAssetIds = new Set<string>();
  const pathEdgeKeys = new Set<string>();

  for (const result of results) {
    criticalAssetIds.add(result.asset_id);

    result.path_node_ids.forEach((nodeId) => pathNodeIds.add(nodeId));

    for (let index = 0; index < result.path_node_ids.length - 1; index += 1) {
      const source = result.path_node_ids[index];
      const target = result.path_node_ids[index + 1];
      pathEdgeKeys.add(`${source}->${target}`);
    }
  }

  return { pathNodeIds, criticalAssetIds, pathEdgeKeys };
}

function getNodeStyle(
  node: GraphNode,
  selectedNodeId: string,
  pathNodeIds: Set<string>,
  criticalAssetIds: Set<string>,
) {
  if (node.id === selectedNodeId) {
    return {
      background: "#7f1d1d",
      border: "2px solid #ef4444",
      color: "#fee2e2",
    };
  }

  if (criticalAssetIds.has(node.id)) {
    return {
      background: "#2e1065",
      border: "2px solid #a78bfa",
      color: "#f5f3ff",
    };
  }

  if (pathNodeIds.has(node.id)) {
    return {
      background: "#7c2d12",
      border: "2px solid #fb923c",
      color: "#ffedd5",
    };
  }

  return {
    background: "#111827",
    border: "1px solid #334155",
    color: "#e5e7eb",
  };
}

function layoutNodes(nodes: GraphNode[]): Node[] {
  const rowsByZone = new Map<string, number>();

  return nodes.map((graphNode) => {
    const zoneIndex = Math.max(zoneOrder.indexOf(graphNode.zone), 0);
    const row = rowsByZone.get(graphNode.zone) || 0;
    rowsByZone.set(graphNode.zone, row + 1);

    return {
      id: graphNode.id,
      position: {
        x: zoneIndex * 260,
        y: row * 135,
      },
      data: {
        label: (
          <div>
            <div className="text-sm font-semibold">{graphNode.label}</div>
            <div className="mt-1 text-[10px] uppercase opacity-70">
              {zoneLabels[graphNode.zone] || graphNode.zone} · C
              {graphNode.criticality}
            </div>
          </div>
        ),
      },
    };
  });
}

export default function GraphView({
  nodes,
  edges,
  selectedNodeId,
  attackPathResults,
}: GraphViewProps) {
  const { pathNodeIds, criticalAssetIds, pathEdgeKeys } =
    buildPathSets(attackPathResults);

  const flowNodes = layoutNodes(nodes).map((flowNode) => {
    const graphNode = nodes.find((node) => node.id === flowNode.id);

    return {
      ...flowNode,
      style: graphNode
        ? getNodeStyle(
            graphNode,
            selectedNodeId,
            pathNodeIds,
            criticalAssetIds,
          )
        : undefined,
    };
  });

  const flowEdges: Edge[] = edges.map((edge) => {
    const isHighlighted = pathEdgeKeys.has(`${edge.source}->${edge.target}`);

    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.relationship.replace("_", " "),
      animated: isHighlighted,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: isHighlighted ? "#f97316" : "#64748b",
      },
      style: {
        stroke: isHighlighted ? "#f97316" : "#475569",
        strokeWidth: isHighlighted ? 3 : 1.5,
      },
      labelStyle: {
        fill: isHighlighted ? "#fed7aa" : "#cbd5e1",
        fontSize: 11,
        fontWeight: 600,
      },
      labelBgStyle: {
        fill: isHighlighted ? "#431407" : "#0f172a",
        fillOpacity: 0.9,
      },
    };
  });

  return (
    <section className="h-[720px] overflow-hidden rounded-lg border border-slate-800 bg-[#080b12]">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        fitView
        minZoom={0.3}
        maxZoom={1.8}
      >
        <MiniMap
          nodeColor={(node) =>
            node.id === selectedNodeId
              ? "#ef4444"
              : criticalAssetIds.has(node.id)
                ? "#8b5cf6"
                : pathNodeIds.has(node.id)
                  ? "#f97316"
                  : "#334155"
          }
          maskColor="rgba(2, 6, 23, 0.7)"
        />
        <Controls />
        <Background color="#1e293b" gap={24} />
      </ReactFlow>
    </section>
  );
}
