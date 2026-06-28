export type BreachPathAnalysisEdgeRef = {
  source: string
  target: string
  relationship?: string | null
}

export type BreachPathAnalysisPath = {
  target: string
  risk_score: number
  risk_level: string
  nodes: string[]
  edges: BreachPathAnalysisEdgeRef[]
  explanation: string
}

export type BreachPathAnalysisRecommendation = {
  title: string
  type: string
  priority: string
  estimated_risk_reduction: number
  explanation: string
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
  risk_score: number
  risk_level: string
  highlighted_nodes: string[]
  highlighted_edges: BreachPathAnalysisEdgeRef[]
  paths: BreachPathAnalysisPath[]
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
  status: string
  storage_backend: string
  turingdb_host: string
  message: string
  mode?: 'turingdb' | 'local_fallback'
  connected?: boolean
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
  const status = await parseJsonResponse<{
    mode: 'turingdb' | 'local_fallback'
    connected: boolean
    message: string
  }>(response)

  return {
    status: status.connected ? 'connected' : 'local_fallback',
    storage_backend: status.mode,
    turingdb_host: '',
    message: status.message,
    mode: status.mode,
    connected: status.connected,
  }
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
