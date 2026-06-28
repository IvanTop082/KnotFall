import type { NodeEntry } from '@/api/models/nodeEntry.model'
import type { TuringEdge, TuringNode } from '@turingcanvas'
import {
  type CyberEdgeTemplate,
  type CyberNodeTemplate,
  getEdgeTemplate,
} from './cyber-templates'

export type BreachPathGraphNode = {
  id: string
  label: string
  node_type: string
  template_type: string
  criticality: string
  zone: string
  is_internet_exposed: boolean
  has_admin_privileges: boolean
  notes: string
}

export type BreachPathGraphEdge = {
  id: string
  source: string
  target: string
  edge_type: string
  label: string
  risk_weight: number
  direction: string
  risk_can_spread_both_ways: boolean
  notes: string
}

export type BreachPathGraphPayload = {
  metadata: {
    name: string
    source: string
  }
  nodes: BreachPathGraphNode[]
  edges: BreachPathGraphEdge[]
}

export type SavedBreachPathGraph = {
  version: 1
  saved_at: string
  graph: BreachPathGraphPayload
}

export type BreachPathNetworkVersion = {
  version: number
  commit_id: string
  message: string
  created_at: string
  graph_hash: string
  node_count: number
  edge_count: number
  graph: BreachPathGraphPayload
  analysed?: boolean
  analysis_count?: number
}

export type BreachPathLocalNetwork = {
  network_id: string
  name: string
  latest_version: number
  updated_at: string
  versions: BreachPathNetworkVersion[]
}

export type BreachPathLocalNetworkSummary = {
  network_id: string
  name: string
  latest_version: number
  updated_at: string
  node_count: number
  edge_count: number
}

export const LOCAL_GRAPH_STORAGE_KEY = 'breachpath.localGraph.v1'
export const LOCAL_NETWORK_INDEX_KEY = 'breachpath.networks.index'
export const LOCAL_NETWORK_KEY_PREFIX = 'breachpath.networks.'
export const LOCAL_CURRENT_NETWORK_ID_KEY = 'breachpath.currentNetworkId'

const PROPERTY_KEYS = {
  id: ['id', 'id (String)', 'breachpath_id', 'breachpath_id (String)'],
  label: ['label', 'label (String)', 'name', 'name (String)', 'title', 'title (String)'],
  node_type: ['node_type', 'node_type (String)', 'type', 'type (String)'],
  template_type: ['template_type', 'template_type (String)'],
  criticality: ['criticality', 'criticality (String)'],
  zone: ['zone', 'zone (String)'],
  is_internet_exposed: ['is_internet_exposed', 'is_internet_exposed (Boolean)'],
  has_admin_privileges: ['has_admin_privileges', 'has_admin_privileges (Boolean)'],
  notes: ['notes', 'notes (String)', 'description', 'description (String)'],
}

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

function commitId(networkId: string, version: number, graphHash: string, message: string) {
  const payload = `${networkId}:${version}:${graphHash}:${message}:${Date.now()}`
  let hash = 0

  for (let index = 0; index < payload.length; index += 1) {
    hash = (hash * 33 + payload.charCodeAt(index)) >>> 0
  }

  return hash.toString(16).padStart(8, '0')
}

export function networkIdFromName(name: string) {
  return slugify(name) || `network-${Date.now()}`
}

function networkStorageKey(networkId: string) {
  return `${LOCAL_NETWORK_KEY_PREFIX}${networkId}`
}

function readNetworkIndex() {
  const raw = localStorage.getItem(LOCAL_NETWORK_INDEX_KEY)
  if (!raw) return [] as string[]

  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === 'string') : []
  } catch {
    return []
  }
}

function writeNetworkIndex(networkIds: string[]) {
  localStorage.setItem(
    LOCAL_NETWORK_INDEX_KEY,
    JSON.stringify([...new Set(networkIds)].sort(), null, 2)
  )
}

function propertyValue(entry: NodeEntry | undefined, keys: string[], fallback = '') {
  if (!entry) return fallback

  for (const key of keys) {
    const value = entry.properties[key]
    if (value !== undefined && value !== null && String(value).trim()) return String(value)
  }

  return fallback
}

function boolProperty(entry: NodeEntry | undefined, keys: string[], fallback = false) {
  const value = propertyValue(entry, keys)
  if (!value) return fallback
  return value === 'true' || value === 'yes' || value === '1'
}

