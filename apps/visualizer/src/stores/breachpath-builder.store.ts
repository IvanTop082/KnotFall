import { create } from 'zustand'

export type BreachPathBuilderStore = {
  builderDrawerOpen: boolean
  nodeCreatorOpen: boolean
  localBuilderMode: boolean
  statusMessage: string | undefined
  setBuilderDrawerOpen: (open: boolean) => void
  setNodeCreatorOpen: (open: boolean) => void
  setLocalBuilderMode: (enabled: boolean) => void
  setStatusMessage: (message: string | undefined) => void
}

export const useBreachPathBuilderStore = create<BreachPathBuilderStore>((set) => ({
  builderDrawerOpen: false,
  nodeCreatorOpen: false,
  localBuilderMode: false,
  statusMessage: undefined,
  setBuilderDrawerOpen: (open) => set({ builderDrawerOpen: open }),
  setNodeCreatorOpen: (open) => set({ nodeCreatorOpen: open }),
  setLocalBuilderMode: (enabled) => set({ localBuilderMode: enabled }),
  setStatusMessage: (message) => set({ statusMessage: message }),
}))

export default useBreachPathBuilderStore
