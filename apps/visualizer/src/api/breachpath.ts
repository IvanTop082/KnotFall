export type BreachPathAnalysisEdgeRef = {
  source: string
  target: string
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

export type BreachPathCompromisedNodeAnalysis = {
  compromised_node: {
    id: string
    label: string
    type: string
  }
  summary: {
    affected_node_count: number
    affected_edge_count: number
    critical_assets_reachable: number
    highest_risk_score: number
    risk_level: string
  }
  highlighted_nodes: string[]
  highlighted_edges: BreachPathAnalysisEdgeRef[]
  paths: BreachPathAnalysisPath[]
  recommendations: BreachPathAnalysisRecommendation[]
  defensive_note: string
}

export type BreachPathGraphPayload = {
  metadata: Record<string, string>
  nodes: unknown[]
  edges: unknown[]
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
  graph: BreachPathGraphPayload
): Promise<BreachPathCompromisedNodeAnalysis> {
  const response = await fetch(`${getBreachPathApiBaseUrl()}/analysis/compromised`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      node_id: nodeId,
      graph,
    }),
  })

  return parseAnalysisResponse(response)
}
