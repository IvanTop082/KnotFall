import type { NodeEntry } from '@/api/models/nodeEntry.model'
import type { BreachPathGraphEdge } from '@/breachpath/graph-utils'
import { useBreachPathStore, useCanvasStore, useVisStore } from '@/stores'
import { getBreachPathNodeId } from '@/utils/breachpath-node-id'
import { useTuringContext } from '@turingcanvas'
import { useEffect, useMemo } from 'react'

const SELECTED_NODE_COLOR = 0xef4444
const DEFAULT_AFFECTED_NODE_COLOR = 0xf59e0b
const BLOCKED_EDGE_COLOR = 0x94a3b8
const REACHABLE_DEBUG_COLOR = 0x64748b
const SEVERITY_COLORS: Record<string, number> = {
  low: 0x60a5fa,
  medium: 0xf59e0b,
  high: 0xf97316,
  critical: 0xc084fc,
}

const SEVERITY_LEVELS: Record<string, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
}

function edgeKey(source: string | undefined, target: string | undefined) {
  return source && target ? `${source}->${target}` : undefined
}

function edgeBreachPathKey(
  edgeData: unknown,
  sourceId: string | undefined,
  targetId: string | undefined
) {
  const typedEdge = edgeData as BreachPathGraphEdge | undefined
  if (typedEdge?.source && typedEdge.target) return edgeKey(typedEdge.source, typedEdge.target)
  return edgeKey(sourceId, targetId)
}

