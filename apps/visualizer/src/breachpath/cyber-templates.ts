export type Criticality = 'low' | 'medium' | 'high' | 'critical'

export type CyberNodeTemplate = {
  id: string
  title: string
  icon: string
  group: 'Home / small network' | 'Business / company network'
  node_type: string
  template_type: string
  criticality: Criticality
  zone: 'home' | 'guest' | 'work' | 'cloud' | 'dmz' | 'internal' | 'critical'
  is_internet_exposed: boolean
  has_admin_privileges: boolean
  notes: string
}

export type CyberEdgeTemplate = {
  edge_type: string
  label: string
  meaning: string
  default_risk: 'low' | 'medium' | 'high'
  risk_weight: number
  direction: 'bidirectional' | 'source_to_target'
  risk_can_spread_both_ways: boolean
}

export const CYBER_NODE_TEMPLATES: CyberNodeTemplate[] = [
  {
    id: 'router',
    title: 'Router',
    icon: '📡',
    group: 'Home / small network',
    node_type: 'router',
    template_type: 'network_device',
    criticality: 'high',
    zone: 'home',
    is_internet_exposed: true,
    has_admin_privileges: false,
    notes: 'Home or small office network gateway.',
  },
  {
    id: 'laptop',
    title: 'Laptop',
    icon: '💻',
    group: 'Home / small network',
    node_type: 'laptop',
    template_type: 'workstation',
    criticality: 'medium',
    zone: 'home',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Personal laptop or everyday endpoint.',
  },
  {
    id: 'work-laptop',
    title: 'Work Laptop',
    icon: '💼',
    group: 'Home / small network',
    node_type: 'work_laptop',
    template_type: 'workstation',
    criticality: 'high',
    zone: 'work',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Managed work endpoint.',
  },
  {
    id: 'phone',
    title: 'Phone',
    icon: '📱',
    group: 'Home / small network',
    node_type: 'phone',
    template_type: 'workstation',
    criticality: 'medium',
    zone: 'home',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Mobile device on the network.',
  },
  {
    id: 'tablet',
    title: 'Tablet',
    icon: '▭',
    group: 'Home / small network',
    node_type: 'tablet',
    template_type: 'workstation',
    criticality: 'low',
    zone: 'home',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Tablet endpoint.',
  },
  {
    id: 'printer',
    title: 'Printer',
    icon: '🖨️',
    group: 'Home / small network',
    node_type: 'printer',
    template_type: 'device',
    criticality: 'low',
    zone: 'home',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Network printer.',
  },
  {
    id: 'smart-tv',
    title: 'Smart TV',
    icon: '📺',
    group: 'Home / small network',
    node_type: 'smart_tv',
    template_type: 'iot',
    criticality: 'low',
    zone: 'home',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Smart television or media device.',
  },
  {
    id: 'security-camera',
    title: 'Security Camera',
    icon: '📷',
    group: 'Home / small network',
    node_type: 'security_camera',
    template_type: 'iot',
    criticality: 'medium',
    zone: 'home',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Camera or recorder device.',
  },
  {
    id: 'nas-home-server',
    title: 'NAS / Home Server',
    icon: '🗄️',
    group: 'Home / small network',
    node_type: 'nas_home_server',
    template_type: 'server',
    criticality: 'high',
    zone: 'home',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Local storage or home server.',
  },
  {
    id: 'iot-device',
    title: 'Smart Speaker / IoT Device',
    icon: '🔊',
    group: 'Home / small network',
    node_type: 'iot_device',
    template_type: 'iot',
    criticality: 'low',
    zone: 'home',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Generic IoT device.',
  },
  {
    id: 'game-console',
    title: 'Game Console',
    icon: '🎮',
    group: 'Home / small network',
    node_type: 'game_console',
    template_type: 'device',
    criticality: 'low',
    zone: 'home',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Console or entertainment device.',
  },
  {
    id: 'guest-device',
    title: 'Guest Device',
    icon: '👥',
    group: 'Home / small network',
    node_type: 'guest_device',
    template_type: 'workstation',
    criticality: 'low',
    zone: 'guest',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Unmanaged guest endpoint.',
  },
  {
    id: 'cloud-account',
    title: 'Cloud Account',
    icon: '☁️',
    group: 'Home / small network',
    node_type: 'cloud_account',
    template_type: 'identity',
    criticality: 'high',
    zone: 'cloud',
    is_internet_exposed: true,
    has_admin_privileges: false,
    notes: 'Cloud identity or SaaS account.',
  },
  {
    id: 'admin-account',
    title: 'Admin Account',
    icon: '🔑',
    group: 'Home / small network',
    node_type: 'admin_account',
    template_type: 'identity',
    criticality: 'critical',
    zone: 'critical',
    is_internet_exposed: false,
    has_admin_privileges: true,
    notes: 'Privileged account with management rights.',
  },
  {
    id: 'internet',
    title: 'Internet',
    icon: '🌐',
    group: 'Home / small network',
    node_type: 'internet',
    template_type: 'network_device',
    criticality: 'high',
    zone: 'dmz',
    is_internet_exposed: true,
    has_admin_privileges: false,
    notes: 'External internet boundary.',
  },
  {
    id: 'workstation',
    title: 'Workstation',
    icon: '🖥️',
    group: 'Business / company network',
    node_type: 'workstation',
    template_type: 'workstation',
    criticality: 'medium',
    zone: 'internal',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Business endpoint.',
  },
  {
    id: 'file-server',
    title: 'File Server',
    icon: '📁',
    group: 'Business / company network',
    node_type: 'file_server',
    template_type: 'server',
    criticality: 'high',
    zone: 'internal',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Shared file server.',
  },
  {
    id: 'database',
    title: 'Database',
    icon: '🛢️',
    group: 'Business / company network',
    node_type: 'database',
    template_type: 'database',
    criticality: 'critical',
    zone: 'critical',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Business data store.',
  },
  {
    id: 'vpn-gateway',
    title: 'VPN Gateway',
    icon: '🔐',
    group: 'Business / company network',
    node_type: 'vpn_gateway',
    template_type: 'network_device',
    criticality: 'high',
    zone: 'dmz',
    is_internet_exposed: true,
    has_admin_privileges: false,
    notes: 'Remote access gateway.',
  },
  {
    id: 'firewall',
    title: 'Firewall',
    icon: '🧱',
    group: 'Business / company network',
    node_type: 'firewall',
    template_type: 'network_device',
    criticality: 'high',
    zone: 'dmz',
    is_internet_exposed: true,
    has_admin_privileges: false,
    notes: 'Network firewall.',
  },
  {
    id: 'domain-controller',
    title: 'Domain Controller',
    icon: '🏛️',
    group: 'Business / company network',
    node_type: 'domain_controller',
    template_type: 'critical_asset',
    criticality: 'critical',
    zone: 'critical',
    is_internet_exposed: false,
    has_admin_privileges: true,
    notes: 'Identity control plane.',
  },
  {
    id: 'backup-server',
    title: 'Backup Server',
    icon: '💾',
    group: 'Business / company network',
    node_type: 'backup_server',
    template_type: 'server',
    criticality: 'high',
    zone: 'internal',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Backup and recovery server.',
  },
  {
    id: 'monitoring-system',
    title: 'Monitoring System',
    icon: '📈',
    group: 'Business / company network',
    node_type: 'monitoring_system',
    template_type: 'security_tool',
    criticality: 'high',
    zone: 'internal',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Security monitoring platform.',
  },
  {
    id: 'critical-service',
    title: 'Critical Service',
    icon: '⭐',
    group: 'Business / company network',
    node_type: 'critical_service',
    template_type: 'critical_asset',
    criticality: 'critical',
    zone: 'critical',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Important business service.',
  },
  {
    id: 'operations-server',
    title: 'Operations Server',
    icon: '⚙️',
    group: 'Business / company network',
    node_type: 'operations_server',
    template_type: 'critical_asset',
    criticality: 'critical',
    zone: 'critical',
    is_internet_exposed: false,
    has_admin_privileges: false,
    notes: 'Operations or production service.',
  },
]

