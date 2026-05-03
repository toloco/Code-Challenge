import { useState } from 'react'
import { CopilotKit } from '@copilotkit/react-core'
import './App.css'
import AppHeader from './components/AppHeader'
import AppSessionShell from './components/AppSessionShell'
import AssistantPanel from './components/AssistantPanel'
import RecipePanel, { type RecipeContext } from './components/RecipePanel'
import UploadPanel, { type UploadResponse } from './components/UploadPanel'

type UploadSession = {
  threadId: string
  state: RecipeContext
}

function App() {
  const [session, setSession] = useState<UploadSession | null>(null)

  const threadId = session?.threadId ?? null
  const recipeContext = session?.state ?? null
  const recipe = recipeContext?.recipe ?? null
  const isReady = Boolean(recipe && threadId)

  const onUploadSuccess = (data: UploadResponse) => {
    const nextSession = {
      threadId: String(data.threadId ?? ''),
      state: (data.state ?? {}) as RecipeContext,
    }
    setSession(nextSession)
  }
  // fallback while CopilotKit starts to keep UI friendly
  const shellWithoutAgent = (
    <main className="app-shell">
      <AppHeader />
      <div className="layout-grid">
        <RecipePanel sharedState={recipeContext} />
        <aside className="side-column" aria-label="Secondary panels">
          <UploadPanel onUploadSuccess={onUploadSuccess} />
          <AssistantPanel sessionActive={Boolean(threadId)} isReady={isReady} />
        </aside>
      </div>
    </main>
  )

  // CopilotKit contacts /copilotkit/ as soon as it mounts. Without a threadId from
  // POST /upload, those requests are invalid and the server returns 422, so we
  // wait until we have a thread before wrapping the app in the provider.
  if (!threadId || !recipeContext) {
    return shellWithoutAgent
  }

  return (
    <CopilotKit
      runtimeUrl="/copilotkit/"
      useSingleEndpoint
      agent="recipe_agent"
      threadId={threadId}
      showDevConsole={false}
    >
      <AppSessionShell
        threadId={threadId}
        isReady={isReady}
        initialRecipeContext={recipeContext}
        onUploadSuccess={onUploadSuccess}
      />
    </CopilotKit>
  )
}

export default App
