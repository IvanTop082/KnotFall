import TuringButton from '@/components/base/turing-button'
import TuringTooltip from '@/components/base/turing-tooltip'
import { useBreachPathBuilderStore, useVisStore } from '@/stores'
import type { FC } from 'react'

export const AddNodesMenu: FC = () => {
  const noNodeSelected = useVisStore((state) => state.neighbourhood.size) === 0
  const setLocalBuilderMode = useBreachPathBuilderStore((state) => state.setLocalBuilderMode)
  const setStatusMessage = useBreachPathBuilderStore((state) => state.setStatusMessage)

  return (
    <TuringTooltip content="Use BreachPath cyber node templates" placement="bottom">
      <TuringButton
        highlight={noNodeSelected}
        onClick={() => {
          setLocalBuilderMode(true)
          setStatusMessage('Choose a cyber node template in the BreachPath builder panel.')
        }}
      >
        Add cyber node
      </TuringButton>
    </TuringTooltip>
  )
}
