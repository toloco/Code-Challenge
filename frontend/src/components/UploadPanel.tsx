import { type ChangeEvent, type FormEvent, useState } from 'react'

export type UploadResponse = {
  threadId?: unknown
  runId?: unknown
  state?: unknown
}

type UploadPanelProps = {
  onUploadSuccess: (data: UploadResponse) => void
}

function UploadPanel({ onUploadSuccess }: UploadPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploadComplete, setUploadComplete] = useState(false)

  function isRetryableStatus(status: number) {
    return status === 422 || status === 429 || status === 503
  }

  function delay(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  function getUploadErrorMessage(status: number | null) {
    if (status === 422) {
      return 'Looks like we are out of tokens, please get in touch.'
    }
    if (status === 429) {
      return 'Too many requests right now. Please wait a moment and try again.'
    }
    if (status) {
      return `Upload failed with status ${status}`
    }
    return 'Upload failed. Please try again.'
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setError(null)
    setUploadComplete(false)
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile) {
      setError('Please choose a .pdf or .txt file first.')
      return
    }

    setLoading(true)
    setError(null)

    try {
      let data: UploadResponse | null = null
      let uploadSucceeded = false
      let lastStatus: number | null = null

      for (let attempt = 1; attempt <= 2; attempt += 1) {
        const formData = new FormData()
        formData.append('file', selectedFile)

        const response = await fetch('http://localhost:8000/upload', {
          method: 'POST',
          body: formData,
        })

        lastStatus = response.status

        if (response.ok) {
          data = await response.json()
          uploadSucceeded = true
          break
        }

        if (attempt === 1 && isRetryableStatus(response.status)) {
          await delay(2000)
          continue
        }

        throw new Error(getUploadErrorMessage(response.status))
      }

      if (!uploadSucceeded || !data) {
        throw new Error(getUploadErrorMessage(lastStatus))
      }

      setUploadComplete(true)
      onUploadSuccess(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed. Please try again.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="panel">
      <h2>Upload Recipe</h2>
      <p>Select a PDF or text recipe file to get started.</p>

      <form className="upload-form" onSubmit={handleUpload}>
        <input
          type="file"
          accept=".pdf,.txt"
          onChange={handleFileChange}
          className="file-input"
        />

        <p className="upload-meta">
          Selected: <strong>{selectedFile?.name ?? 'No file selected'}</strong>
        </p>

        <button type="submit" className="touch-button" disabled={loading || !selectedFile}>
          {loading ? 'Extracting recipe...' : 'Upload Recipe'}
        </button>
      </form>

      {error ? <p className="status-error">{error}</p> : null}
      {uploadComplete ? <p className="status-ok">Recipe uploaded. You can start chatting now.</p> : null}
    </section>
  )
}

export default UploadPanel
