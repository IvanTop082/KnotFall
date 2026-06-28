import type { NodeEntry } from '@/api/models/nodeEntry.model'
import type { BreachPathGraphEdge } from '@/breachpath/graph-utils'
import { useBreachPathStore, useCanvasStore, useVisStore } from '@/stores'
import { getBreachPathNodeId } from '@/utils/breachpath-node-id'
import { useTuringContext } from '@turingcanvas'
import { useEffect, useMemo } from 'react'

const SELECTED_NODE_COLOR = 0xef4444
const DEFAULT_AFFECTED_NODE_COLOR = 0xf59e0b
const RELATED_EDGE_COLOR = 0xfbbf24
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
  const entityCache = useVisStore((state) => state.entityCache)
  const canvasNodes = useCanvasStore((state) => state.nodes())
  const canvasEdges = useCanvasStore((state) => state.edges())

  const highlightedNodes = useMemo(
    () => new Set(analysis?.highlighted_nodes ?? []),
    [analysis?.highlighted_nodes]
  )

  const criticalTargets = useMemo(
    () => new Set(analysis?.paths.map((path) => path.target) ?? []),
    [analysis?.paths]
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
      const sourceHighlighted = sourceId !== undefined && highlightedNodes.has(sourceId)
      const targetHighlighted = targetId !== undefined && highlightedNodes.has(targetId)
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
      } else if (analysis && sourceHighlighted && targetHighlighted) {
        turing.instance.setEdgeColor(edge, RELATED_EDGE_COLOR)
        turing.instance.setEdgeOpacity(edge, 0.65)
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
    canvasEdges,
    canvasNodes,
    criticalTargets,
    entityCache,
    highlightedEdges,
    highlightedNodes,
    selectedNode,
    turing,
    edgeSeverity,
  ])

  return null
}

export default BreachPathCanvasHighlighter
