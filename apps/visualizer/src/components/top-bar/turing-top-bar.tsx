import { useMemo } from 'react'

import { useAppStore, useBreachPathStore } from '@/stores'
import useGraphInfo from '@/hooks/use-graph-info'

export const TuringTopBar = () => {
  const page = useAppStore((state) => state.page)
  const graphName = useAppStore((state) => state.graphName)
  const storageStatusLabel = useBreachPathStore((state) => state.storageStatusLabel)
  const savedNetworkName = useBreachPathStore((state) => state.savedNetworkName)
  const savedNetworkVersion = useBreachPathStore((state) => state.savedNetworkVersion)
  const hasUnsavedChanges = useBreachPathStore((state) => state.hasUnsavedChanges)
  const graph = useGraphInfo(graphName)

  const rightTitle = useMemo(
    () => (graph.info ? graph.info.name : 'No graph selected'),
    [graph.info]
  )
  const leftTitle = useMemo(() => {
    switch (page) {
      case 'viewer':
        return 'BreachPath Network Exposure Simulator'
    }
  }, [page])

  return (
    <div className="border-grey-900 bg-grey-800 flex items-center space-x-4 border-t border-b p-4">
      <div className="text-content-secondary flex flex-1 items-center space-x-7 font-sans text-sm font-medium">
        <span>{leftTitle}</span>
        <span
          className={
            'border-grey-500 text-content-secondary ml-4 rounded-md border p-1 pr-2 pl-2 text-sm'
          }
        >
          {rightTitle}
        </span>
      </div>
      <div className="rounded-md border border-grey-500 px-3 py-1 text-sm text-content-secondary">
        Current network: {savedNetworkName ?? graphName ?? 'breachpath_demo'}
        {savedNetworkVersion ? ` v${savedNetworkVersion}` : ''}
        {hasUnsavedChanges ? ' (unsaved changes)' : ''}
      </div>
      <div className="rounded-md border border-grey-500 px-3 py-1 text-sm text-content-secondary">
        {storageStatusLabel}
      </div>
    </div>
  )
}
