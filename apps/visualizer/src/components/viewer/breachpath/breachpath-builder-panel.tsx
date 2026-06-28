import type { NodeEntry } from '@/api/models/nodeEntry.model'
import {
  compareBreachPathNetworkVersions,
  deleteBreachPathNetwork,
  getBreachPathStorageStatus,
  listBreachPathNetworks,
  loadBreachPathNetwork,
  loadBreachPathNetworkVersion,
  restoreBreachPathNetworkVersion,
  saveBreachPathNetworkVersionForNetwork,
  listBreachPathNetworkVersions,
  type BreachPathNetworkCommit,
  type BreachPathNetworkCompare,
} from '@/api/breachpath'
import {
  CYBER_EDGE_TEMPLATES,
  CYBER_NODE_TEMPLATES,
  getCriticalityHelp,
  getEdgeTemplate,
  getImpactExplanation,
  getNodeTemplate,
  suggestEdgeTypes,
  type Criticality,
} from '@/breachpath/cyber-templates'
import { EXAMPLE_NETWORKS } from '@/breachpath/example-networks'
import {
  buildGraphPayload,
  compareGraphs,
  createEdgeData,
  createNodeEntryFromGraphNode,
  createNodeEntryFromTemplate,
  deleteLocalNetwork,
  downloadGraph,
  getLatestLocalNetworkVersion,
  getLocalNetworkVersion,
  graphFingerprint,
  listLocalNetworks,
  loadLocalNetwork,
  loadGraphFromLocalStorage,
  nextCanvasId,
  nextEdgeId,
  nextNodeSlug,
  networkIdFromName,
  nodeEntryToGraphNode,
  renameLocalNetwork,
  restoreLocalNetworkVersion,
  saveLocalNetworkVersion,
  saveGraphToLocalStorage,
  type BreachPathGraphPayload,
  type BreachPathLocalNetworkSummary,
} from '@/breachpath/graph-utils'
import {
  useAppStore,
  useBreachPathBuilderStore,
  useBreachPathStore,
  useCanvasStore,
  useVisStore,
} from '@/stores'
import { useTuringContext } from '@turingcanvas'
import { Icon } from '@blueprintjs/core'
import { useEffect, useMemo, useRef, useState } from 'react'

function shorten(text: string, max = 26) {
  return text.length > max ? `${text.slice(0, max - 3)}...` : text
}

function formatDateTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export function BreachPathBuilderPanel() {
  const turing = useTuringContext()
  const canvasActions = useCanvasStore((state) => state.actions)
  const canvasNodes = useCanvasStore((state) => state.nodes())
  const canvasEdges = useCanvasStore((state) => state.edges())
  const resetCanvasStates = useCanvasStore((state) => state.resetStates)
  const entityCache = useVisStore((state) => state.entityCache)
  const neighbourhood = useVisStore((state) => state.neighbourhood)
  const graphName = useAppStore((state) => state.graphName)
  const selectedNode = useBreachPathStore((state) => state.selectedNode)
  const simulationType = useBreachPathStore((state) => state.simulationType)
  const hasUnsavedChanges = useBreachPathStore((state) => state.hasUnsavedChanges)
  const savedNetworkVersion = useBreachPathStore((state) => state.savedNetworkVersion)
  const previewVersion = useBreachPathStore((state) => state.previewVersion)
  const setSavedNetworkVersion = useBreachPathStore((state) => state.setSavedNetworkVersion)
  const setNetworkNameInStore = useBreachPathStore((state) => state.setNetworkName)
  const setPreviewVersion = useBreachPathStore((state) => state.setPreviewVersion)
  const setStorageStatusLabel = useBreachPathStore((state) => state.setStorageStatusLabel)
  const setCurrentGraphHash = useBreachPathStore((state) => state.setCurrentGraphHash)
  const selectNodeForAnalysis = useBreachPathStore((state) => state.selectNodeForAnalysis)
  const runAnalysisForSelectedNode = useBreachPathStore(
    (state) => state.runAnalysisForSelectedNode
  )
  const clearAnalysis = useBreachPathStore((state) => state.clearAnalysis)
  const builderDrawerOpen = useBreachPathBuilderStore((state) => state.builderDrawerOpen)
  const setBuilderDrawerOpen = useBreachPathBuilderStore((state) => state.setBuilderDrawerOpen)
  const activePanel = useBreachPathBuilderStore((state) => state.activePanel)
  const setActivePanel = useBreachPathBuilderStore((state) => state.setActivePanel)
  const nodeCreatorOpen = useBreachPathBuilderStore((state) => state.nodeCreatorOpen)
  const setNodeCreatorOpen = useBreachPathBuilderStore((state) => state.setNodeCreatorOpen)
  const localBuilderMode = useBreachPathBuilderStore((state) => state.localBuilderMode)
  const setLocalBuilderMode = useBreachPathBuilderStore((state) => state.setLocalBuilderMode)
  const statusMessage = useBreachPathBuilderStore((state) => state.statusMessage)
  const setStatusMessage = useBreachPathBuilderStore((state) => state.setStatusMessage)

  const [templateId, setTemplateId] = useState('laptop')
  const [nodeLabel, setNodeLabel] = useState('')
  const [nodeCriticality, setNodeCriticality] = useState<Criticality>('medium')
  const [nodeZone, setNodeZone] = useState('home')
  const [nodeInternetExposed, setNodeInternetExposed] = useState(false)
  const [nodeHasAdminPrivileges, setNodeHasAdminPrivileges] = useState(false)
  const [nodeNotes, setNodeNotes] = useState('')
  const [selectedNodeLabelDraft, setSelectedNodeLabelDraft] = useState('')
  const [selectedNodeCriticalityDraft, setSelectedNodeCriticalityDraft] =
    useState<Criticality>('medium')
  const [selectedNodeZoneDraft, setSelectedNodeZoneDraft] = useState('internal')
  const [exampleNetworkId, setExampleNetworkId] = useState('basic-home-network')
  const [networkId, setNetworkId] = useState('home_network')
  const [networkName, setNetworkName] = useState('My Home Network')
  const [commitMessage, setCommitMessage] = useState('Saved network update')
  const [versionHistory, setVersionHistory] = useState<BreachPathNetworkCommit[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [compareResult, setCompareResult] = useState<BreachPathNetworkCompare | undefined>()
  const [localNetworks, setLocalNetworks] = useState<BreachPathLocalNetworkSummary[]>([])
  const [backendNetworkCount, setBackendNetworkCount] = useState<number | undefined>()
  const [sourceCanvasId, setSourceCanvasId] = useState('')
  const [targetCanvasId, setTargetCanvasId] = useState('')
  const [edgeType, setEdgeType] = useState('can_access')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const selectedTemplate = useMemo(() => getNodeTemplate(templateId), [templateId])
  const selectedExampleNetwork = useMemo(
    () => EXAMPLE_NETWORKS.find((example) => example.id === exampleNetworkId),
    [exampleNetworkId]
  )
  const criticalityHelp = useMemo(() => getCriticalityHelp(templateId), [templateId])
  const impactExplanation = useMemo(() => getImpactExplanation(templateId), [templateId])

  useEffect(() => {
    if (!selectedTemplate) return

    setNodeCriticality(selectedTemplate.criticality)
    setNodeZone(selectedTemplate.zone)
    setNodeInternetExposed(selectedTemplate.is_internet_exposed)
    setNodeHasAdminPrivileges(selectedTemplate.has_admin_privileges)
    setNodeNotes(selectedTemplate.notes)
  }, [selectedTemplate])

  useEffect(() => {
    if (!selectedNode) return

    const canvasNode = turing.instance.nodeMap.get(selectedNode.canvasNodeId)
    const nodeEntry =
      (canvasNode?.data as NodeEntry | undefined) ??
      (entityCache.nodes.get(selectedNode.canvasNodeId) as NodeEntry | undefined)
    const graphNode = nodeEntryToGraphNode(nodeEntry)

    setSelectedNodeLabelDraft(graphNode.label)
    setSelectedNodeCriticalityDraft(graphNode.criticality as Criticality)
    setSelectedNodeZoneDraft(graphNode.zone)
  }, [entityCache.nodes, selectedNode, turing.instance.nodeMap])

  const graphNodes = useMemo(
    () =>
      canvasNodes.map((node) => ({
        canvasId: node.id,
        graphNode: nodeEntryToGraphNode(node.data as NodeEntry),
      })),
    [canvasNodes]
  )
  const graphPayload = useMemo(
    () => buildGraphPayload(canvasNodes, canvasEdges),
    [canvasNodes, canvasEdges]
  )
  const graphHash = useMemo(() => graphFingerprint(graphPayload), [graphPayload])
  const latestHistoryVersion = useMemo(
    () => Math.max(0, ...versionHistory.map((version) => version.version)),
    [versionHistory]
  )
  const activeSavedVersion = savedNetworkVersion ?? (latestHistoryVersion || undefined)
  const isReadOnlyPreview =
    previewVersion !== undefined &&
    activeSavedVersion !== undefined &&
    previewVersion !== activeSavedVersion

  useEffect(() => {
    setCurrentGraphHash(graphHash)
  }, [graphHash, setCurrentGraphHash])

  useEffect(() => {
    setNetworkNameInStore(networkName)
  }, [networkName, setNetworkNameInStore])

  const refreshLocalNetworkLibrary = () => {
    setLocalNetworks(listLocalNetworks())
  }

  useEffect(() => {
    refreshLocalNetworkLibrary()
  }, [])

  useEffect(() => {
    let cancelled = false

    getBreachPathStorageStatus()
      .then((status) => {
        if (cancelled) return
        setStorageStatusLabel(
          status.status === 'connected'
            ? 'Storage: TuringDB connected'
            : 'Storage: Local fallback'
        )
      })
      .catch(() => {
        if (!cancelled) setStorageStatusLabel('Storage: Local fallback')
      })

    return () => {
      cancelled = true
    }
  }, [setStorageStatusLabel])

  useEffect(() => {
    let cancelled = false

    listBreachPathNetworks()
      .then((networks) => {
        if (!cancelled) setBackendNetworkCount(networks.length)
      })
      .catch(() => {
        if (!cancelled) setBackendNetworkCount(undefined)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const sourceNode = useMemo(
    () => graphNodes.find((node) => String(node.canvasId) === sourceCanvasId),
    [graphNodes, sourceCanvasId]
  )
  const targetNode = useMemo(
    () => graphNodes.find((node) => String(node.canvasId) === targetCanvasId),
    [graphNodes, targetCanvasId]
  )

  const suggestedEdgeTypes = useMemo(() => {
    return suggestEdgeTypes(sourceNode?.graphNode.node_type, targetNode?.graphNode.node_type)
  }, [sourceNode?.graphNode.node_type, targetNode?.graphNode.node_type])

  const enterLocalMode = () => {
    setLocalBuilderMode(true)
    if (graphName) neighbourhood.reset(graphName)
  }

  const setNodeLabelOnCanvas = (canvasId: number, label: string) => {
    const canvasNode = turing.instance.nodeMap.get(canvasId)
    if (canvasNode) turing.instance.setNodeLabel(canvasNode, label)
  }

  const setEdgeLabelOnCanvas = (edgeId: number, label: string) => {
    const canvasEdge = turing.instance.edgeMap.get(edgeId)
    if (canvasEdge) turing.instance.setEdgeLabel(canvasEdge, label)
  }

  const newNetwork = () => {
    const nextName = window.prompt('New network name', 'Home Network')?.trim() || 'Untitled Network'
    const nextNetworkId = networkIdFromName(nextName)

    enterLocalMode()
    clearAnalysis()
    setPreviewVersion(undefined)
    setNetworkId(nextNetworkId)
    setNetworkName(nextName)
    setSavedNetworkVersion(nextNetworkId, undefined, nextName, undefined)
    setVersionHistory([])
    setCompareResult(undefined)
    entityCache.nodes.clear()
    entityCache.edges.clear()
    canvasActions.reset()
    setStatusMessage(`Started new network: ${nextName}. Add nodes, then Save version.`)
  }

  const addNode = () => {
    if (isReadOnlyPreview) {
      setStatusMessage('Restore this version or load the latest version before editing.')
      return
    }

    const template = getNodeTemplate(templateId)
    if (!template) return

    enterLocalMode()

    const canvasId = nextCanvasId(canvasNodes)
    const label = nodeLabel.trim() || template.title
    const breachPathId = nextNodeSlug(template, canvasNodes)
    const nodeEntry = createNodeEntryFromTemplate(canvasId, template, label, breachPathId, {
      criticality: nodeCriticality,
      zone: nodeZone,
      is_internet_exposed: nodeInternetExposed,
      has_admin_privileges: nodeHasAdminPrivileges,
      notes: nodeNotes,
    })

    entityCache.nodes.set(canvasId, nodeEntry)
    canvasActions.addNodes([{ id: canvasId, primary: true, data: nodeEntry }])
    setNodeLabelOnCanvas(canvasId, `${template.icon} ${label}`)
    setNodeLabel('')
    setNodeCreatorOpen(false)
    setStatusMessage(`Added ${label}.`)
  }

  const updateSelectedNodeDetails = () => {
    if (!selectedNode) {
      setStatusMessage('Select a node on the canvas before editing.')
      return
    }

    const canvasNode = turing.instance.nodeMap.get(selectedNode.canvasNodeId)
    const existingEntry =
      (canvasNode?.data as NodeEntry | undefined) ??
      (entityCache.nodes.get(selectedNode.canvasNodeId) as NodeEntry | undefined)

    if (!existingEntry) {
      setStatusMessage('Selected node data was not available for editing.')
      return
    }

    const updatedEntry: NodeEntry = {
      ...existingEntry,
      properties: {
        ...existingEntry.properties,
        label: selectedNodeLabelDraft.trim() || selectedNode.label,
        criticality: selectedNodeCriticalityDraft,
        zone: selectedNodeZoneDraft.trim() || 'internal',
      },
    }

    if (canvasNode) canvasNode.data = updatedEntry
    entityCache.nodes.set(selectedNode.canvasNodeId, updatedEntry)
    setNodeLabelOnCanvas(selectedNode.canvasNodeId, updatedEntry.properties.label)
    selectNodeForAnalysis(updatedEntry, selectedNode.canvasNodeId)
    resetCanvasStates('nodes', 'nodeMap', 'selectedNodes')
    setStatusMessage(`Updated ${updatedEntry.properties.label}.`)
  }

  const addTypedEdge = () => {
    if (isReadOnlyPreview) {
      setStatusMessage('Restore this version or load the latest version before editing.')
      return
    }

    const source = sourceNode
    const target = targetNode
    const template = getEdgeTemplate(edgeType)

    if (!source || !target || !template || source.canvasId === target.canvasId) {
      setStatusMessage('Choose two different nodes and an edge type before connecting.')
      return
    }

    enterLocalMode()

    const edgeId = nextEdgeId(canvasEdges)
    const edgeData = createEdgeData(edgeId, source.graphNode, target.graphNode, template)

    canvasActions.addEdges([
      {
        id: edgeId,
        src: source.canvasId,
        tgt: target.canvasId,
        data: edgeData,
      },
    ])
    setEdgeLabelOnCanvas(edgeId, template.label)
    setStatusMessage(`Connected ${source.graphNode.label} to ${target.graphNode.label}.`)
  }

  const currentGraph = () => graphPayload

  const refreshVersionHistory = async (
    targetNetworkId = networkId,
    syncLatestVersion = true
  ) => {
    setHistoryLoading(true)
    try {
      const localNetwork = loadLocalNetwork(targetNetworkId)
      const localHistory: BreachPathNetworkCommit[] =
        localNetwork?.versions
          .map((version) => ({
            commit_id: version.commit_id,
            version: version.version,
            message: version.message,
            created_at: version.created_at,
            node_count: version.node_count,
            edge_count: version.edge_count,
            analysed: Boolean(version.analysed),
            analysis_count: version.analysis_count ?? 0,
          }))
          .sort((first, second) => second.version - first.version) ?? []
      let history = localHistory

      try {
        const backendHistory = await listBreachPathNetworkVersions(targetNetworkId)
        if (backendHistory.length > history.length) history = backendHistory
      } catch {
        // Local version history remains the reliable browser fallback.
      }

      setVersionHistory(history)
      const latestVersion = Math.max(0, ...history.map((version) => version.version))
      if (syncLatestVersion && latestVersion > 0) {
        const latestLocalVersion = localNetwork
          ? getLatestLocalNetworkVersion(localNetwork)
          : undefined
        setSavedNetworkVersion(
          targetNetworkId,
          latestVersion,
          localNetwork?.name,
          latestLocalVersion?.graph_hash
        )
      }
      return history
    } finally {
      setHistoryLoading(false)
    }
  }

  const resolveNetworkIdentity = () => {
    const resolvedName =
      networkName.trim() ||
      window.prompt('Network name', 'Home Network')?.trim() ||
      'BreachPath Network'
    const resolvedNetworkId = networkId.trim() || networkIdFromName(resolvedName)

    setNetworkName(resolvedName)
    setNetworkId(resolvedNetworkId)
    return {
      networkId: resolvedNetworkId,
      name: resolvedName,
    }
  }

  const saveCurrentVersion = async (defaultMessage = 'Saved network update') => {
    if (isReadOnlyPreview) {
      setStatusMessage('Read-only preview: use Restore to create a new latest version from this graph.')
      return false
    }

    try {
      const identity = resolveNetworkIdentity()
      const message =
        commitMessage.trim() ||
        window.prompt('Version message', defaultMessage)?.trim() ||
        defaultMessage
      const localSave = saveLocalNetworkVersion({
        networkId: identity.networkId,
        name: identity.name,
        graph: currentGraph(),
        message,
      })

      setNetworkId(localSave.network.network_id)
      setNetworkName(localSave.network.name)
      setCommitMessage(message)
      setSavedNetworkVersion(
        localSave.network.network_id,
        localSave.version.version,
        localSave.network.name,
        localSave.version.graph_hash
      )
      setPreviewVersion(undefined)
      refreshLocalNetworkLibrary()
      await refreshVersionHistory(localSave.network.network_id, false)

      try {
        const response = await saveBreachPathNetworkVersionForNetwork({
          networkId: localSave.network.network_id,
          name: localSave.network.name,
          graph: currentGraph(),
          message,
        })
        const warning = response.warning ? ` ${response.warning}` : ''
        setStatusMessage(
          `Network saved locally as v${localSave.version.version}. Backend ${response.storage_backend}.${warning}`
        )
      } catch (backendError) {
        setStatusMessage(
          `Network saved locally as v${localSave.version.version}. Backend/TuringDB not available, using local fallback.`
        )
      }

      return true
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : 'Could not save network.')
      return false
    }
  }

  const saveToBackend = async () => {
    await saveCurrentVersion('Saved network update')
  }

  const loadFromBackend = async () => {
    const localNetwork = loadLocalNetwork(networkId)
    const latestLocalVersion = localNetwork ? getLatestLocalNetworkVersion(localNetwork) : undefined

    if (localNetwork && latestLocalVersion) {
      loadGraph(latestLocalVersion.graph)
      setNetworkId(localNetwork.network_id)
      setNetworkName(localNetwork.name)
      setSavedNetworkVersion(
        localNetwork.network_id,
        latestLocalVersion.version,
        localNetwork.name,
        latestLocalVersion.graph_hash
      )
      setPreviewVersion(undefined)
      await refreshVersionHistory(localNetwork.network_id, false)
      setStatusMessage(`Loaded ${localNetwork.name} v${latestLocalVersion.version}.`)
      return
    }

    try {
      const saved = await loadBreachPathNetwork(networkId)
      loadGraph(saved.graph)
      setNetworkId(saved.network_id)
      setNetworkName(saved.name)
      setSavedNetworkVersion(saved.network_id, saved.version, saved.name, graphFingerprint(saved.graph))
      setPreviewVersion(undefined)
      await refreshVersionHistory(saved.network_id, false)
      setStatusMessage(`Loaded ${saved.name} v${saved.version} from backend.`)
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : 'Could not load network.')
    }
  }

  const loadNetworkFromLibrary = async (targetNetworkId: string) => {
    const localNetwork = loadLocalNetwork(targetNetworkId)
    const latestLocalVersion = localNetwork ? getLatestLocalNetworkVersion(localNetwork) : undefined

    if (!localNetwork || !latestLocalVersion) {
      setStatusMessage(`Saved network not found locally: ${targetNetworkId}`)
      return
    }

    loadGraph(latestLocalVersion.graph)
    setNetworkId(localNetwork.network_id)
    setNetworkName(localNetwork.name)
    setSavedNetworkVersion(
      localNetwork.network_id,
      latestLocalVersion.version,
      localNetwork.name,
      latestLocalVersion.graph_hash
    )
    setPreviewVersion(undefined)
    setCompareResult(undefined)
    await refreshVersionHistory(localNetwork.network_id, false)
    setStatusMessage(`Loaded ${localNetwork.name} v${latestLocalVersion.version}.`)
  }

  const renameCurrentNetwork = () => {
    const nextName = window.prompt('Rename network', networkName)?.trim()
    if (!nextName) return

    try {
      if (loadLocalNetwork(networkId)) renameLocalNetwork(networkId, nextName)
      setNetworkName(nextName)
      setNetworkNameInStore(nextName)
      refreshLocalNetworkLibrary()
      setStatusMessage(`Renamed current network to ${nextName}.`)
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : 'Could not rename network.')
    }
  }

  const deleteNetworkFromLibrary = async (targetNetworkId: string) => {
    const localNetwork = loadLocalNetwork(targetNetworkId)
    const label = localNetwork?.name ?? targetNetworkId
    const confirmed = window.confirm(`Delete ${label}? This removes the local saved history.`)
    if (!confirmed) return

    deleteLocalNetwork(targetNetworkId)
    refreshLocalNetworkLibrary()
    setVersionHistory([])
    setCompareResult(undefined)

    try {
      await deleteBreachPathNetwork(targetNetworkId)
    } catch {
      // Backend delete is best-effort; local delete is the visible source of truth.
    }

    if (targetNetworkId === networkId) {
      setSavedNetworkVersion(targetNetworkId, undefined, undefined, undefined)
    }

    setStatusMessage(`Deleted ${label} from local Network Library.`)
  }

  const loadVersionPreview = async (version: number) => {
    const localSnapshot = getLocalNetworkVersion(networkId, version)
    if (localSnapshot) {
      const selectedNodeId = selectedNode?.breachPathNodeId
      loadGraph(localSnapshot.graph, selectedNodeId)
      setPreviewVersion(localSnapshot.version)
      setStatusMessage(`Viewing v${localSnapshot.version}. This is not the latest version.`)
      return {
        network_id: networkId,
        name: networkName,
        graph: localSnapshot.graph,
        version: localSnapshot.version,
        graph_hash: localSnapshot.graph_hash,
      }
    }

    const snapshot = await loadBreachPathNetworkVersion(networkId, version)
    const selectedNodeId = selectedNode?.breachPathNodeId
    loadGraph(snapshot.graph, selectedNodeId)
    setNetworkId(snapshot.network_id)
    setNetworkName(snapshot.name)
    setPreviewVersion(snapshot.version)
    setStatusMessage(`Viewing read-only preview of ${snapshot.name} v${snapshot.version}.`)
    return snapshot
  }

  const restoreVersion = async (version: number) => {
    const confirmed = window.confirm(
      `Restore version ${version}? This creates a new latest version and keeps history intact.`
    )
    if (!confirmed) return

    try {
      const localRestore = restoreLocalNetworkVersion(networkId, version)
      loadGraph(localRestore.version.graph, selectedNode?.breachPathNodeId)
      setNetworkId(localRestore.network.network_id)
      setNetworkName(localRestore.network.name)
      setSavedNetworkVersion(
        localRestore.network.network_id,
        localRestore.version.version,
        localRestore.network.name,
        localRestore.version.graph_hash
      )
      setPreviewVersion(undefined)
      refreshLocalNetworkLibrary()
      await refreshVersionHistory(localRestore.network.network_id, false)

      try {
        await restoreBreachPathNetworkVersion(networkId, version)
      } catch {
        // Backend restore is best-effort; local restore is already complete.
      }

      setStatusMessage(`Restored v${version} as new version ${localRestore.version.version}.`)
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : 'Could not restore version.')
    }
  }

  const analyseVersion = async (version: number) => {
    if (!selectedNode) {
      setStatusMessage('Select a device on the canvas first.')
      await runAnalysisForSelectedNode(currentGraph(), graphHash, simulationType)
      return
    }

    try {
      const snapshot = await loadVersionPreview(version)
      const snapshotHash = graphFingerprint(snapshot.graph)
      const didRun = await runAnalysisForSelectedNode(
        snapshot.graph,
        snapshotHash,
        simulationType,
        {
          networkId: snapshot.network_id,
          version: snapshot.version,
          graphHash: snapshotHash,
        }
      )
      await refreshVersionHistory(snapshot.network_id, false)
      setStatusMessage(
        didRun
          ? `Analysis complete for v${snapshot.version}.`
          : 'Analysis failed. Check that the backend is running at http://localhost:8000.'
      )
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : 'Could not analyse version.')
    }
  }

  const compareVersionWithCurrent = async (version: number) => {
    const targetVersion = activeSavedVersion
    if (!targetVersion) {
      setStatusMessage('Save the current network before comparing versions.')
      return
    }

    try {
      const fromSnapshot = getLocalNetworkVersion(networkId, version)
      const toSnapshot = getLocalNetworkVersion(networkId, targetVersion)
      const result =
        fromSnapshot && toSnapshot
          ? {
              network_id: networkId,
              from_version: version,
              to_version: targetVersion,
              ...compareGraphs(fromSnapshot.graph, toSnapshot.graph),
            }
          : await compareBreachPathNetworkVersions(networkId, version, targetVersion)
      setCompareResult(result as BreachPathNetworkCompare)
      setStatusMessage(`Compared v${version} with v${targetVersion}.`)
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : 'Could not compare versions.')
    }
  }

  const loadGraph = (graph: BreachPathGraphPayload, preserveSelectedNodeId?: string) => {
    enterLocalMode()
    clearAnalysis()
    entityCache.nodes.clear()
    entityCache.edges.clear()
    canvasActions.reset()

    const canvasIdByNodeId = new Map<string, number>()

    graph.nodes.forEach((node, index) => {
      const canvasId = index + 1
      canvasIdByNodeId.set(node.id, canvasId)
      const nodeEntry = createNodeEntryFromGraphNode(canvasId, node)
      entityCache.nodes.set(canvasId, nodeEntry)
      canvasActions.addNodes([{ id: canvasId, primary: true, data: nodeEntry }])
      setNodeLabelOnCanvas(canvasId, node.label)
    })

    graph.edges.forEach((edge, index) => {
      const source = canvasIdByNodeId.get(edge.source)
      const target = canvasIdByNodeId.get(edge.target)
      if (!source || !target) return

      const edgeId = index + 1
      canvasActions.addEdges([{ id: edgeId, src: source, tgt: target, data: edge }])
      setEdgeLabelOnCanvas(edgeId, edge.label || edge.edge_type)
    })

    if (preserveSelectedNodeId) {
      const restoredCanvasId = canvasIdByNodeId.get(preserveSelectedNodeId)
      const restoredNode = restoredCanvasId ? entityCache.nodes.get(restoredCanvasId) : undefined
      if (restoredCanvasId && restoredNode) {
        selectNodeForAnalysis(restoredNode as NodeEntry, restoredCanvasId)
      }
    }

    canvasActions.autoFit(1200)
    setStatusMessage('Loaded local BreachPath network.')
  }

  const loadExampleNetwork = () => {
    if (!selectedExampleNetwork) return
    if (
      hasUnsavedChanges &&
      !window.confirm('Replace the current unsaved graph with this example network?')
    ) {
      return
    }

    loadGraph(selectedExampleNetwork.graph)
    setStatusMessage(`Loaded example network: ${selectedExampleNetwork.title}.`)
  }

  const saveLocally = () => {
    saveGraphToLocalStorage(currentGraph())
    saveCurrentVersion('Manual local save').catch((error) => {
      setStatusMessage(error instanceof Error ? error.message : 'Could not save locally.')
    })
  }

  const loadLocally = () => {
    refreshLocalNetworkLibrary()
    setActivePanel('save')
    const saved = loadGraphFromLocalStorage()
    setStatusMessage(
      saved
        ? 'Opened Network Library. Legacy local graph is also available through browser storage.'
        : 'Opened Network Library. Select a saved network or create one.'
    )
  }

  const importJson = async (file: File | undefined) => {
    if (!file) return
    const text = await file.text()
    const parsed = JSON.parse(text) as BreachPathGraphPayload
    loadGraph(parsed)
  }

  const panelContent = {
    builder: {
      title: 'Network Builder',
      description: 'Add cyber nodes and typed relationships without leaving the graph canvas.',
    },
    save: {
      title: 'Save / Load',
      description: 'Manage local network versions, import/export JSON, and backend save attempts.',
    },
    history: {
      title: 'Version History',
      description: 'View, restore, compare, or analyse saved graph snapshots.',
    },
    examples: {
      title: 'Example Networks',
      description: 'Load a ready-made BreachPath demo graph for quick testing.',
    },
    analysis: {
      title: 'Analyse',
      description: 'Run defensive exposure analysis from the selected node.',
    },
  }[activePanel]

  if (!builderDrawerOpen || activePanel === 'analysis') return null

  return (
    <aside className="shadow-dark pointer-events-auto absolute left-4 top-20 z-20 flex max-h-[calc(100vh-7rem)] w-[440px] flex-col overflow-hidden rounded border border-grey-600 bg-grey-800/95 backdrop-blur">
      <header className="shrink-0 border-b border-grey-600 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-content-primary">
              <Icon icon="shield" />
              <h2 className="text-sm font-semibold">{panelContent.title}</h2>
            </div>
            <p className="mt-1 text-xs text-content-secondary">
              {panelContent.description}
            </p>
          </div>
          <button
            className="rounded px-2 py-1 text-content-secondary hover:bg-grey-700 hover:text-content-primary"
            type="button"
            aria-label="Close network builder"
            onClick={() => setBuilderDrawerOpen(false)}
          >
            ×
          </button>
        </div>
      </header>

      <div className="app-scrollbar min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain p-4 pb-12 text-sm">
        {isReadOnlyPreview && (
          <section className="rounded border border-yellow-700/70 bg-yellow-950/30 p-3 text-xs text-yellow-100">
            <strong>Viewing v{previewVersion}. This is not the latest version.</strong>
            <p className="mt-1">
              You are viewing an older saved graph. Use Restore to make it the newest version.
            </p>
            <button className="app-button mt-2 w-full" type="button" onClick={loadFromBackend}>
              View latest
            </button>
          </section>
        )}

        {activePanel === 'save' && (
        <section className="rounded border border-violet-700/70 bg-violet-950/20 p-3">
          <h3 className="font-semibold text-content-primary">Network Library</h3>
          <p className="mt-1 text-xs text-content-secondary">
            Multiple saved networks live in browser localStorage first. Backend/TuringDB saving is
            attempted when available and reported honestly.
          </p>
          <p className="mt-2 rounded border border-grey-600 bg-grey-950/50 p-2 text-xs text-content-secondary">
            Current network:{' '}
            <strong className="text-content-primary">{networkName || 'Unnamed network'}</strong>
            <br />
            Version: {activeSavedVersion ? `v${activeSavedVersion}` : 'Not saved'}
            {hasUnsavedChanges && (
              <>
                <br />
                <span className="text-yellow-100">Unsaved changes</span>
              </>
            )}
            <br />
            Backend networks:{' '}
            {backendNetworkCount === undefined ? 'not available' : backendNetworkCount}
          </p>
          <label className="mt-3 block text-xs text-content-secondary">Network ID</label>
          <input
            className="app-input mt-1 w-full"
            value={networkId}
            onChange={(event) => setNetworkId(event.target.value)}
          />
          <label className="mt-2 block text-xs text-content-secondary">Network name</label>
          <input
            className="app-input mt-1 w-full"
            value={networkName}
            onChange={(event) => setNetworkName(event.target.value)}
          />
          <label className="mt-2 block text-xs text-content-secondary">Commit message</label>
          <input
            className="app-input mt-1 w-full"
            value={commitMessage}
            onChange={(event) => setCommitMessage(event.target.value)}
          />
          <div className="mt-2 grid grid-cols-2 gap-2">
            <button className="app-button" type="button" onClick={newNetwork}>
              Create new
            </button>
            <button className="app-button" type="button" onClick={renameCurrentNetwork}>
              Rename
            </button>
            <button
              className="app-button"
              type="button"
              disabled={isReadOnlyPreview}
              onClick={saveToBackend}
            >
              Save current
            </button>
            <button className="app-button" type="button" onClick={loadFromBackend}>
              Load by ID
            </button>
            <button
              className="app-button"
              type="button"
              disabled={isReadOnlyPreview}
              onClick={() => saveCurrentVersion('Saved new version')}
            >
              Save new version
            </button>
            <button className="app-button" type="button" onClick={loadLocally}>
              Browse saved
            </button>
            <button className="app-button" type="button" onClick={saveLocally}>
              Save locally
            </button>
            <button className="app-button" type="button" onClick={() => downloadGraph(currentGraph())}>
              Export JSON
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json"
            className="hidden"
            onChange={(event) => {
              importJson(event.target.files?.[0]).catch((error) => {
                setStatusMessage(error instanceof Error ? error.message : 'Could not import JSON.')
              })
              event.target.value = ''
            }}
          />
          <button
            className="app-button mt-2 w-full"
            type="button"
            onClick={() => fileInputRef.current?.click()}
          >
            Import network JSON
          </button>

          {localNetworks.length >= 0 && (
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-content-secondary">
                  Saved networks
                </h4>
                <button className="app-button" type="button" onClick={refreshLocalNetworkLibrary}>
                  Refresh
                </button>
              </div>
              {localNetworks.length === 0 && (
                <p className="rounded bg-grey-950/50 p-2 text-xs text-content-secondary">
                  No saved networks yet. Create a network, then click Save current.
                </p>
              )}
              {localNetworks.map((network) => (
                <article
                  key={network.network_id}
                  className="rounded border border-grey-600 bg-grey-950/50 p-2"
                >
                  <strong className="text-content-primary">{network.name}</strong>
                  <p className="mt-1 text-[11px] text-content-secondary">
                    latest v{network.latest_version} - {network.node_count} nodes /{' '}
                    {network.edge_count} edges - saved {formatDateTime(network.updated_at)}
                  </p>
                  <div className="mt-2 grid grid-cols-2 gap-1">
                    <button
                      className="app-button"
                      type="button"
                      onClick={() => loadNetworkFromLibrary(network.network_id)}
                    >
                      Load
                    </button>
                    <button
                      className="app-button"
                      type="button"
                      onClick={() => deleteNetworkFromLibrary(network.network_id)}
                    >
                      Delete
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
        )}

        {activePanel === 'history' && (
          <section className="rounded border border-cyan-700/70 bg-cyan-950/20 p-3">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-semibold text-content-primary">Version History</h3>
              <button
                className="app-button"
                type="button"
                onClick={() => {
                  refreshVersionHistory(networkId, false).catch((error) => {
                    setStatusMessage(
                      error instanceof Error ? error.message : 'Could not load version history.'
                    )
                  })
                }}
              >
                Refresh
              </button>
            </div>
            <p className="mt-1 text-xs text-content-secondary">
              View old snapshots, compare them with latest, restore as a new version, or analyse a
              saved graph.
            </p>
            {historyLoading && (
              <p className="mt-2 rounded bg-grey-950/50 p-2 text-xs text-content-secondary">
                Loading version history...
              </p>
            )}
            {!historyLoading && versionHistory.length === 0 && (
              <p className="mt-2 rounded bg-grey-950/50 p-2 text-xs text-content-secondary">
                No saved versions yet.
              </p>
            )}
            <div className="mt-3 space-y-2">
              {versionHistory.map((version) => (
                <article
                  key={version.commit_id}
                  className="rounded border border-grey-600 bg-grey-950/50 p-2"
                >
                  <strong className="text-content-primary">
                    v{version.version} - {version.message || 'Saved network version'}
                  </strong>
                  <p className="mt-1 text-[11px] text-content-secondary">
                    {formatDateTime(version.created_at)} - {version.node_count} nodes /{' '}
                    {version.edge_count} edges -{' '}
                    {version.analysed
                      ? `Analysed ${version.analysis_count} time(s)`
                      : 'Not analysed'}
                  </p>
                  <div className="mt-2 grid grid-cols-2 gap-1">
                    <button
                      className="app-button"
                      type="button"
                      onClick={() => {
                        loadVersionPreview(version.version).catch((error) => {
                          setStatusMessage(
                            error instanceof Error ? error.message : 'Could not view version.'
                          )
                        })
                      }}
                    >
                      View
                    </button>
                    <button
                      className="app-button"
                      type="button"
                      onClick={() => restoreVersion(version.version)}
                    >
                      Restore
                    </button>
                    <button
                      className="app-button"
                      type="button"
                      onClick={() => compareVersionWithCurrent(version.version)}
                    >
                      Compare
                    </button>
                    <button
                      className="app-button"
                      type="button"
                      onClick={() => analyseVersion(version.version)}
                    >
                      Analyse
                    </button>
                  </div>
                </article>
              ))}
            </div>

            {compareResult && (
              <div className="mt-3 rounded border border-cyan-700/70 bg-cyan-950/20 p-2 text-xs text-cyan-100">
              <strong>
                Compared v{compareResult.from_version} with v{compareResult.to_version}
              </strong>
              <div className="mt-2 grid grid-cols-2 gap-1">
                <span>Added nodes: {compareResult.summary.added_nodes}</span>
                <span>Removed nodes: {compareResult.summary.removed_nodes}</span>
                <span>Changed nodes: {compareResult.summary.changed_nodes}</span>
                <span>Added edges: {compareResult.summary.added_edges}</span>
                <span>Removed edges: {compareResult.summary.removed_edges}</span>
                <span>Changed edges: {compareResult.summary.changed_edges}</span>
              </div>
            </div>
            )}
          </section>
        )}

        {activePanel === 'examples' && (
        <section className="rounded border border-cyan-700/70 bg-cyan-950/20 p-3">
          <h3 className="font-semibold text-content-primary">Load example network</h3>
          <p className="mt-1 text-xs text-content-secondary">
            Start with a built-in test network, then analyse a router, laptop, or server.
          </p>
          <select
            className="app-input mt-2 w-full"
            value={exampleNetworkId}
            onChange={(event) => setExampleNetworkId(event.target.value)}
          >
            {EXAMPLE_NETWORKS.map((example) => (
              <option key={example.id} value={example.id}>
                {example.title}
              </option>
            ))}
          </select>
          {selectedExampleNetwork && (
            <p className="mt-2 text-xs leading-5 text-content-secondary">
              {selectedExampleNetwork.description}
            </p>
          )}
          <button className="app-button mt-2 w-full" type="button" onClick={loadExampleNetwork}>
            Load example network
          </button>
        </section>
        )}

        {activePanel === 'builder' && (
        <>
        <section className="rounded border border-grey-600 bg-grey-900/70 p-3">
          <h3 className="font-semibold text-content-primary">Add cyber node</h3>
          <p className="mt-1 text-xs text-content-secondary">
            Create devices, accounts, services, and important assets from templates.
          </p>
          <button
            className="app-button mt-2 w-full"
            type="button"
            disabled={isReadOnlyPreview}
            onClick={() => setNodeCreatorOpen(true)}
          >
            Add cyber node
          </button>
        </section>

        <section className="rounded border border-grey-600 bg-grey-900/70 p-3">
          <h3 className="font-semibold text-content-primary">Edit selected node</h3>
          {selectedNode ? (
            <>
              <p className="mt-1 text-xs text-content-secondary">
                Editing {selectedNode.label}
                {selectedNode.nodeType && ` (${selectedNode.nodeType})`}
              </p>
              <label className="mt-3 block text-xs text-content-secondary">Label</label>
              <input
                className="app-input mt-1 w-full"
                value={selectedNodeLabelDraft}
                onChange={(event) => setSelectedNodeLabelDraft(event.target.value)}
              />
              <div className="mt-3 grid grid-cols-2 gap-2">
                <label className="block text-xs text-content-secondary">
                  Criticality
                  <select
                    className="app-input mt-1 w-full"
                    value={selectedNodeCriticalityDraft}
                    onChange={(event) =>
                      setSelectedNodeCriticalityDraft(event.target.value as Criticality)
                    }
                  >
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                    <option value="critical">critical</option>
                  </select>
                </label>
                <label className="block text-xs text-content-secondary">
                  Zone
                  <input
                    className="app-input mt-1 w-full"
                    value={selectedNodeZoneDraft}
                    onChange={(event) => setSelectedNodeZoneDraft(event.target.value)}
                  />
                </label>
              </div>
              <button
                className="app-button mt-3 w-full"
                type="button"
                disabled={isReadOnlyPreview}
                onClick={updateSelectedNodeDetails}
              >
                Update selected node
              </button>
            </>
          ) : (
            <p className="mt-1 rounded border border-yellow-700/60 bg-yellow-950/30 p-2 text-xs text-yellow-100">
              Select a node on the canvas to edit its label, criticality, or zone.
            </p>
          )}
        </section>

        {nodeCreatorOpen && (
          <section className="rounded border border-orange-700/70 bg-orange-950/20 p-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-content-primary">New cyber node</h3>
              <button
                className="rounded px-2 py-1 text-content-secondary hover:bg-grey-700 hover:text-content-primary"
                type="button"
                onClick={() => setNodeCreatorOpen(false)}
              >
                Close
              </button>
            </div>

            <label className="mt-3 block text-xs text-content-secondary">Node template</label>
            <select
              className="app-input mt-1 w-full"
              value={templateId}
              onChange={(event) => setTemplateId(event.target.value)}
            >
              {CYBER_NODE_TEMPLATES.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.icon} {template.group} - {template.title}
                </option>
              ))}
            </select>

            <div className="mt-3 rounded border border-cyan-700/60 bg-cyan-950/30 p-2 text-xs leading-5 text-cyan-100">
              <p className="font-medium text-cyan-50">Impact explanation</p>
              <p>{impactExplanation}</p>
            </div>

            <label className="mt-3 block text-xs text-content-secondary">Label</label>
            <input
              className="app-input mt-1 w-full"
              placeholder="Optional label, e.g. Family Laptop"
              value={nodeLabel}
              onChange={(event) => setNodeLabel(event.target.value)}
            />

            <div className="mt-3 grid grid-cols-2 gap-2">
              <label className="block text-xs text-content-secondary">
                Criticality
                <select
                  className="app-input mt-1 w-full"
                  value={nodeCriticality}
                  onChange={(event) => setNodeCriticality(event.target.value as Criticality)}
                >
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                  <option value="critical">critical</option>
                </select>
              </label>

              <label className="block text-xs text-content-secondary">
                Zone
                <select
                  className="app-input mt-1 w-full"
                  value={nodeZone}
                  onChange={(event) => setNodeZone(event.target.value)}
                >
                  <option value="home">home</option>
                  <option value="guest">guest</option>
                  <option value="work">work</option>
                  <option value="cloud">cloud</option>
                  <option value="internal">internal</option>
                  <option value="critical">critical</option>
                </select>
              </label>
            </div>

            <p className="mt-2 rounded border border-yellow-700/60 bg-yellow-950/30 p-2 text-xs leading-5 text-yellow-100">
              Recommended default: <strong>{selectedTemplate?.criticality ?? 'medium'}</strong>.{' '}
              {criticalityHelp}
            </p>

            <label className="mt-3 flex items-center gap-2 text-xs text-content-secondary">
              <input
                type="checkbox"
                checked={nodeInternetExposed}
                onChange={(event) => setNodeInternetExposed(event.target.checked)}
              />
              Internet exposed
            </label>

            <label className="mt-2 flex items-center gap-2 text-xs text-content-secondary">
              <input
                type="checkbox"
                checked={nodeHasAdminPrivileges}
                onChange={(event) => setNodeHasAdminPrivileges(event.target.checked)}
              />
              Has admin privileges
            </label>

            <label className="mt-3 block text-xs text-content-secondary">Notes</label>
            <textarea
              className="app-input mt-1 min-h-20 w-full"
              value={nodeNotes}
              onChange={(event) => setNodeNotes(event.target.value)}
            />

            <p className="mt-3 rounded border border-yellow-700/60 bg-yellow-950/30 p-2 text-xs text-yellow-100">
              Mark devices like routers, NAS/home servers, admin accounts, work laptops,
              databases, and security systems as high or critical if losing them would matter.
            </p>

            <button
              className="app-button mt-3 w-full"
              type="button"
              disabled={isReadOnlyPreview}
              onClick={addNode}
            >
              Create node
            </button>
          </section>
        )}

        <section className="rounded border border-grey-600 bg-grey-900/70 p-3">
          <h3 className="font-semibold text-content-primary">Create typed edge</h3>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <select
              className="app-input w-full"
              value={sourceCanvasId}
              onChange={(event) => setSourceCanvasId(event.target.value)}
            >
              <option value="">Source</option>
              {graphNodes.map((node) => (
                <option key={node.canvasId} value={node.canvasId}>
                  {shorten(node.graphNode.label)}
                </option>
              ))}
            </select>
            <select
              className="app-input w-full"
              value={targetCanvasId}
              onChange={(event) => setTargetCanvasId(event.target.value)}
            >
              <option value="">Target</option>
              {graphNodes.map((node) => (
                <option key={node.canvasId} value={node.canvasId}>
                  {shorten(node.graphNode.label)}
                </option>
              ))}
            </select>
          </div>

          {suggestedEdgeTypes.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {suggestedEdgeTypes.map((suggestion) => (
                <button
                  key={suggestion}
                  className="rounded border border-orange-700/70 bg-orange-950/30 px-2 py-1 text-xs text-orange-100"
                  type="button"
                  onClick={() => setEdgeType(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          <select
            className="app-input mt-2 w-full"
            value={edgeType}
            onChange={(event) => setEdgeType(event.target.value)}
          >
            {CYBER_EDGE_TEMPLATES.map((template) => (
              <option key={template.edge_type} value={template.edge_type}>
                {template.label} - {template.default_risk}
              </option>
            ))}
          </select>
          <p className="mt-2 text-xs text-content-secondary">
            Every connection requires a typed cyber relationship; blank edges are not created.
            Lines are shown without arrows, but the relationship type is still used by analysis.
          </p>
          <button
            className="app-button mt-2 w-full"
            type="button"
            disabled={isReadOnlyPreview}
            onClick={addTypedEdge}
          >
            Confirm typed edge
          </button>
        </section>
        </>
        )}

        <footer className="text-xs text-content-secondary">
          Mode: {localBuilderMode ? 'local builder graph' : 'TuringDB graph view'}
          {statusMessage && <p className="mt-1 text-emerald-200">{statusMessage}</p>}
        </footer>
      </div>
    </aside>
  )
}

export default BreachPathBuilderPanel
