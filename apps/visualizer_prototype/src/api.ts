import type { CompromisedNodeAnalysis, GraphResponse } from "./types";

const API_BASE_URL =
  import.meta.env.VITE_BREACHPATH_API_URL || "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const body = await response.json();
      if (body.detail) {
        message = body.detail;
      }
    } catch {
      // Keep the status message if the API does not return JSON.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function getGraph(): Promise<GraphResponse> {
  return fetchJson<GraphResponse>("/graph");
}

export function getCompromisedAnalysis(
  nodeId: string,
): Promise<CompromisedNodeAnalysis> {
  return fetchJson<CompromisedNodeAnalysis>(
    `/analysis/compromised/${encodeURIComponent(nodeId)}`,
  );
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}
