import type { NodeEntry } from '@/api/models/nodeEntry.model'
import {
  getCompromisedNodeAnalysis,
  type BreachPathAnalysisMetadata,
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
  animateExposurePaths: boolean
  showAllReachable: boolean
  savedNetworkId: string | undefined
  savedNetworkName: string | undefined
  savedNetworkVersion: number | undefined
  lastSavedGraphHash: string | undefined
  hasUnsavedChanges: boolean
  previewVersion: number | undefined
  storageStatusLabel: string
  selectNodeForAnalysis: (node: NodeEntry | undefined, canvasNodeId: number) => void
  setSimulationType: (simulationType: BreachPathSimulationType) => void
  setCurrentGraphHash: (graphHash: string) => void
  setAnimateExposurePaths: (animate: boolean) => void
  setShowAllReachable: (show: boolean) => void
  setSavedNetworkVersion: (
    networkId: string,
    version: number | undefined,
    name?: string,
    graphHash?: string
  ) => void
  setNetworkName: (name: string) => void
  setPreviewVersion: (version: number | undefined) => void
  setStorageStatusLabel: (label: string) => void
  runAnalysisForNode: (
    node: NodeEntry | undefined,
    canvasNodeId: number,
    graph?: BreachPathGraphPayload,
    graphHash?: string,
    simulationType?: BreachPathSimulationType,
    metadata?: BreachPathAnalysisMetadata
  ) => Promise<boolean>
  runAnalysisForSelectedNode: (
    graph?: BreachPathGraphPayload,
    graphHash?: string,
    simulationType?: BreachPathSimulationType,
    metadata?: BreachPathAnalysisMetadata
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
  animateExposurePaths: true,
  showAllReachable: false,
  savedNetworkId: undefined,
  savedNetworkName: undefined,
  savedNetworkVersion: undefined,
  lastSavedGraphHash: undefined,
  hasUnsavedChanges: false,
  previewVersion: undefined,
  storageStatusLabel: 'Storage: Local fallback',
  setSimulationType: (simulationType) => set({ simulationType }),
  setAnimateExposurePaths: (animate) => set({ animateExposurePaths: animate }),
  setShowAllReachable: (show) => set({ showAllReachable: show }),
  setSavedNetworkVersion: (networkId, version, name, graphHash) =>
    set({
      savedNetworkId: networkId,
      savedNetworkName: name,
      savedNetworkVersion: version,
      lastSavedGraphHash: graphHash,
      hasUnsavedChanges: false,
      previewVersion: undefined,
    }),
  setNetworkName: (name) => set({ savedNetworkName: name }),
  setPreviewVersion: (version) => set({ previewVersion: version }),
  setStorageStatusLabel: (label) => set({ storageStatusLabel: label }),
  setCurrentGraphHash: (graphHash) =>
    set((state) => {
      if (state.currentGraphHash === graphHash) return state

      return {
        currentGraphHash: graphHash,
        currentGraphVersion: state.currentGraphVersion + 1,
        hasUnsavedChanges:
          state.lastSavedGraphHash !== undefined && state.lastSavedGraphHash !== graphHash,
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
  runAnalysisForNode: async (node, canvasNodeId, graph, graphHash, simulationType, metadata) => {
    get().selectNodeForAnalysis(node, canvasNodeId)
    return get().runAnalysisForSelectedNode(graph, graphHash, simulationType, metadata)
  },
  runAnalysisForSelectedNode: async (graph, graphHash, simulationType, metadata) => {
    const selectedNode = get().selectedNode
    const selectedSimulationType = simulationType ?? get().simulationType
    const analysisMetadata = metadata ?? {
      networkId: get().savedNetworkId,
      version: get().previewVersion ?? get().savedNetworkVersion,
      graphHash: graphHash ?? get().currentGraphHash,
    }

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
            selectedSimulationType,
            analysisMetadata
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
        lastAnalysisGraphVersion:
          analysis.version ?? analysisMetadata.version ?? get().currentGraphVersion,
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