export function BreachPathCanvasHighlighter() {
  const turing = useTuringContext()
  const selectedNode = useBreachPathStore((state) => state.selectedNode)
  const analysis = useBreachPathStore((state) => state.analysis)
  const animateExposurePaths = useBreachPathStore((state) => state.animateExposurePaths)
  const showAllReachable = useBreachPathStore((state) => state.showAllReachable)
  const entityCache = useVisStore((state) => state.entityCache)
  const canvasNodes = useCanvasStore((state) => state.nodes())
  const canvasEdges = useCanvasStore((state) => state.edges())

  const highlightedNodes = useMemo(
    () => new Set(analysis?.highlighted_nodes ?? []),
    [analysis?.highlighted_nodes]
  )

  const criticalTargets = useMemo(
    () =>
      new Set(
        analysis?.critical_nodes_reached?.length
          ? analysis.critical_nodes_reached
          : (analysis?.top_paths?.map((path) => path.target_node) ??
              analysis?.paths.map((path) => path.target) ??
              [])
      ),
    [analysis?.critical_nodes_reached, analysis?.paths, analysis?.top_paths]
  )

  const highlightedEdges = useMemo(
    () =>
      new Set(
        analysis?.highlighted_edges
          .flatMap((edge) => [edgeKey(edge.source, edge.target), edgeKey(edge.target, edge.source)])
          .filter((key) => key !== undefined)
    ),
    [analysis?.highlighted_edges]
  )

  const blockedEdges = useMemo(
    () =>
      new Set(
        analysis?.blocked_or_reduced_paths
          ?.flatMap((path) => path.edge_refs ?? [])
          .flatMap((edge) => [edgeKey(edge.source, edge.target), edgeKey(edge.target, edge.source)])
          .filter((key) => key !== undefined) ?? []
      ),
    [analysis?.blocked_or_reduced_paths]
  )

  const reachableNodes = useMemo(
    () => new Set(analysis?.traversal_explanation?.reachable_nodes ?? []),
    [analysis?.traversal_explanation?.reachable_nodes]
  )

  const reachableEdges = useMemo(
    () =>
      new Set(
        analysis?.traversal_explanation?.reachable_edges
          ?.flatMap((edge) => [edgeKey(edge.source, edge.target), edgeKey(edge.target, edge.source)])
          .filter((key) => key !== undefined) ?? []
      ),
    [analysis?.traversal_explanation?.reachable_edges]
  )

  const edgeSeverity = useMemo(() => {
    const severity = new Map<string, string>()
    for (const [key, value] of Object.entries(analysis?.visual_severity_by_edge ?? {})) {
      severity.set(key, value)
      const [source, target] = key.split('->')
      if (source && target) severity.set(`${target}->${source}`, value)
    }
    return severity
  }, [analysis?.visual_severity_by_edge])

  useEffect(() => {
    const nodeIdByCanvasId = new Map<number, string>()

    for (const node of canvasNodes) {
      const entry = entityCache.nodes.get(node.id) ?? (node.data as NodeEntry | undefined)
      const breachPathId = getBreachPathNodeId(entry).id
      if (breachPathId) nodeIdByCanvasId.set(node.id, breachPathId)
    }

    for (const node of canvasNodes) {
      const breachPathId = nodeIdByCanvasId.get(node.id)
      const isSelected =
        selectedNode !== undefined &&
        (selectedNode.canvasNodeId === node.id || selectedNode.breachPathNodeId === breachPathId)
      const isHighlighted = breachPathId !== undefined && highlightedNodes.has(breachPathId)
      const isReachable = breachPathId !== undefined && reachableNodes.has(breachPathId)
      const isCritical = breachPathId !== undefined && criticalTargets.has(breachPathId)
      const severity = breachPathId
        ? analysis?.visual_severity_by_node?.[breachPathId]
        : undefined
      const severityColor = severity ? SEVERITY_COLORS[severity] : undefined

      if (!selectedNode) {
        turing.instance.resetNodeColor(node)
        turing.instance.setNodeOpacity(node, 1)
        continue
      }

      if (isSelected) {
        turing.instance.setNodeColor(node, SELECTED_NODE_COLOR)
        turing.instance.setNodeOpacity(node, 1)
      } else if (isCritical) {
        turing.instance.setNodeColor(node, severityColor ?? SEVERITY_COLORS.critical)
        turing.instance.setNodeOpacity(node, 1)
      } else if (isHighlighted) {
        turing.instance.setNodeColor(node, severityColor ?? DEFAULT_AFFECTED_NODE_COLOR)
        turing.instance.setNodeOpacity(node, 0.95)
      } else if (analysis && showAllReachable && isReachable) {
        turing.instance.setNodeColor(node, REACHABLE_DEBUG_COLOR)
        turing.instance.setNodeOpacity(node, 0.55)
      } else {
        turing.instance.resetNodeColor(node)
        turing.instance.setNodeOpacity(node, analysis ? 0.18 : 0.32)
      }
    }

    for (const edge of canvasEdges) {
      const sourceId = nodeIdByCanvasId.get(edge.source.id)
      const targetId = nodeIdByCanvasId.get(edge.target.id)
      const currentEdgeKey = edgeBreachPathKey(edge.data, sourceId, targetId)
      const isHighlighted = currentEdgeKey !== undefined && highlightedEdges.has(currentEdgeKey)
      const isBlocked = currentEdgeKey !== undefined && blockedEdges.has(currentEdgeKey)
      const isReachable = currentEdgeKey !== undefined && reachableEdges.has(currentEdgeKey)
      const severity = currentEdgeKey ? edgeSeverity.get(currentEdgeKey) : undefined
      const severityColor = severity ? SEVERITY_COLORS[severity] : undefined

      if (!selectedNode) {
        turing.instance.setEdgeColor(edge, undefined)
        turing.instance.setEdgeOpacity(edge, 0.75)
        turing.instance.setEdgeExposureAnimation(edge, false, 0)
        continue
      }

      if (isHighlighted) {
        turing.instance.setEdgeColor(edge, severityColor ?? SEVERITY_COLORS.high)
        turing.instance.setEdgeOpacity(edge, 1)
        turing.instance.setEdgeExposureAnimation(
          edge,
          animateExposurePaths,
          SEVERITY_LEVELS[severity ?? 'high'] ?? 3
        )
      } else if (isBlocked) {
        turing.instance.setEdgeColor(edge, BLOCKED_EDGE_COLOR)
        turing.instance.setEdgeOpacity(edge, 0.45)
        turing.instance.setEdgeExposureAnimation(edge, false, 0)
      } else if (analysis && showAllReachable && isReachable) {
        turing.instance.setEdgeColor(edge, REACHABLE_DEBUG_COLOR)
        turing.instance.setEdgeOpacity(edge, 0.35)
        turing.instance.setEdgeExposureAnimation(edge, false, 0)
      } else {
        turing.instance.setEdgeColor(edge, undefined)
        turing.instance.setEdgeOpacity(edge, analysis ? 0.08 : 0.2)
        turing.instance.setEdgeExposureAnimation(edge, false, 0)
      }
    }
  }, [
    analysis,
    animateExposurePaths,
    blockedEdges,
    canvasEdges,
    canvasNodes,
    criticalTargets,
    entityCache,
    highlightedEdges,
    highlightedNodes,
    reachableEdges,
    reachableNodes,
    selectedNode,
    showAllReachable,
    turing,
    edgeSeverity,
  ])

  return null
}

export default BreachPathCanvasHighlighter
