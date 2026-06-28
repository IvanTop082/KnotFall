export type BreachPathAnalysisEdgeRef = {
  id?: string | null
  source: string
  target: string
  relationship?: string | null
  blocked_or_reduced_by?: string[]
}

export type BreachPathAnalysisPath = {
  path_id?: string | null
  target: string
  risk_score: number
  risk_level: string
  nodes: string[]
  edges: BreachPathAnalysisEdgeRef[]
  explanation: string
  edge_ids?: string[]
  edge_types?: string[]
  target_node?: string | null
  target_criticality?: number | null
  score?: number | null
  severity?: string | null
  why_this_path_matters?: string | null
  blocked_or_reduced_by?: string[]
}

export type BreachPathRankedPath = {
  path_id: string
  nodes: string[]
  edges: string[]
  edge_refs?: BreachPathAnalysisEdgeRef[]
  edge_types: string[]
  target_node: string
  target_criticality: number
  score: number
  severity: string
  why_this_path_matters: string
  blocked_or_reduced_by: string[]
}

export type BreachPathBlockedPath = {
  path_id: string
  nodes: string[]
  edges?: string[]
  edge_refs?: BreachPathAnalysisEdgeRef[]
  edge_types?: string[]
  target_node?: string | null
  reason: string
  severity: string
}

export type BreachPathTraversalEdgeDecision = {
  edge_id: string
  from: string
  to: string
  edge_type: string
  direction: string
  decision: string
  reason: string
  from_label?: string | null
  to_label?: string | null
  score?: number | null
}

export type BreachPathRankedButNotHighlightedPath = {
  nodes: string[]
  edges?: string[]
  edge_types?: string[]
  score: number
  reason: string
}

export type BreachPathConnectedButNotHighlighted = {
  node_id: string
  label: string
  reason: string
  edge_id?: string | null
  edge_type?: string | null
}

export type BreachPathTraversalExplanation = {
  source_node: string
  simulation_type: BreachPathSimulationType | string
  highlight_threshold: number
  max_highlighted_paths: number
  followed_edges: BreachPathTraversalEdgeDecision[]
  skipped_edges: BreachPathTraversalEdgeDecision[]
  ranked_but_not_highlighted_paths: BreachPathRankedButNotHighlightedPath[]
  connected_but_not_highlighted: BreachPathConnectedButNotHighlighted[]
  reachable_nodes: string[]
  reachable_edges: BreachPathAnalysisEdgeRef[]
}

export type BreachPathAnalysisRecommendation = {
  title: string
  type: string
  priority: string
  estimated_risk_reduction: number
  explanation: string
  severity?: string | null
  reason?: string | null
  triggered_by_path?: string[]
  affected_nodes?: string[]
  relevant_edge_types?: string[]
  simulation_type?: BreachPathSimulationType | string | null
  what_it_fixes?: string | null
  expected_effect?: string | null
  confidence?: string | null
  action_steps?: string[]
}

export type BreachPathSimulationType =
  | 'compromise'
  | 'offline'
  | 'spyware'
  | 'data_leak'
  | 'lateral_movement'

export type BreachPathCompromisedNodeAnalysis = {
  compromised_node: {
    id: string
    label: string
    type: string
  }
  source_node?: {
    id: string
    label: string
    type: string
  } | null
  network_id?: string | null
  version?: number | null
  graph_hash?: string | null
  analysed_at?: string | null
  simulation_type: BreachPathSimulationType
  summary: {
    affected_node_count: number
    affected_edge_count: number
    critical_assets_reachable: number
    highest_risk_score: number
    risk_level: string
  }
  summary_text?: string | null
  risk_score: number
  risk_level: string
  highlighted_nodes: string[]
  highlighted_edges: BreachPathAnalysisEdgeRef[]
  paths: BreachPathAnalysisPath[]
  top_paths?: BreachPathRankedPath[]
  affected_nodes?: string[]
  critical_nodes_reached?: string[]
  blocked_or_reduced_paths?: BreachPathBlockedPath[]
  low_relevance_nodes?: string[]
  traversal_explanation?: BreachPathTraversalExplanation | null
  recommendations: BreachPathAnalysisRecommendation[]
  explanation: string
  followed_edge_types: string[]
  visual_severity_by_node: Record<string, string>
  visual_severity_by_edge: Record<string, string>
  defensive_note: string
}

export type BreachPathGraphPayload = {
  metadata: Record<string, string>
  nodes: unknown[]
  edges: unknown[]
}

