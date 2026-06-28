import { getEdgeTemplate, getNodeTemplate } from './cyber-templates'
import type {
  BreachPathGraphEdge,
  BreachPathGraphNode,
  BreachPathGraphPayload,
} from './graph-utils'

type ExampleNodeInput = {
  id: string
  label: string
  templateId: string
  criticality?: string
}

type ExampleEdgeInput = {
  source: string
  target: string
  edgeType: string
}

export type ExampleNetwork = {
  id: string
  title: string
  description: string
  graph: BreachPathGraphPayload
}

function node(input: ExampleNodeInput): BreachPathGraphNode {
  const template = getNodeTemplate(input.templateId)

  if (!template) {
    throw new Error(`Unknown BreachPath node template: ${input.templateId}`)
  }

  return {
    id: input.id,
    label: input.label,
    node_type: template.node_type,
    template_type: template.template_type,
    criticality: input.criticality ?? template.criticality,
    zone: template.zone,
    is_internet_exposed: template.is_internet_exposed,
    has_admin_privileges: template.has_admin_privileges,
    notes: template.notes,
  }
}

function edge(index: number, input: ExampleEdgeInput): BreachPathGraphEdge {
  const template = getEdgeTemplate(input.edgeType)

  if (!template) {
    throw new Error(`Unknown BreachPath edge template: ${input.edgeType}`)
  }

  return {
    id: `example-edge-${index}`,
    source: input.source,
    target: input.target,
    edge_type: template.edge_type,
    label: template.label,
    risk_weight: template.risk_weight,
    direction: template.direction,
    risk_can_spread_both_ways: template.risk_can_spread_both_ways,
    notes: template.meaning,
  }
}

function graph(
  name: string,
  nodes: ExampleNodeInput[],
  edges: ExampleEdgeInput[]
): BreachPathGraphPayload {
  return {
    metadata: {
      name,
      source: 'Built-in BreachPath example network',
    },
    nodes: nodes.map(node),
    edges: edges.map((exampleEdge, index) => edge(index + 1, exampleEdge)),
  }
}

export const EXAMPLE_NETWORKS: ExampleNetwork[] = [
  {
    id: 'basic-home-network',
    title: 'Basic Home Network',
    description: 'Router, internet, personal devices, printer, and NAS storage.',
    graph: graph(
      'Basic Home Network',
      [
        { id: 'internet', label: 'Internet', templateId: 'internet' },
        { id: 'router', label: 'Router', templateId: 'router' },
        { id: 'personal-laptop', label: 'Personal Laptop', templateId: 'laptop' },
        { id: 'phone', label: 'Phone', templateId: 'phone' },
        { id: 'printer', label: 'Printer', templateId: 'printer' },
        { id: 'nas-home-server', label: 'NAS / Home Server', templateId: 'nas-home-server' },
      ],
      [
        { source: 'router', target: 'internet', edgeType: 'routes_through' },
        { source: 'router', target: 'personal-laptop', edgeType: 'same_network' },
        { source: 'router', target: 'phone', edgeType: 'same_network' },
        { source: 'router', target: 'printer', edgeType: 'same_network' },
        { source: 'personal-laptop', target: 'nas-home-server', edgeType: 'can_access' },
      ]
    ),
  },
  {
    id: 'home-iot-network',
    title: 'Home + IoT Network',
    description: 'Home devices, IoT devices, work laptop, VPN, and shared storage.',
    graph: graph(
      'Home + IoT Network',
      [
        { id: 'router', label: 'Router', templateId: 'router' },
        { id: 'personal-laptop', label: 'Personal Laptop', templateId: 'laptop' },
        { id: 'work-laptop', label: 'Work Laptop', templateId: 'work-laptop' },
        { id: 'phone', label: 'Phone', templateId: 'phone' },
        { id: 'smart-tv', label: 'Smart TV', templateId: 'smart-tv' },
        { id: 'security-camera', label: 'Security Camera', templateId: 'security-camera' },
        { id: 'smart-speaker', label: 'Smart Speaker / IoT Device', templateId: 'iot-device' },
        { id: 'nas-home-server', label: 'NAS / Home Server', templateId: 'nas-home-server' },
        { id: 'vpn-gateway', label: 'VPN Gateway', templateId: 'vpn-gateway' },
      ],
      [
        { source: 'router', target: 'personal-laptop', edgeType: 'same_network' },
        { source: 'router', target: 'work-laptop', edgeType: 'same_network' },
        { source: 'router', target: 'phone', edgeType: 'same_network' },
        { source: 'router', target: 'smart-tv', edgeType: 'same_network' },
        { source: 'router', target: 'security-camera', edgeType: 'same_network' },
        { source: 'router', target: 'smart-speaker', edgeType: 'same_network' },
        { source: 'router', target: 'nas-home-server', edgeType: 'same_network' },
        { source: 'personal-laptop', target: 'nas-home-server', edgeType: 'can_access' },
        { source: 'work-laptop', target: 'vpn-gateway', edgeType: 'can_access' },
        { source: 'security-camera', target: 'router', edgeType: 'can_access' },
      ]
    ),
  },
  {
    id: 'small-office-network',
    title: 'Small Office Network',
    description: 'Firewall, VPN, workstation, file server, admin identity, and core data.',
    graph: graph(
      'Small Office Network',
      [
        { id: 'internet', label: 'Internet', templateId: 'internet' },
        { id: 'firewall', label: 'Firewall', templateId: 'firewall' },
        { id: 'vpn-gateway', label: 'VPN Gateway', templateId: 'vpn-gateway' },
        { id: 'workstation', label: 'Workstation', templateId: 'workstation' },
        { id: 'file-server', label: 'File Server', templateId: 'file-server' },
        { id: 'admin-account', label: 'Admin Account', templateId: 'admin-account' },
        { id: 'domain-controller', label: 'Domain Controller', templateId: 'domain-controller' },
        { id: 'database', label: 'Database', templateId: 'database' },
        { id: 'backup-server', label: 'Backup Server', templateId: 'backup-server' },
      ],
      [
        { source: 'firewall', target: 'internet', edgeType: 'routes_through' },
        { source: 'vpn-gateway', target: 'workstation', edgeType: 'can_access' },
        { source: 'workstation', target: 'file-server', edgeType: 'can_access' },
        { source: 'file-server', target: 'admin-account', edgeType: 'stores_credentials_for' },
        { source: 'admin-account', target: 'domain-controller', edgeType: 'administers' },
        { source: 'domain-controller', target: 'database', edgeType: 'controls' },
        { source: 'backup-server', target: 'file-server', edgeType: 'backs_up' },
      ]
    ),
  },
]