export const CYBER_EDGE_TEMPLATES: CyberEdgeTemplate[] = [
  {
    edge_type: 'same_network',
    label: 'Same network',
    meaning: 'Devices are on the same network/subnet.',
    default_risk: 'low',
    risk_weight: 25,
    direction: 'bidirectional',
    risk_can_spread_both_ways: true,
  },
  {
    edge_type: 'can_access',
    label: 'Can access',
    meaning: 'Source can reach or use target.',
    default_risk: 'medium',
    risk_weight: 55,
    direction: 'source_to_target',
    risk_can_spread_both_ways: true,
  },
  {
    edge_type: 'administers',
    label: 'Administers',
    meaning: 'Source can manage target.',
    default_risk: 'high',
    risk_weight: 85,
    direction: 'source_to_target',
    risk_can_spread_both_ways: false,
  },
  {
    edge_type: 'stores_credentials_for',
    label: 'Stores credentials for',
    meaning: 'Source stores credentials that can access target.',
    default_risk: 'high',
    risk_weight: 90,
    direction: 'source_to_target',
    risk_can_spread_both_ways: false,
  },
  {
    edge_type: 'controls',
    label: 'Controls',
    meaning: 'Source controls target system/account.',
    default_risk: 'high',
    risk_weight: 90,
    direction: 'source_to_target',
    risk_can_spread_both_ways: false,
  },
  {
    edge_type: 'depends_on',
    label: 'Depends on',
    meaning: 'Source depends on target to function.',
    default_risk: 'medium',
    risk_weight: 50,
    direction: 'source_to_target',
    risk_can_spread_both_ways: false,
  },
  {
    edge_type: 'routes_through',
    label: 'Routes through',
    meaning: 'Traffic passes through target.',
    default_risk: 'medium',
    risk_weight: 55,
    direction: 'source_to_target',
    risk_can_spread_both_ways: true,
  },
  {
    edge_type: 'backs_up',
    label: 'Backs up',
    meaning: 'Source backs up target.',
    default_risk: 'medium',
    risk_weight: 45,
    direction: 'source_to_target',
    risk_can_spread_both_ways: false,
  },
  {
    edge_type: 'monitors',
    label: 'Monitors',
    meaning: 'Source monitors target.',
    default_risk: 'low',
    risk_weight: 25,
    direction: 'source_to_target',
    risk_can_spread_both_ways: false,
  },
  {
    edge_type: 'internet_exposes',
    label: 'Internet exposes',
    meaning: 'Source exposes target to internet access.',
    default_risk: 'high',
    risk_weight: 85,
    direction: 'source_to_target',
    risk_can_spread_both_ways: false,
  },
]

