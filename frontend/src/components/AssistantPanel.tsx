import { useCoAgent } from '@copilotkit/react-core'
import { CopilotChat } from '@copilotkit/react-ui'

type AssistantPanelProps = {
  /** True once POST /upload returns a thread (CopilotKit is mounted). */
  sessionActive: boolean
  isReady: boolean
  initialRecipeContext?: Record<string, unknown>
}

function AssistantPanelSession({
  isReady,
  initialRecipeContext,
}: Pick<AssistantPanelProps, 'isReady' | 'initialRecipeContext'>) {
  useCoAgent({
    name: 'recipe_agent',
    initialState: initialRecipeContext ?? {},
  })

  return (
    <>
      {!isReady ? (
        <p className="assistant-disabled-note">
          Upload a recipe first to start a chat in the same recipe session.
        </p>
      ) : (
        <div className="assistant-chat-shell">
          <CopilotChat className="assistant-chat" />
        </div>
      )}
    </>
  )
}

function AssistantPanel({ sessionActive, isReady, initialRecipeContext }: AssistantPanelProps) {
  return (
    <section className="panel">
      <h2>Cooking Assistant</h2>
      <p>
        Ask the assistant to scale servings, suggest substitutions, or guide you through the next
        step.
      </p>

      {sessionActive ? (
        <AssistantPanelSession isReady={isReady} initialRecipeContext={initialRecipeContext} />
      ) : (
        <p className="assistant-disabled-note">
          Upload a recipe first to start a chat in the same recipe session.
        </p>
      )}
    </section>
  )
}

export default AssistantPanel
