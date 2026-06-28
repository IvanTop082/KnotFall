import { getBreachPathApiBaseUrl, type BreachPathSimulationType } from '@/api/breachpath'
import { buildGraphPayload, graphFingerprint } from '@/breachpath/graph-utils'
import { useBreachPathBuilderStore, useBreachPathStore, useCanvasStore } from '@/stores'
import { Icon, Spinner } from '@blueprintjs/core'
import { useMemo } from 'react'

function formatRiskLevel(level: string | undefined) {
  if (!level) return 'none'
  return level.charAt(0).toUpperCase() + level.slice(1)
}

export function BreachPathAnalysisPanel() {
  const selectedNode = useBreachPathStore((state) => state.selectedNode)
  const analysis = useBreachPathStore((state) => state.analysis)
  const status = useBreachPathStore((state) => state.status)
  const error = useBreachPathStore((state) => state.error)
  const currentGraphHash = useBreachPathStore((state) => state.currentGraphHash)
  const lastAnalysisGraphHash = useBreachPathStore((state) => state.lastAnalysisGraphHash)
  const currentGraphVersion = useBreachPathStore((state) => state.currentGraphVersion)
  const lastAnalysisGraphVersion = useBreachPathStore((state) => state.lastAnalysisGraphVersion)
  const savedNetworkId = useBreachPathStore((state) => state.savedNetworkId)
  const savedNetworkName = useBreachPathStore((state) => state.savedNetworkName)
  const savedNetworkVersion = useBreachPathStore((state) => state.savedNetworkVersion)
  const hasUnsavedChanges = useBreachPathStore((state) => state.hasUnsavedChanges)
  const previewVersion = useBreachPathStore((state) => state.previewVersion)
  const simulationType = useBreachPathStore((state) => state.simulationType)
  const setSimulationType = useBreachPathStore((state) => state.setSimulationType)
  const builderDrawerOpen = useBreachPathBuilderStore((state) => state.builderDrawerOpen)
  const activePanel = useBreachPathBuilderStore((state) => state.activePanel)
  const setBuilderDrawerOpen = useBreachPathBuilderStore((state) => state.setBuilderDrawerOpen)
  const setActivePanel = useBreachPathBuilderStore((state) => state.setActivePanel)
  const lastAnalysisSimulationType = useBreachPathStore(
    (state) => state.lastAnalysisSimulationType
  )
  const animateExposurePaths = useBreachPathStore((state) => state.animateExposurePaths)
  const setAnimateExposurePaths = useBreachPathStore(
    (state) => state.setAnimateExposurePaths
  )
  const runAnalysisForSelectedNode = useBreachPathStore(
    (state) => state.runAnalysisForSelectedNode
  )
  const canvasNodes = useCanvasStore((state) => state.nodes())
  const canvasEdges = useCanvasStore((state) => state.edges())
  const isAnalysisOutdated =
    lastAnalysisGraphHash !== undefined && currentGraphHash !== lastAnalysisGraphHash
  const analysisFreshnessLabel =
    lastAnalysisGraphHash === undefined
      ? 'Not analysed'
      : isAnalysisOutdated
        ? 'Outdated'
        : 'Up to date'
  const currentGraph = useMemo(
    () => buildGraphPayload(canvasNodes, canvasEdges),
    [canvasNodes, canvasEdges]
  )
  const currentGraphFingerprint = useMemo(() => graphFingerprint(currentGraph), [currentGraph])

  const runSelectedAnalysis = () => {
    runAnalysisForSelectedNode(currentGraph, currentGraphFingerprint, simulationType, {
      networkId: savedNetworkId,
      version: previewVersion ?? savedNetworkVersion,
      graphHash: currentGraphFingerprint,
    })
  }

  const rerunAnalysis = () => {
    runAnalysisForSelectedNode(
      currentGraph,
      currentGraphFingerprint,
      lastAnalysisSimulationType ?? analysis?.simulation_type,
      {
        networkId: savedNetworkId,
        version: previewVersion ?? savedNetworkVersion,
        graphHash: currentGraphFingerprint,
      }
    )
  }

  const highestRiskPath = useMemo(() => {
    if (!analysis?.paths.length) return undefined
    return [...analysis.paths].sort((a, b) => b.risk_score - a.risk_score)[0]
  }, [analysis])

  const criticalSystems = useMemo(() => {
    if (!analysis) return []
    return [...new Set(analysis.paths.map((path) => path.target))]
  }, [analysis])

  const relationshipTypesFollowed = useMemo(() => {
    if (!analysis) return []
    return [
      ...new Set(
        analysis.highlighted_edges
          .map((edge) => edge.relationship)
          .filter((relationship): relationship is string => Boolean(relationship))
      ),
    ]
  }, [analysis])

  const affectedDeviceIds = useMemo(() => {
    if (!analysis) return []
    return analysis.highlighted_nodes.filter((nodeId) => nodeId !== analysis.compromised_node.id)
  }, [analysis])

  const fallbackRecommendations = [
    'No high/critical devices were reached, but connected devices may still be exposed.',
    'Mark important devices as high/critical to improve analysis.',
    'Consider separating low-trust devices such as printers, smart TVs, and IoT devices.',
  ]

  if (!builderDrawerOpen || activePanel !== 'analysis') return null

  return (
    <aside className="shadow-dark pointer-events-auto absolute right-4 top-20 z-20 flex max-h-[calc(100vh-7rem)] w-[390px] flex-col overflow-hidden rounded border border-grey-600 bg-grey-800/95 backdrop-blur">
      <header className="shrink-0 border-b border-grey-600 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-content-primary">
              <Icon icon="path-search" />
              <h2 className="text-sm font-semibold">Analyse Exposure</h2>
            </div>
            <p className="mt-1 text-xs text-content-secondary">
              Selected-node defensive analysis and risk recommendations.
            </p>
          </div>
          <button
            className="rounded px-2 py-1 text-content-secondary hover:bg-grey-700 hover:text-content-primary"
            type="button"
            aria-label="Close analysis panel"
            onClick={() => setBuilderDrawerOpen(false)}
          >
            ×
          </button>
        </div>
        <p className="mt-1 text-xs text-content-secondary">
          FastAPI brain: {getBreachPathApiBaseUrl()}
        </p>
      </header>

      <div className="app-scrollbar flex flex-1 flex-col gap-4 overflow-y-auto p-4">
        <section className="rounded border border-grey-600 bg-grey-900/70 p-3 text-xs text-content-secondary">
          <label className="block text-xs text-content-secondary">Simulation type</label>
          <select
            className="app-input mt-1 w-full"
            value={simulationType}
            onChange={(event) => setSimulationType(event.target.value as BreachPathSimulationType)}
          >
            <option value="compromise">Compromise</option>
            <option value="offline">Offline / destroyed</option>
            <option value="spyware">Spyware</option>
            <option value="data_leak">Data leak</option>
            <option value="lateral_movement">Lateral movement</option>
          </select>
          <button
            className="app-button mt-2 w-full"
            type="button"
            disabled={status === 'loading'}
            onClick={runSelectedAnalysis}
          >
            {status === 'loading' ? 'Analysing...' : 'Analyse selected node'}
          </button>
          {!selectedNode && (
            <p className="mt-2 rounded border border-yellow-700/60 bg-yellow-950/30 p-2 text-yellow-100">
              Select a device on the canvas first.
            </p>
          )}
        </section>

        <section className="rounded border border-grey-600 bg-grey-900/70 p-3 text-xs text-content-secondary">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <p>Local version</p>
              <strong className="text-content-primary">v{currentGraphVersion}</strong>
            </div>
            <div>
              <p>Last analysed</p>
              <strong className="text-content-primary">
                {lastAnalysisGraphVersion ? `v${lastAnalysisGraphVersion}` : 'Not analysed'}
              </strong>
            </div>
          </div>
          <p className="mt-2 text-xs">
            Network:{' '}
            <strong className="text-content-primary">
              {savedNetworkName ?? analysis?.network_id ?? 'Unsaved network'}
            </strong>
            <br />
            Saved version:{' '}
            <strong className="text-content-primary">
              {previewVersion
                ? `preview v${previewVersion}`
                : savedNetworkVersion
                  ? `v${savedNetworkVersion}`
                  : 'Not saved'}
            </strong>
          </p>
          <p
            className={`mt-2 rounded px-2 py-1 ${
              lastAnalysisGraphHash === undefined
                ? 'bg-grey-800 text-content-secondary'
                : isAnalysisOutdated
                  ? 'bg-yellow-950/40 text-yellow-100'
                  : 'bg-emerald-950/30 text-emerald-100'
            }`}
          >
            {analysisFreshnessLabel}
          </p>
          {isAnalysisOutdated && (
            <div className="mt-2 rounded border border-yellow-700/60 bg-yellow-950/30 p-2 text-yellow-100">
              <p>
                {lastAnalysisGraphVersion
                  ? `This analysis was run on v${lastAnalysisGraphVersion}, but the current graph has unsaved changes.`
                  : 'Network changed. Previous exposure analysis may be outdated.'}
              </p>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <button
                  className="app-button"
                  type="button"
                  onClick={() => setActivePanel('save')}
                >
                  Save new version
                </button>
                <button className="app-button" type="button" onClick={rerunAnalysis}>
                  Re-run analysis
                </button>
              </div>
            </div>
          )}
          {hasUnsavedChanges && !isAnalysisOutdated && (
            <p className="mt-2 rounded border border-yellow-700/60 bg-yellow-950/30 p-2 text-yellow-100">
              Unsaved changes are present. Save a new version when this graph state matters.
            </p>
          )}
          <label className="mt-3 flex items-center gap-2 text-xs text-content-secondary">
            <input
              type="checkbox"
              checked={animateExposurePaths}
              onChange={(event) => setAnimateExposurePaths(event.target.checked)}
            />
            Animate exposure paths
          </label>
        </section>

        {!selectedNode && status !== 'error' && (
          <div className="flex flex-1 items-center justify-center text-center text-sm text-content-secondary">
            Select a device on the canvas, then run analysis.
          </div>
        )}

        {selectedNode && status === 'idle' && (
          <div className="rounded border border-grey-600 bg-grey-900/70 p-3 text-sm text-content-secondary">
            <p className="font-medium text-content-primary">Selected: {selectedNode.label}</p>
            {selectedNode.nodeType && (
              <p className="mt-1 text-xs text-content-secondary">Type: {selectedNode.nodeType}</p>
            )}
            <p className="mt-1">
              Use Analyse selected or the BreachPath builder panel to run analysis against the
              current graph.
            </p>
          </div>
        )}

        {selectedNode && status === 'loading' && (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center text-sm text-content-secondary">
            <Spinner size={28} />
            <span>Running defensive exposure simulation...</span>
          </div>
        )}

        {status === 'error' && (
          <div className="rounded border border-red-700 bg-red-950/30 p-3 text-sm">
            <div className="flex items-center gap-2 text-red-200">
              <Icon icon="error" />
              <span className="font-medium">
                {error === 'Select a device on the canvas first.'
                  ? 'Select a device on the canvas first.'
                  : 'Analysis failed. Check that the backend is running at http://localhost:8000.'}
              </span>
            </div>
            {error && error !== 'Select a device on the canvas first.' && (
              <p className="mt-2 text-xs text-red-100/80">{error}</p>
            )}
          </div>
        )}

        {selectedNode && analysis && status === 'ready' && (
          <>
            <section className="rounded border border-grey-600 bg-grey-900/70 p-3">
              <p className="text-xs font-medium text-content-secondary">Selected device</p>
              <h3 className="mt-1 text-base font-semibold text-content-primary">
                {analysis.compromised_node.label || selectedNode.label}
              </h3>
              <p className="mt-1 text-xs text-content-secondary">
                {analysis.compromised_node.id}
                {analysis.compromised_node.type && ` - ${analysis.compromised_node.type}`}
              </p>
              <p className="mt-2 rounded border border-violet-700/60 bg-violet-950/30 p-2 text-xs text-violet-100">
                Analysed network: {savedNetworkName ?? analysis.network_id ?? 'Unsaved network'}
                <br />
                Simulation: {analysis.simulation_type.replace(/_/g, ' ')}
                {analysis.version && (
                  <>
                    <br />
                    Analysed version: v{analysis.version}
                  </>
                )}
                {analysis.analysed_at && (
                  <>
                    <br />
                    Analysed at: {new Date(analysis.analysed_at).toLocaleString()}
                  </>
                )}
              </p>
              {selectedNode.mappingNote && (
                <p className="mt-2 rounded border border-yellow-700/70 bg-yellow-950/30 p-2 text-xs text-yellow-100">
                  {selectedNode.mappingNote}
                </p>
              )}
            </section>

            <section className="grid grid-cols-2 gap-2">
              <div className="rounded border border-orange-600/70 bg-orange-950/30 p-3">
                <p className="text-xs text-orange-100/80">Risk score</p>
                <strong className="mt-1 block text-2xl leading-none text-orange-100">
                  {analysis.summary.highest_risk_score}
                </strong>
                <span className="mt-1 block text-xs text-orange-100/80">
                  {formatRiskLevel(analysis.summary.risk_level)}
                </span>
              </div>
              <div className="rounded border border-cyan-600/70 bg-cyan-950/30 p-3">
                <p className="text-xs text-cyan-100/80">Critical systems</p>
                <strong className="mt-1 block text-2xl leading-none text-cyan-100">
                  {analysis.summary.critical_assets_reachable}
                </strong>
                <span className="mt-1 block text-xs text-cyan-100/80">reachable</span>
              </div>
            </section>

            <section className="grid grid-cols-2 gap-2 text-sm">
              <div className="rounded border border-grey-600 bg-grey-900/70 p-3">
                <span className="text-lg font-semibold text-content-primary">
                  {analysis.summary.affected_node_count}
                </span>
                <p className="text-xs text-content-secondary">affected nodes</p>
              </div>
              <div className="rounded border border-grey-600 bg-grey-900/70 p-3">
                <span className="text-lg font-semibold text-content-primary">
                  {analysis.summary.affected_edge_count}
                </span>
                <p className="text-xs text-content-secondary">affected edges</p>
              </div>
            </section>

            <section>
              <h3 className="text-sm font-semibold text-content-primary">
                Why these devices are affected
              </h3>
              <p className="mt-2 text-xs leading-5 text-content-secondary">
                {analysis.explanation ||
                  'BreachPath follows typed relationships from the selected device through the current graph.'}
              </p>
              {affectedDeviceIds.length ? (
                <ul className="mt-2 grid grid-cols-1 gap-1 text-sm text-content-secondary">
                  {affectedDeviceIds.map((nodeId) => (
                    <li key={nodeId} className="rounded bg-grey-900/70 px-2 py-1">
                      {nodeId}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-content-secondary">
                  No other connected devices were reached from this node.
                </p>
              )}
            </section>

            <section>
              <h3 className="text-sm font-semibold text-content-primary">
                What relationship types were followed
              </h3>
              {relationshipTypesFollowed.length ? (
                <div className="mt-2 flex flex-wrap gap-1">
                  {relationshipTypesFollowed.map((relationship) => (
                    <span
                      key={relationship}
                      className="rounded border border-grey-600 bg-grey-900/70 px-2 py-1 text-xs text-content-secondary"
                    >
                      {relationship}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-content-secondary">
                  No typed relationships were followed from this device.
                </p>
              )}
              <p className="mt-2 text-xs leading-5 text-content-secondary">
                Home-style relationships such as same_network, can_access, and routes_through
                can spread risk both ways. Admin, credential, control, backup, monitoring, and
                dependency relationships remain directional.
              </p>
            </section>

            <section>
              <h3 className="text-sm font-semibold text-content-primary">
                Critical devices reached
              </h3>
              {criticalSystems.length ? (
                <ul className="mt-2 space-y-1 text-sm text-content-secondary">
                  {criticalSystems.map((system) => (
                    <li key={system} className="rounded bg-grey-900/70 px-2 py-1">
                      {system}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="mt-2 rounded border border-yellow-700/60 bg-yellow-950/30 p-3 text-sm text-yellow-100">
                  <p>
                    No critical devices were reached. This may be because no connected devices are
                    marked as high/critical.
                  </p>
                  <p className="mt-2 text-xs">
                    Tip: mark important devices such as router, NAS, admin account, work laptop, or
                    security camera as high/critical to make the analysis more useful.
                  </p>
                </div>
              )}
            </section>

            <section>
              <h3 className="text-sm font-semibold text-content-primary">Exposure paths</h3>
              {analysis.paths.length ? (
                <div className="mt-2 space-y-2">
                  {analysis.paths.map((path) => (
                    <article
                      key={`${path.target}-${path.nodes.join('-')}`}
                      className="rounded border border-grey-600 bg-grey-900/70 p-2"
                    >
                      <div className="flex items-center justify-between gap-2 text-xs">
                        <strong className="text-content-primary">{path.target}</strong>
                        <span className="text-orange-100">
                          {path.risk_level} / {path.risk_score}
                        </span>
                      </div>
                      <p className="mt-2 text-xs leading-5 text-content-secondary">
                        {path.nodes.join(' -> ')}
                      </p>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-content-secondary">
                  No exposure path to a high/critical device was found.
                </p>
              )}
            </section>

            {highestRiskPath && (
              <section>
                <h3 className="text-sm font-semibold text-content-primary">
                  Plain-English explanation
                </h3>
                <p className="mt-2 rounded border border-grey-600 bg-grey-900/70 p-2 text-xs leading-5 text-content-primary">
                  {highestRiskPath.nodes.join(' -> ')}
                </p>
                <p className="mt-2 text-xs leading-5 text-content-secondary">
                  {highestRiskPath.explanation}
                </p>
              </section>
            )}

            <section>
              <h3 className="text-sm font-semibold text-content-primary">Recommendations</h3>
              {analysis.recommendations.length ? (
                <div className="mt-2 space-y-2">
                  {analysis.recommendations.map((recommendation) => (
                    <article
                      key={`${recommendation.title}-${recommendation.type}`}
                      className="rounded border border-grey-600 bg-grey-900/70 p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <strong className="text-sm text-content-primary">
                          {recommendation.title}
                        </strong>
                        <span className="rounded bg-grey-700 px-2 py-0.5 text-xs text-content-secondary">
                          {recommendation.priority}
                        </span>
                      </div>
                      <p className="mt-2 text-xs leading-5 text-content-secondary">
                        {recommendation.explanation}
                      </p>
                      <p className="mt-2 text-xs text-emerald-200">
                        Estimated risk reduction: {recommendation.estimated_risk_reduction}
                      </p>
                    </article>
                  ))}
                </div>
              ) : (
                <ul className="mt-2 space-y-1 text-sm text-content-secondary">
                  {fallbackRecommendations.map((recommendation) => (
                    <li key={recommendation} className="rounded bg-grey-900/70 px-2 py-1">
                      {recommendation}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded border border-grey-600 bg-grey-900/70 p-3">
              <h3 className="text-sm font-semibold text-content-primary">
                Before/after response simulation
              </h3>
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-content-secondary">
                <div className="rounded bg-grey-800 p-2">
                  <p>Before risk</p>
                  <strong className="text-content-primary">{analysis.risk_score}</strong>
                </div>
                <div className="rounded bg-grey-800 p-2">
                  <p>After risk</p>
                  <strong className="text-content-primary">--</strong>
                </div>
                <div className="rounded bg-grey-800 p-2">
                  <p>Risk reduction</p>
                  <strong className="text-content-primary">--</strong>
                </div>
              </div>
              <p className="mt-2 text-xs text-content-secondary">
                Mitigation comparison coming next.
              </p>
            </section>

            <p className="rounded border border-grey-600 bg-grey-900/70 p-3 text-xs leading-5 text-content-secondary">
              This is a defensive exposure simulation. It does not perform exploitation,
              scanning, or payload execution.
            </p>
          </>
        )}
      </div>
    </aside>
  )
}

export default BreachPathAnalysisPanel
