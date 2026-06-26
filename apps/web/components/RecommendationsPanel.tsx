import type {
  RecommendationLevel,
  RecommendationResponse,
  RecommendationResult,
} from "../lib/types";

interface RecommendationsPanelProps {
  selectedNodeId: string;
  response: RecommendationResponse | null;
  isLoading: boolean;
  error: string | null;
}

const levelClasses: Record<RecommendationLevel, string> = {
  strong: "border-emerald-500/50 bg-emerald-500/10 text-emerald-100",
  useful: "border-sky-500/50 bg-sky-500/10 text-sky-100",
  limited: "border-orange-500/50 bg-orange-500/10 text-orange-100",
  weak: "border-slate-600 bg-slate-800/60 text-slate-200",
};

function protectedAssetsText(result: RecommendationResult) {
  if (result.critical_assets_protected.length === 0) {
    return "No complete critical-asset paths removed.";
  }

  return result.critical_assets_protected.join(", ");
}

export default function RecommendationsPanel({
  selectedNodeId,
  response,
  isLoading,
  error,
}: RecommendationsPanelProps) {
  if (!selectedNodeId) {
    return null;
  }

  if (isLoading) {
    return (
      <section className="rounded-lg border border-slate-800 bg-breach-panel p-5 text-sm text-slate-300">
        Simulating defensive improvements...
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-lg border border-red-500/40 bg-red-500/10 p-5 text-sm text-red-100">
        {error}
      </section>
    );
  }

  if (!response || response.results.length === 0) {
    return (
      <section className="rounded-lg border border-slate-800 bg-breach-panel p-5 text-sm text-slate-300">
        {response?.message ||
          "No urgent blocking recommendation is needed for this node."}
      </section>
    );
  }

  const bestRecommendation = response.results[0];

  return (
    <section className="rounded-lg border border-slate-800 bg-breach-panel p-5">
      <div>
        <p className="text-sm uppercase tracking-wide text-slate-500">
          Recommendation simulation
        </p>
        <h2 className="mt-1 text-xl font-semibold text-slate-100">
          Best action: {bestRecommendation.title}
        </h2>
      </div>

      <div className="mt-5 rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-emerald-100">
              {bestRecommendation.reason}
            </p>
            <p className="mt-2 text-sm text-slate-300">
              Tradeoff: {bestRecommendation.tradeoff}
            </p>
          </div>
          <span
            className={`rounded-md border px-2 py-1 text-xs font-semibold uppercase ${levelClasses[bestRecommendation.recommendation_level]}`}
          >
            {bestRecommendation.recommendation_level} -{" "}
            {bestRecommendation.recommendation_score}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
          <div>
            <p className="text-slate-500">Before risk</p>
            <p className="text-lg font-semibold text-slate-100">
              {bestRecommendation.baseline_total_risk}
            </p>
          </div>
          <div>
            <p className="text-slate-500">After risk</p>
            <p className="text-lg font-semibold text-slate-100">
              {bestRecommendation.after_total_risk}
            </p>
          </div>
          <div>
            <p className="text-slate-500">Reduction</p>
            <p className="text-lg font-semibold text-emerald-100">
              {bestRecommendation.risk_reduction}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        <p className="text-sm font-medium text-slate-300">
          Other options ranked
        </p>

        {response.results.map((result) => (
          <article
            key={result.improvement_id}
            className="rounded-lg border border-slate-800 bg-slate-950/60 p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold text-slate-100">{result.title}</h3>
                <p className="mt-1 text-xs uppercase text-slate-500">
                  Risk reduction {result.risk_reduction} - cost{" "}
                  {result.operational_cost} - removed paths{" "}
                  {result.paths_removed_count}
                </p>
              </div>
              <span
                className={`rounded-md border px-2 py-1 text-xs font-semibold uppercase ${levelClasses[result.recommendation_level]}`}
              >
                {result.recommendation_level}
              </span>
            </div>

            <p className="mt-3 text-sm text-slate-300">{result.reason}</p>
            <p className="mt-2 text-sm text-slate-400">
              Protected: {protectedAssetsText(result)}
            </p>
            {result.why_not_enough ? (
              <p className="mt-2 text-sm text-orange-200">
                Why not enough: {result.why_not_enough}
              </p>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
