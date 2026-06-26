import type { AttackPathResponse } from "../lib/types";

interface RiskPanelProps {
  selectedNodeId: string;
  response: AttackPathResponse | null;
  isLoading: boolean;
  error: string | null;
}

const riskClasses = {
  low: "border-emerald-500/40 bg-emerald-500/10 text-emerald-100",
  medium: "border-orange-500/40 bg-orange-500/10 text-orange-100",
  high: "border-red-500/40 bg-red-500/10 text-red-100",
};

export default function RiskPanel({
  selectedNodeId,
  response,
  isLoading,
  error,
}: RiskPanelProps) {
  if (!selectedNodeId) {
    return (
      <section className="rounded-lg border border-slate-800 bg-breach-panel p-5 text-sm text-slate-300">
        Select a compromised node to analyse possible attack paths.
      </section>
    );
  }

  if (isLoading) {
    return (
      <section className="rounded-lg border border-slate-800 bg-breach-panel p-5 text-sm text-slate-300">
        Analysing reachable critical assets...
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
        No critical assets reachable within the current search depth.
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-slate-800 bg-breach-panel p-5">
      <div>
        <p className="text-sm uppercase tracking-wide text-slate-500">
          Attack path results
        </p>
        <h2 className="mt-1 text-xl font-semibold text-slate-100">
          {response.paths_found} paths to {response.critical_assets_found}{" "}
          critical assets
        </h2>
      </div>

      <div className="mt-5 space-y-4">
        {response.results.map((result, index) => (
          <article
            key={`${result.asset_id}-${index}`}
            className="rounded-lg border border-slate-800 bg-slate-950/60 p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold text-slate-100">
                  {result.asset_label}
                </h3>
                <p className="mt-1 text-xs uppercase text-slate-500">
                  {result.asset_type.replace("_", " ")} - {result.hops} hops
                </p>
              </div>
              <span
                className={`rounded-md border px-2 py-1 text-xs font-semibold uppercase ${riskClasses[result.risk_level]}`}
              >
                {result.risk_level} - {result.risk_score}
              </span>
            </div>

            <p className="mt-3 text-sm text-slate-300">
              {result.path_labels.join(" -> ")}
            </p>
            <p className="mt-3 text-sm text-slate-400">{result.reason}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
