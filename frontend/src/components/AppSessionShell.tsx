import { useCoAgent } from '@copilotkit/react-core'
import AppHeader from './AppHeader'
import AssistantPanel from './AssistantPanel'
import RecipePanel, { type RecipeContext } from './RecipePanel'
import UploadPanel from './UploadPanel'

type AppSessionShellProps = {
  threadId: string
  isReady: boolean
  initialRecipeContext: RecipeContext
  onUploadSuccess: (data: any) => void
}

function AppSessionShell({
  threadId,
  isReady,
  initialRecipeContext,
  onUploadSuccess,
}: AppSessionShellProps) {
  const { state: sharedState, setState: setSharedState } = useCoAgent<RecipeContext>({
    name: 'recipe_agent',
    initialState: initialRecipeContext,
  })

  return (
    <main className="app-shell">
      <AppHeader />
      <div className="layout-grid">
        <RecipePanel sharedState={sharedState ?? null} setSharedState={setSharedState} />
        <aside className="side-column" aria-label="Secondary panels">
          <UploadPanel onUploadSuccess={onUploadSuccess} />
          <AssistantPanel sessionActive={Boolean(threadId)} isReady={isReady} />
        </aside>
      </div>
    </main>
  )
}

export default AppSessionShell