export type BreachPathNetworkSaveResponse = {
  network_id: string
  name?: string | null
  commit_id: string
  version: number
  message?: string | null
  created_at?: string | null
  node_count?: number | null
  edge_count?: number | null
  status: string
  storage_backend: string
  warning?: string | null
}

export type BreachPathSavedNetwork = {
  network_id: string
  name: string
  graph: BreachPathGraphPayload
  version: number
  commit_id: string
  updated_at: string
  storage_backend: string
}

export type BreachPathNetworkSummary = {
  network_id: string
  name: string
  version: number
  updated_at: string
  node_count: number
  edge_count: number
  storage_backend: string
}

export type BreachPathNetworkCommit = {
  commit_id: string
  version: number
  message: string
  created_at: string
  node_count: number
  edge_count: number
  analysed: boolean
  analysis_count: number
}

export type BreachPathSavedNetworkVersion = {
  network_id: string
  name: string
  graph: BreachPathGraphPayload
  version: number
  commit_id: string
  message: string
  created_at: string
  node_count: number
  edge_count: number
  analysed: boolean
  analysis_count: number
}

export type BreachPathNetworkCompare = {
  network_id: string
  from_version: number
  to_version: number
  added_nodes: Record<string, unknown>[]
  removed_nodes: Record<string, unknown>[]
  changed_nodes: Record<string, unknown>[]
  added_edges: Record<string, unknown>[]
  removed_edges: Record<string, unknown>[]
  changed_edges: Record<string, unknown>[]
  summary: Record<string, number>
}

export type BreachPathStorageStatus = {
  mode: 'turingdb' | 'local_fallback'
  connected: boolean
  repository: string
  turingdb_url: string
  sdk_available?: boolean
  http_server_reachable?: boolean
  graph_writes_supported?: boolean
  graph_storage?: string
  metadata_storage?: string
  storage_backend: string
  message: string
}

export function formatStorageStatusLabel(status: BreachPathStorageStatus): string {
  if (status.mode === 'local_fallback') {
    return 'Storage: Local fallback'
  }
  if (status.connected) {
    return 'Storage: TuringDB connected'
  }
  return 'Storage: TuringDB disconnected'
}

export function storageStatusBadgeClass(status: BreachPathStorageStatus): string {
  if (status.mode === 'local_fallback') {
    return 'text-amber-200 border-amber-700/70'
  }
  if (status.connected) {
    return 'text-green-200 border-green-700/70'
  }
  return 'text-red-200 border-red-700/70'
}

export type BreachPathAnalysisMetadata = {
  networkId?: string
  version?: number
  graphHash?: string
}

export function getBreachPathApiBaseUrl() {
  return (import.meta.env.VITE_BREACHPATH_API_URL || 'http://localhost:8000').replace(/\/+$/, '')
}

async function parseAnalysisResponse(response: Response) {
  if (!response.ok) {
    let message = `BreachPath API returned ${response.status}`

    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // Keep the status-derived message when the response body is not JSON.
    }

    throw new Error(message)
  }

  return response.json() as Promise<BreachPathCompromisedNodeAnalysis>
}

export async function getCompromisedNodeAnalysis(
  nodeId: string
): Promise<BreachPathCompromisedNodeAnalysis> {
  const response = await fetch(
    `${getBreachPathApiBaseUrl()}/analysis/compromised/${encodeURIComponent(nodeId)}`
  )

  return parseAnalysisResponse(response)
}

export async function postCompromisedNodeAnalysis(
  nodeId: string,
  graph: BreachPathGraphPayload,
  simulationType: BreachPathSimulationType = 'compromise',
  metadata: BreachPathAnalysisMetadata = {}
): Promise<BreachPathCompromisedNodeAnalysis> {
  const response = await fetch(`${getBreachPathApiBaseUrl()}/analysis/compromised`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      node_id: nodeId,
      simulation_type: simulationType,
      network_id: metadata.networkId,
      version: metadata.version,
      graph_hash: metadata.graphHash,
      graph,
    }),
  })

  return parseAnalysisResponse(response)
}

export async function getBreachPathStorageStatus(): Promise<BreachPathStorageStatus> {
  const response = await fetch(`${getBreachPathApiBaseUrl()}/storage/status`)
  return parseJsonResponse<BreachPathStorageStatus>(response)
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `BreachPath API returned ${response.status}`

    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // Keep the status-derived message when the response body is not JSON.
    }

    throw new Error(message)
  }

  return response.json() as Promise<T>
}

