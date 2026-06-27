import type { NodeEntry } from '@/api/models/nodeEntry.model'
import {
  CYBER_EDGE_TEMPLATES,
  CYBER_NODE_TEMPLATES,
  getEdgeTemplate,
  getNodeTemplate,
  suggestEdgeTypes,
  type Criticality,
} from '@/breachpath/cyber-templates'
import {
  buildGraphPayload,
  createEdgeData,
  createNodeEntryFromGraphNode,
  createNodeEntryFromTemplate,
  downloadGraph,
  loadGraphFromLocalStorage,
  nextCanvasId,
  nextEdgeId,
  nextNodeSlug,
  nodeEntryToGraphNode,
  saveGraphToLocalStorage,
  type BreachPathGraphPayload,
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

export function BreachPathBuilderPanel() {
  const turing = useTuringContext()
  const canvasActions = useCanvasStore((state) => state.actions)
  const canvasNodes = useCanvasStore((state) => state.nodes())
  const canvasEdges = useCanvasStore((state) => state.edges())
  const selectedNodes = useCanvasStore((state) => state.selectedNodes())
  const entityCache = useVisStore((state) => state.entityCache)
  const neighbourhood = useVisStore((state) => state.neighbourhood)
  const graphName = useAppStore((state) => state.graphName)
  const runAnalysisForNode = useBreachPathStore((state) => state.runAnalysisForNode)
  const clearAnalysis = useBreachPathStore((state) => state.clearAnalysis)
  const builderDrawerOpen = useBreachPathBuilderStore((state) => state.builderDrawerOpen)
  const setBuilderDrawerOpen = useBreachPathBuilderStore((state) => state.setBuilderDrawerOpen)
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
  const [sourceCanvasId, setSourceCanvasId] = useState('')
  const [targetCanvasId, setTargetCanvasId] = useState('')
  const [edgeType, setEdgeType] = useState('can_access')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const selectedTemplate = useMemo(() => getNodeTemplate(templateId), [templateId])

  useEffect(() => {
    if (!selectedTemplate) return

    setNodeCriticality(selectedTemplate.criticality)
    setNodeZone(selectedTemplate.zone)
    setNodeInternetExposed(selectedTemplate.is_internet_exposed)
    setNodeHasAdminPrivileges(selectedTemplate.has_admin_privileges)
    setNodeNotes(selectedTemplate.notes)
  }, [selectedTemplate])

  const graphNodes = useMemo(
    () =>
      canvasNodes.map((node) => ({
        canvasId: node.id,
        graphNode: nodeEntryToGraphNode(node.data as NodeEntry),
      })),
    [canvasNodes]
  )

  const selectedNode = useMemo(() => {
    const firstSelected = [...selectedNodes.values()][0]
    return firstSelected
  }, [selectedNodes])

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
    enterLocalMode()
    clearAnalysis()
    entityCache.nodes.clear()
    entityCache.edges.clear()
    canvasActions.reset()
    setStatusMessage('Started a new local BreachPath network.')
  }

  const addNode = () => {
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

  const addTypedEdge = () => {
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

  const currentGraph = () => buildGraphPayload(canvasNodes, canvasEdges)

  const runSelectedAnalysis = async () => {
    if (!selectedNode) {
      setStatusMessage('Select a node on the canvas before running analysis.')
      return
    }

    const graph = currentGraph()
    await runAnalysisForNode(selectedNode.data as NodeEntry | undefined, selectedNode.id, graph)
  }

  const loadGraph = (graph: BreachPathGraphPayload) => {
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

    canvasActions.autoFit(1200)
    setStatusMessage('Loaded local BreachPath network.')
  }

  const saveLocally = () => {
    saveGraphToLocalStorage(currentGraph())
    setStatusMessage('Saved this network in browser localStorage.')
  }

  const loadLocally = () => {
    const saved = loadGraphFromLocalStorage()
    if (!saved) {
      setStatusMessage('No local BreachPath network has been saved yet.')
      return
    }

    loadGraph(saved.graph)
  }

  const importJson = async (file: File | undefined) => {
    if (!file) return
    const text = await file.text()
    const parsed = JSON.parse(text) as BreachPathGraphPayload
    loadGraph(parsed)
  }

  if (!builderDrawerOpen) return null

  return (
    <aside className="shadow-dark pointer-events-auto absolute bottom-4 left-4 top-20 z-10 w-[410px] overflow-hidden rounded border border-grey-600 bg-grey-800">
      <header className="border-b border-grey-600 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-content-primary">
              <Icon icon="shield" />
              <h2 className="text-sm font-semibold">Network builder</h2>
            </div>
            <p className="mt-1 text-xs text-content-secondary">
              Build a cyber network, add typed relationships, then run defensive exposure analysis.
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

      <div className="app-scrollbar max-h-[calc(100vh-9rem)] space-y-4 overflow-y-auto p-4 text-sm">
        <section>
          <div className="grid grid-cols-2 gap-2">
            <button className="app-button" type="button" onClick={newNetwork}>
              New network
            </button>
            <button className="app-button" type="button" onClick={saveLocally}>
              Save locally
            </button>
            <button className="app-button" type="button" onClick={loadLocally}>
              Load locally
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
            Import JSON
          </button>
        </section>

        <section className="rounded border border-grey-600 bg-grey-900/70 p-3">
          <h3 className="font-semibold text-content-primary">Add cyber node</h3>
          <p className="mt-1 text-xs text-content-secondary">
            Create devices, accounts, services, and important assets from templates.
          </p>
          <button
            className="app-button mt-2 w-full"
            type="button"
            onClick={() => setNodeCreatorOpen(true)}
          >
            Add cyber node
          </button>
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

            <button className="app-button mt-3 w-full" type="button" onClick={addNode}>
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
          <button className="app-button mt-2 w-full" type="button" onClick={addTypedEdge}>
            Confirm typed edge
          </button>
        </section>

        <section className="rounded border border-grey-600 bg-grey-900/70 p-3">
          <h3 className="font-semibold text-content-primary">Compromise analysis</h3>
          <p className="mt-1 text-xs text-content-secondary">
            Select a suspected compromised node on the canvas, then run analysis against the
            current graph.
          </p>
          <button className="app-button mt-2 w-full" type="button" onClick={runSelectedAnalysis}>
            Analyse selected node
          </button>
        </section>

        <footer className="text-xs text-content-secondary">
          Mode: {localBuilderMode ? 'local builder graph' : 'TuringDB graph view'}
          {statusMessage && <p className="mt-1 text-emerald-200">{statusMessage}</p>}
        </footer>
      </div>
    </aside>
  )
}

export default BreachPathBuilderPanel
