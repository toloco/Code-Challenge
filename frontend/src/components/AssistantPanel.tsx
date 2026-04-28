import { useRef } from 'react'
import { CopilotChat } from '@copilotkit/react-ui'
import VoiceInputControl from './VoiceInputControl'

type AssistantPanelProps = {
  /** True once POST /upload returns a thread (CopilotKit is mounted). */
  sessionActive: boolean
  isReady: boolean
}

function AssistantPanel({ sessionActive, isReady }: AssistantPanelProps) {
  const chatShellRef = useRef<HTMLDivElement>(null)

  function setNativeInputValue(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
    const prototype = Object.getPrototypeOf(element)
    const descriptor = Object.getOwnPropertyDescriptor(prototype, 'value')
    descriptor?.set?.call(element, value)
    element.dispatchEvent(new Event('input', { bubbles: true }))
    element.dispatchEvent(new Event('change', { bubbles: true }))
  }

  function insertTranscriptIntoComposer(transcript: string) {
    const root = chatShellRef.current
    const scope = root ?? document.body

    const textarea = scope.querySelector('textarea')
    if (textarea instanceof HTMLTextAreaElement) {
      const nextValue = textarea.value ? `${textarea.value} ${transcript}` : transcript
      textarea.focus()
      setNativeInputValue(textarea, nextValue)
      return true
    }

    const input = scope.querySelector('input[type="text"]')
    if (input instanceof HTMLInputElement) {
      const nextValue = input.value ? `${input.value} ${transcript}` : transcript
      input.focus()
      setNativeInputValue(input, nextValue)
      return true
    }

    const editable = scope.querySelector('[contenteditable="true"]')
    if (editable instanceof HTMLElement) {
      const nextValue = editable.textContent ? `${editable.textContent} ${transcript}` : transcript
      editable.focus()
      editable.textContent = nextValue
      editable.dispatchEvent(new InputEvent('input', { bubbles: true, data: transcript }))
      return true
    }

    return false
  }

  return (
    <section className="panel">
      <h2>Cooking Assistant</h2>
      <p>
        Ask the assistant to scale servings, suggest substitutions, or guide you through the next
        step.
      </p>

      {!sessionActive || !isReady ? (
        <div className="assistant-disabled-shell" aria-disabled="true">
          <p className="assistant-disabled-note">Upload a recipe to start chatting.</p>
        </div>
      ) : (
        <>
          <div className="assistant-chat-shell" ref={chatShellRef}>
            <CopilotChat className="assistant-chat" />
          </div>
          <VoiceInputControl onTranscript={insertTranscriptIntoComposer} />
        </>
      )}
    </section>
  )
}

export default AssistantPanel
