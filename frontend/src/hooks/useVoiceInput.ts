import { useRef, useState } from 'react'

type SpeechRecognitionEvent = Event & {
  results: ArrayLike<ArrayLike<{ transcript: string }>>
}

type SpeechRecognitionLike = {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: Event & { error?: string }) => void) | null
  onend: (() => void) | null
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionCtor
    webkitSpeechRecognition?: SpeechRecognitionCtor
  }
}

type UseVoiceInputArgs = {
  onTranscript: (transcript: string) => boolean
}

export function useVoiceInput({ onTranscript }: UseVoiceInputArgs) {
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const [isListening, setIsListening] = useState(false)
  const [voiceError, setVoiceError] = useState<string | null>(null)
  const [lastTranscript, setLastTranscript] = useState('')

  const SpeechRecognition = window.SpeechRecognition ?? window.webkitSpeechRecognition
  const voiceSupported = Boolean(SpeechRecognition)

  function startVoiceInput() {
    if (!SpeechRecognition) return

    setVoiceError(null)
    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-GB'

    recognition.onresult = (event) => {
      const transcripts: string[] = []
      for (let i = 0; i < event.results.length; i += 1) {
        transcripts.push(event.results[i]?.[0]?.transcript ?? '')
      }
      const transcript = transcripts.join(' ').trim()
      if (!transcript) return

      setLastTranscript(transcript)
      const inserted = onTranscript(transcript)
      if (!inserted) {
        setVoiceError('Captured speech but could not find chat input. Please paste manually.')
      }
    }

    recognition.onerror = (event) => {
      if (event.error === 'not-allowed') {
        setVoiceError('Microphone access denied. You can still type your message.')
      } else if (event.error === 'no-speech') {
        setVoiceError('No speech detected. Try again and speak a bit louder.')
      } else {
        setVoiceError('Voice input failed. Please type your message.')
      }
    }

    recognition.onend = () => {
      setIsListening(false)
      recognitionRef.current = null
    }

    recognitionRef.current = recognition
    setIsListening(true)
    recognition.start()
  }

  function stopVoiceInput() {
    recognitionRef.current?.stop()
    setIsListening(false)
  }

  return {
    isListening,
    voiceError,
    lastTranscript,
    voiceSupported,
    startVoiceInput,
    stopVoiceInput,
  }
}
