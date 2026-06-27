import type { NodeEntry } from '@/api/models/nodeEntry.model'
import {
  getCompromisedNodeAnalysis,
  type BreachPathCompromisedNodeAnalysis,
  type BreachPathGraphPayload,
  postCompromisedNodeAnalysis,
} from '@/api/breachpath'
import {
  getBreachPathNodeId,
  getBreachPathNodeLabel,
  getBreachPathNodeType,
} from '@/utils/breachpath-node-id'
import { create } from 'zustand'

export type BreachPathAnalysisStatus = 'idle' | 'loading' | 'ready' | 'error'

export type SelectedBreachPathNode = {
  canvasNodeId: number
  breachPathNodeId: string
  label: string
  nodeType?: string
  mappingNote?: string
}

export type BreachPathStore = {
  selectedNode: SelectedBreachPathNode | undefined
  analysis: BreachPathCompromisedNodeAnalysis | undefined
  status: BreachPathAnalysisStatus
  error: string | undefined
  selectNodeForAnalysis: (node: NodeEntry | undefined, canvasNodeId: number) => void
  runAnalysisForNode: (
    node: NodeEntry | undefined,
    canvasNodeId: number,
    graph?: BreachPathGraphPayload
  ) => Promise<void>
  clearAnalysis: () => void
}

export const useBreachPathStore = create<BreachPathStore>((set, get) => ({
  selectedNode: undefined,
  analysis: undefined,
  status: 'idle',
  error: undefined,
  selectNodeForAnalysis: (node, canvasNodeId) => {
    const nodeIdResult = getBreachPathNodeId(node)
    const selectedNode =
      nodeIdResult.id === undefined
        ? undefined
        : {
            canvasNodeId,
            breachPathNodeId: nodeIdResult.id,
            label: getBreachPathNodeLabel(node),
            nodeType: getBreachPathNodeType(node),
            mappingNote: nodeIdResult.note,
          }

    if (!selectedNode) {
      set({
        selectedNode: undefined,
        analysis: undefined,
        status: 'error',
        error: nodeIdResult.note,
      })
      return
    }

    set({
      selectedNode,
      analysis: undefined,
      status: 'idle',
      error: undefined,
    })
  },
  runAnalysisForNode: async (node, canvasNodeId, graph) => {
    get().selectNodeForAnalysis(node, canvasNodeId)
    const selectedNode = get().selectedNode

    if (!selectedNode) {
      return
    }

    set({
      selectedNode,
      analysis: undefined,
      status: 'loading',
      error: undefined,
    })

    try {
      const analysis = graph
        ? await postCompromisedNodeAnalysis(selectedNode.breachPathNodeId, graph)
        : await getCompromisedNodeAnalysis(selectedNode.breachPathNodeId)
      const currentSelectedNode = get().selectedNode

      if (
        currentSelectedNode?.canvasNodeId !== canvasNodeId ||
        currentSelectedNode.breachPathNodeId !== selectedNode.breachPathNodeId
      ) {
        return
      }

      set({
        analysis,
        status: 'ready',
        error: undefined,
      })
    } catch (error) {
      const currentSelectedNode = get().selectedNode
      if (
        currentSelectedNode?.canvasNodeId !== canvasNodeId ||
        currentSelectedNode.breachPathNodeId !== selectedNode.breachPathNodeId
      ) {
        return
      }

      set({
        analysis: undefined,
        status: 'error',
        error: error instanceof Error ? error.message : 'Could not analyse this node.',
      })
    }
  },
  clearAnalysis: () =>
    set({
      selectedNode: undefined,
      analysis: undefined,
      status: 'idle',
      error: undefined,
    }),
}))

export default useBreachPathStore
