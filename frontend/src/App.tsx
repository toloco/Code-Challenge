import { useEffect, useState } from 'react'
import { CopilotKit } from '@copilotkit/react-core'
import { HttpAgent } from '@ag-ui/client'
import './App.css'
import AppHeader from './components/AppHeader'
import AssistantPanel from './components/AssistantPanel'
import RecipePanel, { type Recipe } from './components/RecipePanel'
import UploadPanel from './components/UploadPanel'

type UploadSession = {
  threadId: string
  runId: string
  state: Record<string, unknown>
}

const SESSION_STORAGE_KEY = 'recipe-companion:last-session'
const DEV_MOCK_SESSION: UploadSession = {
  threadId: 'dev-thread-local',
  runId: 'dev-run-local',
  state: {
    document_text: 'Mock recipe session seeded locally for offline frontend testing.',
    recipe: {
      title: 'Quick Tomato Pasta (Mock)',
      prep_time_minutes: 10,
      cook_time_minutes: 15,
      servings: 2,
      difficulty: 'easy',
      ingredients: [
        { name: 'spaghetti', quantity: 200, unit: 'g', preparation: null },
        { name: 'olive oil', quantity: 2, unit: 'tbsp', preparation: null },
        { name: 'garlic', quantity: 2, unit: 'cloves', preparation: 'minced' },
        { name: 'chopped tomatoes', quantity: 400, unit: 'g', preparation: null },
        { name: 'basil', quantity: 8, unit: 'leaves', preparation: 'torn' },
        { name: 'salt', quantity: null, unit: null, preparation: 'to taste' },
      ],
      steps: [
        { step_number: 1, instruction: 'Boil salted water and cook spaghetti until al dente.' },
        { step_number: 2, instruction: 'Saute garlic in olive oil for 30 seconds.' },
        { step_number: 3, instruction: 'Add tomatoes, simmer for 8 minutes, then season.' },
        { step_number: 4, instruction: 'Toss pasta with sauce, finish with basil, and serve.' },
      ],
    },
    current_step: 0,
    scaled_servings: null,
    checked_ingredients: [],
    cooking_started: false,
  },
}
// TEMP DEV ONLY (remove when model quota is available again):
// 1) Remove `SESSION_STORAGE_KEY` and `DEV_MOCK_SESSION`.
// 2) Remove the localStorage hydrate/save useEffects.
// 3) Keep only the real /upload -> setSession flow in `onUploadSuccess`.
// 4) If needed, clear old browser state with:
//    localStorage.removeItem('recipe-companion:last-session')

const recipeAgent = new HttpAgent({
  url: 'http://localhost:8000/copilotkit/',
})

function App() {
  const [session, setSession] = useState<UploadSession | null>(null)

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(SESSION_STORAGE_KEY)
      if (!raw) {
        // Seed local storage in dev so frontend/chat flow can be tested
        // without consuming model quota via /upload.
        if (import.meta.env.DEV) {
          window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(DEV_MOCK_SESSION))
          setSession(DEV_MOCK_SESSION)
        }
        return
      }

      const parsed = JSON.parse(raw) as Partial<UploadSession>
      if (
        typeof parsed?.threadId === 'string' &&
        typeof parsed?.runId === 'string' &&
        parsed?.state &&
        typeof parsed.state === 'object'
      ) {
        setSession({
          threadId: parsed.threadId,
          runId: parsed.runId,
          state: parsed.state as Record<string, unknown>,
        })
      }
    } catch {
      // Ignore malformed stored data and continue with a fresh session.
    }
  }, [])

  useEffect(() => {
    if (!session) return
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
  }, [session])

  const recipe = (session?.state?.recipe as Recipe | undefined) ?? null
  const threadId = session?.threadId ?? null
  const isReady = Boolean(recipe && threadId)

  const shell = (
    <main className="app-shell">
      <AppHeader />
      <div className="layout-grid">
        <RecipePanel recipe={recipe} />
        <aside className="side-column" aria-label="Secondary panels">
          <UploadPanel
            onUploadSuccess={(data) => {
              const nextSession = {
                threadId: String(data.threadId ?? ''),
                runId: String(data.runId ?? ''),
                state: (data.state ?? {}) as Record<string, unknown>,
              }
              setSession(nextSession)
            }}
          />
          <AssistantPanel
            sessionActive={Boolean(threadId)}
            isReady={isReady}
            initialRecipeContext={session?.state}
          />
        </aside>
      </div>
    </main>
  )

  // CopilotKit contacts /copilotkit/ as soon as it mounts. Without a threadId from
  // POST /upload, those requests are invalid and the server returns 422, so we
  // wait until we have a thread before wrapping the app in the provider.
  if (!threadId) {
    return shell
  }

  return (
    <CopilotKit
      runtimeUrl="/copilotkit/"
      useSingleEndpoint
      agents__unsafe_dev_only={{ recipe_agent: recipeAgent }}
      agent="recipe_agent"
      threadId={threadId}
      showDevConsole={false}
    >
      {shell}
    </CopilotKit>
  )
}

export default App
