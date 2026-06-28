import TuringButton from '@/components/base/turing-button'
import { getBreachPathStorageStatus, saveBreachPathNetworkVersionForNetwork } from '@/api/breachpath'
import {
  buildGraphPayload,
  networkIdFromName,
  saveLocalNetworkVersion,
} from '@/breachpath/graph-utils'
import { useBreachPathBuilderStore, useBreachPathStore, useCanvasStore, useVisStore } from '@/stores'
import { CenterForceSwitch } from './actions/center-force-switch'
import { NodeShapeSwitch } from './actions/node-shape-switch'
import { useEffect } from 'react'

export const TuringTopToolBar = () => {
  const inspectNodeInfo = useVisStore((state) => state.inspectNodeInfo)
  const isNodeInspectorExtended = useVisStore((state) => state.isNodeInspectorExtended)
  const nodeInspectorExtendedWidth = useVisStore((state) => state.nodeInspectorExtendedWidth)
  const nodeInspectorCollapsedWidth = useVisStore((state) => state.nodeInspectorCollapsedWidth)
  const graphLoading = useVisStore((state) => state.graphLoading)
  const canvasNodes = useCanvasStore((state) => state.nodes())
  const canvasEdges = useCanvasStore((state) => state.edges())
  const builderDrawerOpen = useBreachPathBuilderStore((state) => state.builderDrawerOpen)
  const activePanel = useBreachPathBuilderStore((state) => state.activePanel)
  const setActivePanel = useBreachPathBuilderStore((state) => state.setActivePanel)
  const setStatusMessage = useBreachPathBuilderStore((state) => state.setStatusMessage)
  const analysisStatus = useBreachPathStore((state) => state.status)
  const savedNetworkId = useBreachPathStore((state) => state.savedNetworkId)
  const savedNetworkName = useBreachPathStore((state) => state.savedNetworkName)
  const savedNetworkVersion = useBreachPathStore((state) => state.savedNetworkVersion)
  const hasUnsavedChanges = useBreachPathStore((state) => state.hasUnsavedChanges)
  const previewVersion = useBreachPathStore((state) => state.previewVersion)
  const storageStatusLabel = useBreachPathStore((state) => state.storageStatusLabel)
  const setStorageStatusLabel = useBreachPathStore((state) => state.setStorageStatusLabel)
  const setSavedNetworkVersion = useBreachPathStore((state) => state.setSavedNetworkVersion)

  const inspectorOffset = inspectNodeInfo
    ? isNodeInspectorExtended
      ? nodeInspectorExtendedWidth
      : nodeInspectorCollapsedWidth
    : 0
  const currentGraph = buildGraphPayload(canvasNodes, canvasEdges)
  const analysisVersion = previewVersion ?? savedNetworkVersion
  const currentNetworkLabel = savedNetworkName ?? 'Unsaved network'

  const saveVersionFromToolbar = async () => {
    const name =
      savedNetworkName ||
      window.prompt('Network name', 'Home Network')?.trim() ||
      'BreachPath Network'
    const networkId = savedNetworkId || networkIdFromName(name)
    const message =
      window.prompt('Version message', hasUnsavedChanges ? 'Saved changes' : 'Saved version')?.trim() ||
      'Saved version'
    const result = saveLocalNetworkVersion({
      networkId,
      name,
      graph: currentGraph,
      message,
    })

    setSavedNetworkVersion(
      result.network.network_id,
      result.version.version,
      result.network.name,
      result.version.graph_hash
    )

    try {
      const backendResult = await saveBreachPathNetworkVersionForNetwork({
        networkId: result.network.network_id,
        name: result.network.name,
        graph: currentGraph,
        message,
      })
      const warning = backendResult.warning ? ` ${backendResult.warning}` : ''
      setStatusMessage(
        `Saved ${result.network.name} v${result.version.version} locally. Backend ${backendResult.storage_backend}.${warning}`
      )
    } catch {
      setStatusMessage(
        `Saved ${result.network.name} v${result.version.version} locally. Backend/TuringDB unavailable.`
      )
    }
  }

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

  return (
    <div
      className="absolute top-0 m-4 transition-[left] duration-300"
      style={{ left: `${inspectorOffset}px` }}
    >
      <div className="flex items-center gap-2 rounded border border-grey-600 bg-grey-800/95 p-2 shadow-dark">
        <TuringButton
          icon="shield"
          intent="primary"
          highlight={builderDrawerOpen && activePanel === 'builder'}
          loading={graphLoading}
          onClick={() => setActivePanel('builder')}
        >
          Network builder
        </TuringButton>

        <TuringButton
          icon="path-search"
          intent="success"
          highlight={builderDrawerOpen && activePanel === 'analysis'}
          loading={analysisStatus === 'loading'}
          onClick={() => setActivePanel('analysis')}
        >
          Analyse
        </TuringButton>

        <TuringButton
          icon="folder-open"
          highlight={builderDrawerOpen && activePanel === 'save'}
          onClick={() => setActivePanel('save')}
        >
          Save / Load
        </TuringButton>

        <TuringButton
          icon="history"
          highlight={builderDrawerOpen && activePanel === 'history'}
          onClick={() => setActivePanel('history')}
        >
          Version History
        </TuringButton>

        <TuringButton
          icon="database"
          highlight={builderDrawerOpen && activePanel === 'examples'}
          onClick={() => setActivePanel('examples')}
        >
          Examples
        </TuringButton>

        <TuringButton icon="floppy-disk" intent="warning" onClick={saveVersionFromToolbar}>
          Save Version
        </TuringButton>

        <div className="mx-1 h-6 border-l border-grey-600" />

        <CenterForceSwitch />
        <NodeShapeSwitch />

        <span className="ml-2 text-xs text-content-secondary">
          {currentNetworkLabel}
          {analysisVersion ? ` / v${analysisVersion}` : ' / not saved'}
          {hasUnsavedChanges ? ' / Unsaved changes' : ''}
          {' / '}
          {storageStatusLabel}
        </span>
      </div>
    </div>
  )
}