export function nextCanvasId(nodes: TuringNode[]) {
  return Math.max(0, ...nodes.map((node) => node.id)) + 1
}

export function nextEdgeId(edges: TuringEdge[]) {
  return Math.max(0, ...edges.map((edge) => edge.id)) + 1
}

export function nextNodeSlug(template: CyberNodeTemplate, nodes: TuringNode[]) {
  const prefix = slugify(template.node_type)
  const used = new Set(nodes.map((node) => nodeEntryToGraphNode(node.data as NodeEntry).id))
  let index = 1

  while (used.has(`${prefix}-${index}`)) index += 1
  return `${prefix}-${index}`
}

export function createNodeEntryFromTemplate(
  canvasId: number,
  template: CyberNodeTemplate,
  label: string,
  breachPathId: string,
  overrides: Partial<BreachPathGraphNode> = {}
): NodeEntry {
  return {
    id: canvasId,
    in_edge_count: 0,
    out_edge_count: 0,
    labels: ['BreachPathNode', template.template_type],
    properties: {
      id: breachPathId,
      label,
      node_type: overrides.node_type ?? template.node_type,
      template_type: overrides.template_type ?? template.template_type,
      criticality: overrides.criticality ?? template.criticality,
      zone: overrides.zone ?? template.zone,
      is_internet_exposed: String(
        overrides.is_internet_exposed ?? template.is_internet_exposed
      ),
      has_admin_privileges: String(
        overrides.has_admin_privileges ?? template.has_admin_privileges
      ),
      notes: overrides.notes ?? template.notes,
    },
  }
}

export function createNodeEntryFromGraphNode(
  canvasId: number,
  node: BreachPathGraphNode
): NodeEntry {
  return {
    id: canvasId,
    in_edge_count: 0,
    out_edge_count: 0,
    labels: ['BreachPathNode', node.template_type],
    properties: {
      id: node.id,
      label: node.label,
      node_type: node.node_type,
      template_type: node.template_type,
      criticality: node.criticality,
      zone: node.zone,
      is_internet_exposed: String(node.is_internet_exposed),
      has_admin_privileges: String(node.has_admin_privileges),
      notes: node.notes,
    },
  }
}

export function nodeEntryToGraphNode(entry: NodeEntry | undefined): BreachPathGraphNode {
  const canvasId = entry?.id ?? 0
  const fallbackId = `node-${canvasId}`
  const id = propertyValue(entry, PROPERTY_KEYS.id, fallbackId)
  const label = propertyValue(entry, PROPERTY_KEYS.label, id)
  const node_type = propertyValue(entry, PROPERTY_KEYS.node_type, 'workstation')

  return {
    id,
    label,
    node_type,
    template_type: propertyValue(entry, PROPERTY_KEYS.template_type, node_type),
    criticality: propertyValue(entry, PROPERTY_KEYS.criticality, 'medium'),
    zone: propertyValue(entry, PROPERTY_KEYS.zone, 'internal'),
    is_internet_exposed: boolProperty(entry, PROPERTY_KEYS.is_internet_exposed),
    has_admin_privileges: boolProperty(entry, PROPERTY_KEYS.has_admin_privileges),
    notes: propertyValue(entry, PROPERTY_KEYS.notes),
  }
}

export function createEdgeData(
  edgeId: number,
  sourceNode: BreachPathGraphNode,
  targetNode: BreachPathGraphNode,
  template: CyberEdgeTemplate,
  notes = ''
): BreachPathGraphEdge {
  return {
    id: `edge-${edgeId}`,
    source: sourceNode.id,
    target: targetNode.id,
    edge_type: template.edge_type,
    label: template.label,
    risk_weight: template.risk_weight,
    direction: template.direction,
    risk_can_spread_both_ways: template.risk_can_spread_both_ways,
    notes: notes || template.meaning,
  }
}

export function edgeToGraphEdge(edge: TuringEdge): BreachPathGraphEdge {
  const customData = edge.data as BreachPathGraphEdge | undefined

  if (customData?.edge_type && customData.source && customData.target) {
    return customData
  }

  const source = nodeEntryToGraphNode(edge.source.data as NodeEntry)
  const target = nodeEntryToGraphNode(edge.target.data as NodeEntry)
  const fallbackTemplate = getEdgeTemplate('can_access')

  return {
    id: `edge-${edge.id}`,
    source: source.id,
    target: target.id,
    edge_type: fallbackTemplate?.edge_type ?? 'can_access',
    label: fallbackTemplate?.label ?? 'Can access',
    risk_weight: fallbackTemplate?.risk_weight ?? 55,
    direction: fallbackTemplate?.direction ?? 'source_to_target',
    risk_can_spread_both_ways: fallbackTemplate?.risk_can_spread_both_ways ?? true,
    notes: 'Imported visualizer edge without BreachPath edge metadata.',
  }
}

