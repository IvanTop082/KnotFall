import type {
  AttackPathResponse,
  GraphResponse,
  HealthResponse,
  RecommendationResponse,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorBody = await response.json();
      if (errorBody.detail) {
        message = errorBody.detail;
      }
    } catch {
      // Keep the status-based message if the API does not return JSON.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/health");
}

export function getGraph(): Promise<GraphResponse> {
  return fetchJson<GraphResponse>("/graph");
}

export function getAttackPaths(
  compromisedNodeId: string,
): Promise<AttackPathResponse> {
  return fetchJson<AttackPathResponse>(
    `/attack-paths/${encodeURIComponent(compromisedNodeId)}`,
  );
}

export function getRecommendations(
  compromisedNodeId: string,
): Promise<RecommendationResponse> {
  return fetchJson<RecommendationResponse>(
    `/recommendations/${encodeURIComponent(compromisedNodeId)}`,
  );
}