export function getEdgeTemplate(edgeType: string) {
  return CYBER_EDGE_TEMPLATES.find((template) => template.edge_type === edgeType)
}

export function getNodeTemplate(templateId: string) {
  return CYBER_NODE_TEMPLATES.find((template) => template.id === templateId)
}

export function suggestEdgeTypes(sourceType?: string, targetType?: string) {
  const source = sourceType ?? ''
  const target = targetType ?? ''

  if (source.includes('laptop') && target === 'printer') return ['can_access', 'same_network']
  if (source.includes('laptop') && target === 'router') return ['same_network', 'routes_through']
  if (source === 'router' && target === 'internet') return ['routes_through']
  if (source === 'admin_account' && ['router', 'server', 'file_server'].includes(target)) {
    return ['administers']
  }
  if (source === 'work_laptop' && target === 'vpn_gateway') return ['can_access']
  if (source === 'vpn_gateway' && ['file_server', 'operations_server', 'critical_service'].includes(target)) {
    return ['can_access']
  }
  if (source === 'file_server' && target === 'admin_account') return ['stores_credentials_for']
  if (source === 'domain_controller' && target === 'workstation') return ['controls']
  if (source === 'backup_server' && target === 'file_server') return ['backs_up']
  if (source === 'monitoring_system' && target.includes('server')) return ['monitors']

  return ['can_access', 'same_network', 'routes_through']
}
