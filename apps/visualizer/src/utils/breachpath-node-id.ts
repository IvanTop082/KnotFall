import type { NodeEntry } from '@/api/models/nodeEntry.model'
import { getNodeName } from './nodes'

const BREACHPATH_ID_KEYS = [
  'id',
  'id (String)',
  'node_id',
  'node_id (String)',
  'breachpath_id',
  'breachpath_id (String)',
]

const NODE_TYPE_KEYS = ['type', 'type (String)', 'node_type', 'node_type (String)']

function propertyValue(node: NodeEntry | undefined, keys: string[]) {
  if (!node) return undefined

  for (const key of keys) {
    const value = node.properties[key]
    if (value !== undefined && value !== null && String(value).trim()) {
      return String(value)
    }
  }

  const normalizedKeys = new Set(keys.map((key) => key.toLowerCase()))
  for (const [key, value] of Object.entries(node.properties)) {
    const normalizedKey = key.replace(/\s+\(.+\)$/, '').toLowerCase()
    if (normalizedKeys.has(normalizedKey) && value !== undefined && value !== null) {
      const text = String(value)
      if (text.trim()) return text
    }
  }

  return undefined
}

export function getBreachPathNodeId(node: NodeEntry | undefined) {
  const id = propertyValue(node, BREACHPATH_ID_KEYS)
  if (id) return { id }

  if (!node) {
    return {
      id: undefined,
      note: 'The selected TuringDB node has no loaded node data yet.',
    }
  }

  return {
    id: String(node.id),
    note:
      'No BreachPath id property was found on this TuringDB node, so the internal TuringDB id was used. Import breachpath_demo with the id property to avoid this mapping mismatch.',
  }
}

export function getBreachPathNodeLabel(node: NodeEntry | undefined) {
  if (!node) return 'Unknown node'

  const name = getNodeName(node.properties)
  return String(name?.value ?? node.id)
}

export function getBreachPathNodeType(node: NodeEntry | undefined) {
  return propertyValue(node, NODE_TYPE_KEYS)
}
