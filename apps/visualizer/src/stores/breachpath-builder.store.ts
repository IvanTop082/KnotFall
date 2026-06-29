import { create } from 'zustand'

export type BreachPathToolPanel = 'builder' | 'analysis' | 'save' | 'history' | 'examples'

export type BreachPathBuilderStore = {
  builderDrawerOpen: boolean
  activePanel: BreachPathToolPanel
  nodeCreatorOpen: boolean
  localBuilderMode: boolean
  statusMessage: string | undefined
  libraryRefreshToken: number
  setBuilderDrawerOpen: (open: boolean) => void
  setActivePanel: (panel: BreachPathToolPanel) => void
  setNodeCreatorOpen: (open: boolean) => void
  setLocalBuilderMode: (enabled: boolean) => void
  setStatusMessage: (message: string | undefined) => void
  requestLibraryRefresh: () => void
}

export const useBreachPathBuilderStore = create<BreachPathBuilderStore>((set) => ({
  builderDrawerOpen: false,
  activePanel: 'builder',
  nodeCreatorOpen: false,
  localBuilderMode: false,
  statusMessage: undefined,
  libraryRefreshToken: 0,
  setBuilderDrawerOpen: (open) => set({ builderDrawerOpen: open }),
  setActivePanel: (panel) => set({ activePanel: panel, builderDrawerOpen: true }),
  setNodeCreatorOpen: (open) => set({ nodeCreatorOpen: open }),
  setLocalBuilderMode: (enabled) => set({ localBuilderMode: enabled }),
  setStatusMessage: (message) => set({ statusMessage: message }),
  requestLibraryRefresh: () =>
    set((state) => ({ libraryRefreshToken: state.libraryRefreshToken + 1 })),
}))

export default useBreachPathBuilderStore
