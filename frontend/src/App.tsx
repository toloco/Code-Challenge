import { useState } from 'react'
import './App.css'
import AppHeader from './components/AppHeader'
import AssistantPanel from './components/AssistantPanel'
import RecipePanel from './components/RecipePanel'
import UploadPanel from './components/UploadPanel'

function App() {
  const [recipe, setRecipe] = useState<any>(null)

  return (
    <main className="app-shell">
      <AppHeader />
      <div className="layout-grid">
        <RecipePanel recipe={recipe} />
        <aside className="side-column" aria-label="Secondary panels">
          <UploadPanel onUploadSuccess={(data) => setRecipe(data?.state?.recipe ?? null)} />
          <AssistantPanel />
        </aside>
      </div>
    </main>
  )
}

export default App