export function buildGraphPayload(nodes: TuringNode[], edges: TuringEdge[]): BreachPathGraphPayload {
  return {
    metadata: {
      name: 'BreachPath local network',
      source: 'apps/visualizer local canvas',
    },
    nodes: nodes.map((node) => nodeEntryToGraphNode(node.data as NodeEntry)),
    edges: edges.map(edgeToGraphEdge),
  }
}

export function saveGraphToLocalStorage(graph: BreachPathGraphPayload) {
  const saved: SavedBreachPathGraph = {
    version: 1,
    saved_at: new Date().toISOString(),
    graph,
  }
  localStorage.setItem(LOCAL_GRAPH_STORAGE_KEY, JSON.stringify(saved, null, 2))
}

export function loadGraphFromLocalStorage() {
  const raw = localStorage.getItem(LOCAL_GRAPH_STORAGE_KEY)
  if (!raw) return undefined
  return JSON.parse(raw) as SavedBreachPathGraph
}

export function listLocalNetworks(): BreachPathLocalNetworkSummary[] {
  return readNetworkIndex()
    .map((networkId) => loadLocalNetwork(networkId))
    .filter((network): network is BreachPathLocalNetwork => Boolean(network))
    .map((network) => {
      const latest = getLatestLocalNetworkVersion(network)
      return {
        network_id: network.network_id,
        name: network.name,
        latest_version: network.latest_version,
        updated_at: network.updated_at,
        node_count: latest?.node_count ?? 0,
        edge_count: latest?.edge_count ?? 0,
      }
    })
    .sort((first, second) => second.updated_at.localeCompare(first.updated_at))
}

export function loadLocalNetwork(networkId: string) {
  const raw = localStorage.getItem(networkStorageKey(networkId))
  if (!raw) return undefined

  try {
    return JSON.parse(raw) as BreachPathLocalNetwork
  } catch {
    return undefined
  }
}

export function getLatestLocalNetworkVersion(network: BreachPathLocalNetwork) {
  return [...network.versions].sort((first, second) => second.version - first.version)[0]
}

export function getLocalNetworkVersion(networkId: string, version: number) {
  return loadLocalNetwork(networkId)?.versions.find((entry) => entry.version === version)
}

export function saveLocalNetworkVersion(args: {
  networkId: string
  name: string
  graph: BreachPathGraphPayload
  message: string
}) {
  const networkId = args.networkId || networkIdFromName(args.name)
  const existing = loadLocalNetwork(networkId)
  const version = (existing?.latest_version ?? 0) + 1
  const createdAt = new Date().toISOString()
  const graph_hash = graphFingerprint(args.graph)
  const entry: BreachPathNetworkVersion = {
    version,
    commit_id: commitId(networkId, version, graph_hash, args.message),
    message: args.message || `Saved version ${version}`,
    created_at: createdAt,
    graph_hash,
    node_count: args.graph.nodes.length,
    edge_count: args.graph.edges.length,
    graph: args.graph,
    analysed: false,
    analysis_count: 0,
  }
  const network: BreachPathLocalNetwork = {
    network_id: networkId,
    name: args.name || existing?.name || networkId,
    latest_version: version,
    updated_at: createdAt,
    versions: [...(existing?.versions ?? []), entry],
  }
  const index = readNetworkIndex()

  localStorage.setItem(networkStorageKey(networkId), JSON.stringify(network, null, 2))
  writeNetworkIndex([...index, networkId])
  localStorage.setItem(LOCAL_CURRENT_NETWORK_ID_KEY, networkId)

  return { network, version: entry }
}

export function renameLocalNetwork(networkId: string, name: string) {
  const network = loadLocalNetwork(networkId)
  if (!network) throw new Error(`Saved network not found: ${networkId}`)

  const updated = {
    ...network,
    name,
    updated_at: new Date().toISOString(),
  }
  localStorage.setItem(networkStorageKey(networkId), JSON.stringify(updated, null, 2))
  return updated
}

