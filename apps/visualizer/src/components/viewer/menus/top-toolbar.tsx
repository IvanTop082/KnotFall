import TuringButton from '@/components/base/turing-button'
import { buildGraphPayload, graphFingerprint } from '@/breachpath/graph-utils'
import { useBreachPathBuilderStore, useBreachPathStore, useCanvasStore, useVisStore } from '@/stores'
import { CenterForceSwitch } from './actions/center-force-switch'
import { NodeShapeSwitch } from './actions/node-shape-switch'

export const TuringTopToolBar = () => {
  const inspectNodeInfo = useVisStore((state) => state.inspectNodeInfo)
  const isNodeInspectorExtended = useVisStore((state) => state.isNodeInspectorExtended)
  const nodeInspectorExtendedWidth = useVisStore((state) => state.nodeInspectorExtendedWidth)
  const nodeInspectorCollapsedWidth = useVisStore((state) => state.nodeInspectorCollapsedWidth)
  const graphLoading = useVisStore((state) => state.graphLoading)
  const canvasNodes = useCanvasStore((state) => state.nodes())
  const canvasEdges = useCanvasStore((state) => state.edges())
  const builderDrawerOpen = useBreachPathBuilderStore((state) => state.builderDrawerOpen)
  const setBuilderDrawerOpen = useBreachPathBuilderStore((state) => state.setBuilderDrawerOpen)
  const selectedNode = useBreachPathStore((state) => state.selectedNode)
  const analysisStatus = useBreachPathStore((state) => state.status)
  const runAnalysisForSelectedNode = useBreachPathStore(
    (state) => state.runAnalysisForSelectedNode
  )

  const inspectorOffset = inspectNodeInfo
    ? isNodeInspectorExtended
      ? nodeInspectorExtendedWidth
      : nodeInspectorCollapsedWidth
    : 0
  const currentGraph = buildGraphPayload(canvasNodes, canvasEdges)
  const currentGraphHash = graphFingerprint(currentGraph)

  return (
    <div
      className="absolute top-0 m-4 transition-[left] duration-300"
      style={{ left: `${inspectorOffset}px` }}
    >
      <div className="flex items-center gap-2 rounded border border-grey-600 bg-grey-800/95 p-2 shadow-dark">
        <TuringButton
          icon="shield"
          intent="primary"
          highlight={builderDrawerOpen}
          loading={graphLoading}
          onClick={() => setBuilderDrawerOpen(!builderDrawerOpen)}
        >
          Network builder
        </TuringButton>

        <TuringButton
          icon="path-search"
          intent="success"
          disabled={!selectedNode || analysisStatus === 'loading'}
          loading={analysisStatus === 'loading'}
          onClick={() => runAnalysisForSelectedNode(currentGraph, currentGraphHash)}
        >
          Analyse selected
        </TuringButton>

        <div className="mx-1 h-6 border-l border-grey-600" />

        <CenterForceSwitch />
        <NodeShapeSwitch />

        <span className="ml-2 text-xs text-content-secondary">
          Build visually. Analyse defensively.
        </span>
      </div>
    </div>
  )
}
