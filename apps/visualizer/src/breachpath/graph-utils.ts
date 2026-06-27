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

export const LOCAL_GRAPH_STORAGE_KEY = 'breachpath.localGraph.v1'

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

export function downloadGraph(graph: BreachPathGraphPayload) {
  const blob = new Blob([JSON.stringify(graph, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'breachpath-network.json'
  link.click()
  URL.revokeObjectURL(url)
}
