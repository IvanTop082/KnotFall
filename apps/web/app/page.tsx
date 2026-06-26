"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import NodeSelector from "../components/NodeSelector";
import RecommendationsPanel from "../components/RecommendationsPanel";
import RiskPanel from "../components/RiskPanel";
import StatusCard from "../components/StatusCard";
import {
  getAttackPaths,
  getGraph,
  getHealth,
  getRecommendations,
} from "../lib/api";
import type {
  AttackPathResponse,
  GraphResponse,
  RecommendationResponse,
  RiskLevel,
} from "../lib/types";

const GraphView = dynamic(() => import("../components/GraphView"), {
  ssr: false,
});

function riskTone(riskLevel: RiskLevel | "none") {
  if (riskLevel === "high") {
    return "danger";
  }
  if (riskLevel === "medium") {
    return "warn";
  }
  if (riskLevel === "low") {
    return "good";
  }
  return "neutral";
}

function getHighestRiskLevel(response: AttackPathResponse | null) {
  if (!response || response.results.length === 0) {
    return "none";
  }

  if (response.results.some((result) => result.risk_level === "high")) {
    return "high";
  }

  if (response.results.some((result) => result.risk_level === "medium")) {
    return "medium";
  }

  return "low";
}

export default function HomePage() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [attackPaths, setAttackPaths] = useState<AttackPathResponse | null>(
    null,
  );
  const [recommendations, setRecommendations] =
    useState<RecommendationResponse | null>(null);
  const [backendStatus, setBackendStatus] = useState("checking");
  const [graphError, setGraphError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [recommendationError, setRecommendationError] = useState<string | null>(
    null,
  );
  const [isGraphLoading, setIsGraphLoading] = useState(true);
  const [isAnalysisLoading, setIsAnalysisLoading] = useState(false);
  const [isRecommendationLoading, setIsRecommendationLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadInitialData() {
      try {
        await getHealth();
        if (isMounted) {
          setBackendStatus("online");
        }
      } catch {
        if (isMounted) {
          setBackendStatus("offline");
        }
      }

      try {
        const graphData = await getGraph();
        if (isMounted) {
          setGraph(graphData);
          setGraphError(null);
        }
      } catch (error) {
        if (isMounted) {
          setGraphError(
            error instanceof Error ? error.message : "Could not load graph.",
          );
        }
      } finally {
        if (isMounted) {
          setIsGraphLoading(false);
        }
      }
    }

    loadInitialData();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedNodeId) {
      setAttackPaths(null);
      setRecommendations(null);
      setAnalysisError(null);
      setRecommendationError(null);
      return;
    }

    let isMounted = true;

    async function analyseNode() {
      setIsAnalysisLoading(true);
      setIsRecommendationLoading(true);
      setAnalysisError(null);
      setRecommendationError(null);

      const [attackPathResult, recommendationResult] = await Promise.allSettled([
        getAttackPaths(selectedNodeId),
        getRecommendations(selectedNodeId),
      ]);

      if (!isMounted) {
        return;
      }

      if (attackPathResult.status === "fulfilled") {
        setAttackPaths(attackPathResult.value);
      } else {
        setAttackPaths(null);
        setAnalysisError(
          attackPathResult.reason instanceof Error
            ? attackPathResult.reason.message
            : "Could not analyse attack paths.",
        );
      }

      if (recommendationResult.status === "fulfilled") {
        setRecommendations(recommendationResult.value);
      } else {
        setRecommendations(null);
        setRecommendationError(
          recommendationResult.reason instanceof Error
            ? recommendationResult.reason.message
            : "Could not simulate recommendations.",
        );
      }

      setIsAnalysisLoading(false);
      setIsRecommendationLoading(false);
    }

    analyseNode();

    return () => {
      isMounted = false;
    };
  }, [selectedNodeId]);

  const selectedNode = useMemo(
    () => graph?.nodes.find((node) => node.id === selectedNodeId),
    [graph, selectedNodeId],
  );

  const highestRiskLevel = getHighestRiskLevel(attackPaths);
  const attackPathResults = attackPaths?.results || [];

  return (
    <main className="min-h-screen bg-breach-black">
      <header className="border-b border-slate-800 bg-slate-950/80 px-6 py-5">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-wide text-orange-300">
              Cyber defence graph analysis
            </p>
            <h1 className="text-3xl font-bold text-slate-50">BreachPath</h1>
          </div>
          <p className="max-w-2xl text-sm text-slate-400">
            Select a suspected compromise point and trace reachable critical
            assets through the demo mission network.
          </p>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-6 py-6 lg:grid-cols-[380px_1fr]">
        <aside className="space-y-5">
          <div className="grid grid-cols-2 gap-3">
            <StatusCard
              label="Backend"
              value={backendStatus}
              detail="FastAPI"
              tone={backendStatus === "online" ? "good" : "danger"}
            />
            <StatusCard
              label="Selected"
              value={selectedNode?.label || "None"}
              detail={selectedNode?.type.replace("_", " ") || "Awaiting input"}
            />
            <StatusCard
              label="Paths"
              value={attackPaths?.paths_found || 0}
              detail="Reachable routes"
              tone={attackPaths?.paths_found ? "warn" : "neutral"}
            />
            <StatusCard
              label="Highest risk"
              value={highestRiskLevel}
              detail="Current analysis"
              tone={riskTone(highestRiskLevel)}
            />
          </div>

          {graph ? (
            <NodeSelector
              nodes={graph.nodes}
              selectedNodeId={selectedNodeId}
              onSelect={setSelectedNodeId}
            />
          ) : null}

          <RiskPanel
            selectedNodeId={selectedNodeId}
            response={attackPaths}
            isLoading={isAnalysisLoading}
            error={analysisError}
          />

          <RecommendationsPanel
            selectedNodeId={selectedNodeId}
            response={recommendations}
            isLoading={isRecommendationLoading}
            error={recommendationError}
          />
        </aside>

        <section>
          {isGraphLoading ? (
            <div className="flex h-[720px] items-center justify-center rounded-lg border border-slate-800 bg-breach-panel text-slate-300">
              Loading demo network...
            </div>
          ) : graphError ? (
            <div className="flex h-[720px] items-center justify-center rounded-lg border border-red-500/40 bg-red-500/10 p-8 text-center text-red-100">
              {graphError}
            </div>
          ) : graph ? (
            <GraphView
              nodes={graph.nodes}
              edges={graph.edges}
              selectedNodeId={selectedNodeId}
              attackPathResults={attackPathResults}
            />
          ) : null}
        </section>
      </div>
    </main>
  );
}