export async function saveBreachPathNetwork(args: {
  networkId: string
  name: string
  graph: BreachPathGraphPayload
  message: string
}): Promise<BreachPathNetworkSaveResponse> {
  const response = await fetch(`${getBreachPathApiBaseUrl()}/networks/save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      network_id: args.networkId,
      name: args.name,
      graph: args.graph,
      message: args.message,
    }),
  })

  return parseJsonResponse<BreachPathNetworkSaveResponse>(response)
}

export async function saveBreachPathNetworkVersion(args: {
  networkId: string
  name?: string
  graph: BreachPathGraphPayload
  message: string
}): Promise<BreachPathNetworkSaveResponse> {
  const response = await fetch(`${getBreachPathApiBaseUrl()}/networks/save-version`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      network_id: args.networkId,
      name: args.name,
      graph: args.graph,
      message: args.message,
    }),
  })

  return parseJsonResponse<BreachPathNetworkSaveResponse>(response)
}

export async function saveBreachPathNetworkVersionForNetwork(args: {
  networkId: string
  name?: string
  graph: BreachPathGraphPayload
  message: string
}): Promise<BreachPathNetworkSaveResponse> {
  const response = await fetch(
    `${getBreachPathApiBaseUrl()}/networks/${encodeURIComponent(args.networkId)}/versions`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        network_id: args.networkId,
        name: args.name,
        graph: args.graph,
        message: args.message,
      }),
    }
  )

  return parseJsonResponse<BreachPathNetworkSaveResponse>(response)
}

export async function loadBreachPathNetwork(networkId: string): Promise<BreachPathSavedNetwork> {
  const response = await fetch(
    `${getBreachPathApiBaseUrl()}/networks/${encodeURIComponent(networkId)}`
  )
  return parseJsonResponse<BreachPathSavedNetwork>(response)
}

export async function listBreachPathNetworks(): Promise<BreachPathNetworkSummary[]> {
  const response = await fetch(`${getBreachPathApiBaseUrl()}/networks`)
  return parseJsonResponse<BreachPathNetworkSummary[]>(response)
}

export async function deleteBreachPathNetwork(networkId: string): Promise<void> {
  const response = await fetch(
    `${getBreachPathApiBaseUrl()}/networks/${encodeURIComponent(networkId)}`,
    { method: 'DELETE' }
  )
  await parseJsonResponse<{ status: string }>(response)
}

export async function getBreachPathNetworkHistory(
  networkId: string
): Promise<BreachPathNetworkCommit[]> {
  const response = await fetch(
    `${getBreachPathApiBaseUrl()}/networks/${encodeURIComponent(networkId)}/history`
  )
  return parseJsonResponse<BreachPathNetworkCommit[]>(response)
}

export async function listBreachPathNetworkVersions(
  networkId: string
): Promise<BreachPathNetworkCommit[]> {
  const response = await fetch(
    `${getBreachPathApiBaseUrl()}/networks/${encodeURIComponent(networkId)}/versions`
  )
  return parseJsonResponse<BreachPathNetworkCommit[]>(response)
}

export async function loadBreachPathNetworkVersion(
  networkId: string,
  version: number
): Promise<BreachPathSavedNetworkVersion> {
  const response = await fetch(
    `${getBreachPathApiBaseUrl()}/networks/${encodeURIComponent(networkId)}/versions/${version}`
  )
  return parseJsonResponse<BreachPathSavedNetworkVersion>(response)
}

export async function restoreBreachPathNetworkVersion(
  networkId: string,
  version: number
): Promise<BreachPathNetworkSaveResponse> {
  const response = await fetch(
    `${getBreachPathApiBaseUrl()}/networks/${encodeURIComponent(networkId)}/restore/${version}`,
    { method: 'POST' }
  )
  return parseJsonResponse<BreachPathNetworkSaveResponse>(response)
}

export async function compareBreachPathNetworkVersions(
  networkId: string,
  fromVersion: number,
  toVersion: number
): Promise<BreachPathNetworkCompare> {
  const search = new URLSearchParams({
    from_version: String(fromVersion),
    to_version: String(toVersion),
  })
  const response = await fetch(
    `${getBreachPathApiBaseUrl()}/networks/${encodeURIComponent(networkId)}/compare?${search}`
  )
  return parseJsonResponse<BreachPathNetworkCompare>(response)
}
