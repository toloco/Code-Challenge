import './App.css'
import AppHeader from './components/AppHeader'
import AssistantPanel from './components/AssistantPanel'
import RecipePanel from './components/RecipePanel'
import UploadPanel from './components/UploadPanel'

function App() {
  return (
    <main className="app-shell">
      <AppHeader />
      <div className="layout-grid">
        <RecipePanel />
        <aside className="side-column" aria-label="Secondary panels">
          <UploadPanel />
          <AssistantPanel />
        </aside>
      </div>
    </main>
  )
}

export default App
