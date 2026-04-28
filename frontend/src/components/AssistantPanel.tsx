import { CopilotChat } from '@copilotkit/react-ui'

type AssistantPanelProps = {
  /** True once POST /upload returns a thread (CopilotKit is mounted). */
  sessionActive: boolean
  isReady: boolean
}

function AssistantPanel({ sessionActive, isReady }: AssistantPanelProps) {
  return (
    <section className="panel">
      <h2>Cooking Assistant</h2>
      <p>
        Ask the assistant to scale servings, suggest substitutions, or guide you through the next
        step.
      </p>

      {!sessionActive || !isReady ? (
        <p className="assistant-disabled-note">
          Upload a recipe first to start a chat in the same recipe session.
        </p>
      ) : (
        <div className="assistant-chat-shell">
          <CopilotChat className="assistant-chat" />
        </div>
      )}
    </section>
  )
}

export default AssistantPanel
