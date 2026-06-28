import type { NodeEntry } from '@/api/models/nodeEntry.model'
import {
  getCompromisedNodeAnalysis,
  type BreachPathCompromisedNodeAnalysis,
  type BreachPathGraphPayload,
  type BreachPathSimulationType,
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
  simulationType: BreachPathSimulationType
  currentGraphHash: string | undefined
  lastAnalysisGraphHash: string | undefined
  currentGraphVersion: number
  lastAnalysisGraphVersion: number | undefined
  lastAnalysisSimulationType: BreachPathSimulationType | undefined
  selectNodeForAnalysis: (node: NodeEntry | undefined, canvasNodeId: number) => void
  setSimulationType: (simulationType: BreachPathSimulationType) => void
  setCurrentGraphHash: (graphHash: string) => void
  runAnalysisForNode: (
    node: NodeEntry | undefined,
    canvasNodeId: number,
    graph?: BreachPathGraphPayload,
    graphHash?: string,
    simulationType?: BreachPathSimulationType
  ) => Promise<boolean>
  runAnalysisForSelectedNode: (
    graph?: BreachPathGraphPayload,
    graphHash?: string,
    simulationType?: BreachPathSimulationType
  ) => Promise<boolean>
  clearAnalysis: () => void
}

export const useBreachPathStore = create<BreachPathStore>((set, get) => ({
  selectedNode: undefined,
  analysis: undefined,
  status: 'idle',
  error: undefined,
  simulationType: 'compromise',
  currentGraphHash: undefined,
  lastAnalysisGraphHash: undefined,
  currentGraphVersion: 0,
  lastAnalysisGraphVersion: undefined,
  lastAnalysisSimulationType: undefined,
  setSimulationType: (simulationType) => set({ simulationType }),
  setCurrentGraphHash: (graphHash) =>
    set((state) => {
      if (state.currentGraphHash === graphHash) return state

      return {
        currentGraphHash: graphHash,
        currentGraphVersion: state.currentGraphVersion + 1,
      }
    }),
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
  runAnalysisForNode: async (node, canvasNodeId, graph, graphHash, simulationType) => {
    get().selectNodeForAnalysis(node, canvasNodeId)
    return get().runAnalysisForSelectedNode(graph, graphHash, simulationType)
  },
  runAnalysisForSelectedNode: async (graph, graphHash, simulationType) => {
    const selectedNode = get().selectedNode
    const selectedSimulationType = simulationType ?? get().simulationType

    if (!selectedNode) {
      set({
        analysis: undefined,
        status: 'error',
        error: 'Select a device on the canvas first.',
      })
      return false
    }

    set({
      selectedNode,
      analysis: undefined,
      status: 'loading',
      error: undefined,
      simulationType: selectedSimulationType,
    })

    try {
      const analysis = graph
        ? await postCompromisedNodeAnalysis(
            selectedNode.breachPathNodeId,
            graph,
            selectedSimulationType
          )
        : await getCompromisedNodeAnalysis(selectedNode.breachPathNodeId)
      const currentSelectedNode = get().selectedNode

      if (
        currentSelectedNode?.canvasNodeId !== selectedNode.canvasNodeId ||
        currentSelectedNode.breachPathNodeId !== selectedNode.breachPathNodeId
      ) {
        return false
      }

      set({
        analysis,
        status: 'ready',
        error: undefined,
        lastAnalysisGraphHash: graphHash ?? get().currentGraphHash,
        lastAnalysisGraphVersion: get().currentGraphVersion,
        lastAnalysisSimulationType: selectedSimulationType,
      })
      return true
    } catch (error) {
      const currentSelectedNode = get().selectedNode
      if (
        currentSelectedNode?.canvasNodeId !== selectedNode.canvasNodeId ||
        currentSelectedNode.breachPathNodeId !== selectedNode.breachPathNodeId
      ) {
        return false
      }

      set({
        analysis: undefined,
        status: 'error',
        error: error instanceof Error ? error.message : 'Could not analyse this node.',
      })
      return false
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