export function deleteLocalNetwork(networkId: string) {
  localStorage.removeItem(networkStorageKey(networkId))
  writeNetworkIndex(readNetworkIndex().filter((savedNetworkId) => savedNetworkId !== networkId))

  if (localStorage.getItem(LOCAL_CURRENT_NETWORK_ID_KEY) === networkId) {
    localStorage.removeItem(LOCAL_CURRENT_NETWORK_ID_KEY)
  }
}

export function restoreLocalNetworkVersion(networkId: string, version: number) {
  const network = loadLocalNetwork(networkId)
  const snapshot = network?.versions.find((entry) => entry.version === version)
  if (!network || !snapshot) throw new Error(`Version ${version} not found.`)

  return saveLocalNetworkVersion({
    networkId,
    name: network.name,
    graph: snapshot.graph,
    message: `Restored from v${version}`,
  })
}

export function compareGraphs(
  fromGraph: BreachPathGraphPayload,
  toGraph: BreachPathGraphPayload
) {
  const fromNodes = new Map(fromGraph.nodes.map((node) => [node.id, node]))
  const toNodes = new Map(toGraph.nodes.map((node) => [node.id, node]))
  const fromEdges = new Map(fromGraph.edges.map((edge) => [edge.id, edge]))
  const toEdges = new Map(toGraph.edges.map((edge) => [edge.id, edge]))
  const added_nodes = [...toNodes.keys()]
    .filter((nodeId) => !fromNodes.has(nodeId))
    .map((nodeId) => toNodes.get(nodeId)!)
  const removed_nodes = [...fromNodes.keys()]
    .filter((nodeId) => !toNodes.has(nodeId))
    .map((nodeId) => fromNodes.get(nodeId)!)
  const changed_nodes = [...fromNodes.keys()]
    .filter((nodeId) => {
      const before = fromNodes.get(nodeId)
      const after = toNodes.get(nodeId)
      return before && after && before.criticality !== after.criticality
    })
    .map((nodeId) => ({
      id: nodeId,
      label: toNodes.get(nodeId)?.label ?? fromNodes.get(nodeId)?.label ?? nodeId,
      before_criticality: fromNodes.get(nodeId)?.criticality,
      after_criticality: toNodes.get(nodeId)?.criticality,
    }))
  const added_edges = [...toEdges.keys()]
    .filter((edgeId) => !fromEdges.has(edgeId))
    .map((edgeId) => toEdges.get(edgeId)!)
  const removed_edges = [...fromEdges.keys()]
    .filter((edgeId) => !toEdges.has(edgeId))
    .map((edgeId) => fromEdges.get(edgeId)!)
  const changed_edges = [...fromEdges.keys()]
    .filter((edgeId) => {
      const before = fromEdges.get(edgeId)
      const after = toEdges.get(edgeId)
      return before && after && before.edge_type !== after.edge_type
    })
    .map((edgeId) => ({
      id: edgeId,
      source: toEdges.get(edgeId)?.source ?? fromEdges.get(edgeId)?.source,
      target: toEdges.get(edgeId)?.target ?? fromEdges.get(edgeId)?.target,
      before_relationship: fromEdges.get(edgeId)?.edge_type,
      after_relationship: toEdges.get(edgeId)?.edge_type,
    }))

  return {
    added_nodes,
    removed_nodes,
    changed_nodes,
    added_edges,
    removed_edges,
    changed_edges,
    summary: {
      added_nodes: added_nodes.length,
      removed_nodes: removed_nodes.length,
      changed_nodes: changed_nodes.length,
      added_edges: added_edges.length,
      removed_edges: removed_edges.length,
      changed_edges: changed_edges.length,
    },
  }
}

export function downloadGraph(graph: BreachPathGraphPayload) {
  const blob = new Blob([JSON.stringify(graph, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'breachpath-network.json'
  link.click()
  URL.revokeObjectURL(url)
}

export function graphFingerprint(graph: BreachPathGraphPayload) {
  const stableGraph = {
    nodes: [...graph.nodes].sort((first, second) => first.id.localeCompare(second.id)),
    edges: [...graph.edges].sort((first, second) => first.id.localeCompare(second.id)),
  }
  const payload = JSON.stringify(stableGraph)
  let hash = 0

  for (let index = 0; index < payload.length; index += 1) {
    hash = (hash * 31 + payload.charCodeAt(index)) >>> 0
  }

  return hash.toString(16).padStart(8, '0')
}
