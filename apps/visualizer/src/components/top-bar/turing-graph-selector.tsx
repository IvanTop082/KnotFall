import { listAvailableGraphs } from '@/api'
import { type FC, useCallback, useEffect, useMemo, useState } from 'react'
import { TuringSelect } from '../base/turing-select'
import type { TuringSelectItem } from '../base/turing-select-item'

import useGraphInfo from '@/hooks/use-graph-info'
import { useSelectedChips } from '../turing-bar/use-selected-chips'
import {
  useAppStore,
  useBreachPathBuilderStore,
  useBreachPathStore,
  useCanvasStore,
  useVisStore,
} from '@/stores'
import type { CanvasStore } from '@turingcanvas'

const HIDDEN_NON_CYBER_GRAPHS = new Set([
  'supply_chain',
  'logistics_risk',
  'drone_swarm',
  'power_plants',
  'poledb',
  'attack_scenarios',
])

export const TuringGraphSelector: FC = () => {
  const entityCache = useVisStore((state) => state.entityCache)
  const neighbourhood = useVisStore((state) => state.neighbourhood)
  const hiddenNodes = useVisStore((state) => state.hiddenNodes)

  const graphName = useAppStore((state) => state.graphName)
  const setGraphName = useAppStore((state) => state.setGraphName)
  const setLocalBuilderMode = useBreachPathBuilderStore((state) => state.setLocalBuilderMode)
  const clearBreachPathAnalysis = useBreachPathStore((state) => state.clearAnalysis)
  const turingActions = useCanvasStore((state: CanvasStore) => state.actions)
  const { refetch } = useGraphInfo(graphName)

  const [graphs, setGraphs] = useState<string[]>([])

  const availGraphs = useMemo(
    () =>
      graphs
        .filter((graph) => !HIDDEN_NON_CYBER_GRAPHS.has(graph))
        .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))
        .map((graph) => ({ name: graph })),
    [graphs]
  )

  const unselectAllChips = useSelectedChips((state) => state.unselectAllChips)
  const onItemSelect = useCallback(
    (graph: TuringSelectItem) => {
      neighbourhood.reset(graph.name)
      hiddenNodes.clear()
      entityCache.edges.clear()
      entityCache.nodes.clear()
      setLocalBuilderMode(false)
      clearBreachPathAnalysis()
      unselectAllChips()

      turingActions.reset()
      setGraphName(graph.name)
      refetch()
    },
    [
      refetch,
      setGraphName,
      turingActions,
      hiddenNodes,
      neighbourhood,
      entityCache,
      setLocalBuilderMode,
      clearBreachPathAnalysis,
      unselectAllChips,
    ]
  )

  useEffect(() => {
    listAvailableGraphs({})
      .then((data) => {
        setGraphs(data)
      })
      .catch((err) => console.log(err))
  }, [])

  return (
    <TuringSelect items={availGraphs} onItemSelect={onItemSelect}>
      {graphName !== undefined ? graphName : 'Graph'}
    </TuringSelect>
  )
}
