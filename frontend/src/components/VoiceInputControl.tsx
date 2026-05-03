import { useVoiceInput } from '../hooks/useVoiceInput'

type VoiceInputControlProps = {
  onTranscript: (transcript: string) => boolean
}

function VoiceInputControl({ onTranscript }: VoiceInputControlProps) {
  const {
    isListening,
    voiceError,
    lastTranscript,
    voiceSupported,
    startVoiceInput,
    stopVoiceInput,
  } = useVoiceInput({ onTranscript })

  return (
    <div className="assistant-chat-tools">
      <button
        type="button"
        className={`voice-button${isListening ? ' is-listening' : ''}`}
        onClick={isListening ? stopVoiceInput : startVoiceInput}
        disabled={!voiceSupported}
        aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
      >
        <svg className="voice-button-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 3a3 3 0 0 1 3 3v6a3 3 0 1 1-6 0V6a3 3 0 0 1 3-3Z"
            fill="currentColor"
          />
          <path
            d="M6.5 11.5a.75.75 0 0 1 .75.75 4.75 4.75 0 0 0 9.5 0 .75.75 0 0 1 1.5 0 6.25 6.25 0 0 1-5.5 6.2V21h2a.75.75 0 0 1 0 1.5h-6a.75.75 0 0 1 0-1.5h2v-2.55a6.25 6.25 0 0 1-5.5-6.2.75.75 0 0 1 .75-.75Z"
            fill="currentColor"
          />
        </svg>
        <span>{isListening ? 'Stop' : 'Voice'}</span>
      </button>
      <p className="voice-status">
        {!voiceSupported
          ? 'Voice input is not supported in this browser.'
          : isListening
            ? 'Listening... speak naturally.'
            : 'Use voice if your hands are busy, or type your message above.'}
      </p>
      {lastTranscript ? <p className="voice-status">Heard: "{lastTranscript}"</p> : null}
      {voiceError ? <p className="status-error voice-error">{voiceError}</p> : null}
    </div>
  )
}

export default VoiceInputControl
